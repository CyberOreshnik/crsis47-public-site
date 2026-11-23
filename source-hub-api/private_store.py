"""Private SQLite operations for Gate 4. Managed paths verify POSIX permissions or Windows ACLs."""
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat

VERSION = 1
MIGRATION = """
CREATE TABLE IF NOT EXISTS source_controls(
    url TEXT PRIMARY KEY, state TEXT NOT NULL CHECK(state IN ('approved','suspended','revoked'))
);
CREATE TABLE IF NOT EXISTS control_audit(
    sequence INTEGER PRIMARY KEY, url TEXT NOT NULL, action TEXT NOT NULL,
    detail TEXT NOT NULL, recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""
TABLES = ("registry", "aliases", "relationships", "intake_events", "audit",
          "source_controls", "control_audit")

def migrate(db):
    version = db.execute("PRAGMA user_version").fetchone()[0]
    if version not in (0, VERSION):
        raise ValueError("unsupported private registry schema")
    if version == 0:
        db.executescript("BEGIN IMMEDIATE;" + MIGRATION + "PRAGMA user_version=1; COMMIT;")

def private_path(value, create=False):
    if os.name not in {"posix", "nt"}:
        raise ValueError("unsupported private storage platform")
    from server import DB
    raw = Path(value).expanduser().absolute()
    if os.name == "nt":
        import windows_security
        windows_security.reject_reparse(raw)
    path = raw.resolve()
    checkout = Path(__file__).resolve().parents[1]
    if raw != path or path.is_relative_to(checkout) or path == Path(DB).resolve():
        raise ValueError("private file must be outside checkout and distinct from public storage")
    if os.name == "nt":
        windows_security.directory(path.parent, create)
        for item in (path, *(Path(str(path) + suffix) for suffix in ("-wal", "-shm", "-journal"))):
            if item.exists():
                windows_security.file(item)
        return path
    if create:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    parent = path.parent.stat()
    if parent.st_uid != os.getuid() or stat.S_IMODE(parent.st_mode) != 0o700:
        raise ValueError("private directory must be owned by the operator and mode 0700")
    for item in (path, *(Path(str(path) + suffix) for suffix in ("-wal", "-shm", "-journal"))):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
            or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600):
            raise ValueError("private database and SQLite sidecars must be owned mode-0600 regular files")
    return path

def provision(value):
    path = private_path(value, create=True)
    if not path.exists():
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
    return path

def inspect_connection(db):
    if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise ValueError("SQLite integrity check failed")
    if db.execute("PRAGMA foreign_key_check").fetchone():
        raise ValueError("SQLite foreign key integrity check failed")
    version = db.execute("PRAGMA user_version").fetchone()[0]
    if version not in (0, VERSION):
        raise ValueError("unknown backup schema")
    if db.execute("""SELECT 1 FROM intake_events e LEFT JOIN registry r ON r.id=e.source_id
                     WHERE (e.status='filed' AND r.id IS NULL)
                        OR e.status NOT IN ('queued','filed','failed') LIMIT 1""").fetchone():
        raise ValueError("filing receipt integrity check failed")
    counts = {}
    digest = hashlib.sha256()
    for table in TABLES if version else TABLES[:5]:
        rows = db.execute(f"SELECT * FROM {table} ORDER BY rowid")
        count = 0
        for row in rows:
            digest.update(json.dumps((table, row), ensure_ascii=False).encode() + b"\n")
            count += 1
        counts[table] = count
    return {"schema_version": version, "counts": counts, "record_digest": digest.hexdigest()}

def inspect(value):
    path = private_path(value)
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
        db.execute("BEGIN")
        return inspect_connection(db)

def copy_verified(source, destination):
    source = private_path(source)
    destination = private_path(destination, create=True)
    if any(Path(str(destination) + suffix).exists() for suffix in ("", "-wal", "-shm", "-journal")):
        raise FileExistsError("backup or restore target already exists")
    # Reserve a restrictive file before SQLite can write any pages.
    fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    try:
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as original:
            original.execute("BEGIN")
            expected = inspect_connection(original)
            with closing(sqlite3.connect(destination)) as target:
                original.backup(target)
        actual = inspect(destination)
        if actual != expected:
            raise ValueError("backup or restore verification mismatch")
        return actual
    except BaseException:
        destination.unlink(missing_ok=True)
        raise

def blocked(db, url):
    row = db.execute("SELECT state FROM source_controls WHERE url=?", (url,)).fetchone()
    return row is not None and row[0] != "approved"

def govern(path, url, action, reason, correction=None):
    import ingest
    import source_policy
    if url not in source_policy.load() or not reason.strip() or len(reason) > 500:
        raise ValueError("governance requires an exact reviewed URL and bounded reason")
    with closing(ingest.connect(path)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        prior = db.execute("SELECT state FROM source_controls WHERE url=?", (url,)).fetchone()
        before = prior[0] if prior else "approved"
        if action == "correct":
            if not isinstance(correction, dict) or not correction or set(correction) - {"title", "publisher"}:
                raise ValueError("only policy-aligned title and publisher corrections are supported")
            policy = source_policy.load()[url]
            if any(correction[key] != policy[key] for key in correction):
                raise ValueError("amend the reviewed policy register before correcting metadata")
            row = db.execute("""SELECT r.id,r.metadata FROM aliases a JOIN registry r ON r.id=a.source_id
                                WHERE a.kind='url' AND a.value=?""", (url,)).fetchone()
            if not row:
                raise ValueError("source has not been filed")
            old = json.loads(row[1])
            new = dict(old, **correction)
            db.execute("UPDATE registry SET metadata=? WHERE id=?", (ingest.encode(new), row[0]))
            detail = {"old": old, "new": new}
        else:
            state = {"approve": "approved", "suspend": "suspended", "revoke": "revoked"}.get(action)
            if state is None:
                raise ValueError("invalid policy transition")
            db.execute("""INSERT INTO source_controls VALUES(?,?) ON CONFLICT(url)
                          DO UPDATE SET state=excluded.state""", (url, state))
            detail = {"old": before, "new": state}
        db.execute("INSERT INTO control_audit(url,action,detail) VALUES(?,?,?)",
                   (url, action, ingest.encode(dict(detail, reason=reason))))

def main():
    import ingest
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=os.getenv("SOURCE_HUB_PRIVATE_DB"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("verify")
    sub.add_parser("migrate")
    for name in ("backup", "restore"):
        sub.add_parser(name).add_argument("destination")
    control = sub.add_parser("policy")
    control.add_argument("action", choices=("approve", "suspend", "revoke", "correct"))
    control.add_argument("url")
    control.add_argument("--reason", required=True)
    control.add_argument("--correction-json")
    args = parser.parse_args()
    if not args.db:
        parser.error("set --db or SOURCE_HUB_PRIVATE_DB")
    try:
        if args.command in {"backup", "restore"}:
            result = copy_verified(args.db, args.destination)
        elif args.command == "policy":
            path = private_path(args.db)
            govern(path, args.url, args.action, args.reason,
                   json.loads(args.correction_json) if args.correction_json else None)
            result = {"status": "recorded"}
        else:
            if args.command == "migrate":
                ingest.initialize(provision(args.db))
            result = inspect(args.db)
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, sqlite3.Error) as exc:
        parser.exit(1, f"Private registry operation failed: {exc}\n")

if __name__ == "__main__":
    main()
