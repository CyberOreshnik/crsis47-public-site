"""Loopback synthetic SOURCE_USED intake. Private database never serves public search."""
import argparse
from contextlib import closing
from datetime import date, datetime, timezone
import hashlib
from http.server import ThreadingHTTPServer
import hmac
import json
import logging
import os
from pathlib import Path
import re
import sqlite3
import time
import threading
from urllib.parse import unquote, urlsplit, urlunsplit
import uuid

import server
import private_store

SCHEMA = """
CREATE TABLE IF NOT EXISTS intake_events(
 key TEXT PRIMARY KEY, receipt TEXT UNIQUE NOT NULL, digest TEXT NOT NULL,
 payload TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'queued',
 attempts INTEGER NOT NULL DEFAULT 0, available REAL NOT NULL, source_id TEXT, error TEXT
);
CREATE INDEX IF NOT EXISTS intake_ready ON intake_events(status,available);
CREATE TABLE IF NOT EXISTS registry(
 id TEXT PRIMARY KEY, metadata TEXT NOT NULL, collection TEXT NOT NULL,
 classification TEXT NOT NULL, verification TEXT NOT NULL DEFAULT 'CAPTURED',
 preservation TEXT NOT NULL DEFAULT 'NOT_PRESERVED',
 publication TEXT NOT NULL DEFAULT 'UNAPPROVED', discovered_at TEXT NOT NULL,
 retrieved_at TEXT, original_checksum TEXT, rights TEXT NOT NULL DEFAULT 'UNKNOWN'
);
CREATE TABLE IF NOT EXISTS aliases(
 kind TEXT NOT NULL, value TEXT NOT NULL, source_id TEXT NOT NULL REFERENCES registry,
 PRIMARY KEY(kind,value)
);
CREATE TABLE IF NOT EXISTS relationships(
 source_id TEXT NOT NULL REFERENCES registry, project TEXT NOT NULL, claim TEXT NOT NULL,
 PRIMARY KEY(source_id,project,claim)
);
CREATE TABLE IF NOT EXISTS audit(
 sequence INTEGER PRIMARY KEY, source_id TEXT NOT NULL REFERENCES registry,
 receipt TEXT NOT NULL, action TEXT NOT NULL, detail TEXT NOT NULL, at TEXT NOT NULL
);
"""
COLLECTIONS = {
    "scholarly_article": "scholarly-literature", "citation_register": "doctoral-research",
    "pgdt_scenario": "pgdt", "engineering_archive": "engineering",
    "validator_record": "validation", "governance_record": "governance",
    "case_study": "case-studies", "book": "books", "laboratory": "laboratories",
    "historical_evidence": "historical-archives",
    "public_research_guidance": "research-laboratories",
    "public_technical_guidance": "engineering-governance",
    "public_governance_guidance": "engineering-governance",
}
REQUIRED = {
    "event_type", "source_url", "doi", "title", "authors", "publisher",
    "publication_date", "used_at", "project_ids", "claim_ids", "evidence_type",
    "classification", "originating_workflow", "capture_method",
}
OPTIONAL = {"schema_version", "pgdt_lens", "external_ids", "preservation_requested"}
GATE2_URL = "https://www.iana.org/help/example-domains"
GATE2_WORKFLOW = "codex-gate2-iana"
PRIVATE_TYPES = {"validator_record", "engineering_archive", "governance_record", "citation_register"}
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")
LENSES = {"People", "Governance", "Data", "Technology"}

class Conflict(ValueError):
    pass

def now():
    return datetime.now(timezone.utc).isoformat()

def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def validate(event):
    if not isinstance(event, dict) or REQUIRED - event.keys() or event.keys() - REQUIRED - OPTIONAL:
        raise ValueError("invalid_fields")
    if (event["event_type"] != "SOURCE_USED" or type(event.get("schema_version", 1)) is not int
        or event.get("schema_version", 1) != 1):
        raise ValueError("unsupported_event")
    result = dict(event, schema_version=1)
    for key in ("title", "publisher", "doi", "publication_date", "pgdt_lens"):
        value = result.get(key)
        if value is not None and (not isinstance(value, str) or len(value) > 256):
            raise ValueError("invalid_metadata")
        result[key] = value.strip() or None if value is not None else None
    for key in ("originating_workflow", "capture_method", "used_at", "source_url",
                "evidence_type", "classification"):
        if not isinstance(result[key], str) or not result[key] or len(result[key]) > 2048:
            raise ValueError("invalid_metadata")
    for key in ("project_ids", "claim_ids", "authors", "external_ids"):
        values = result.get(key, [])
        if (not isinstance(values, list) or len(values) > 64 or any(
            not isinstance(v, str) or not v.strip() or len(v) > 128
            or (key != "authors" and not ID.fullmatch(v)) for v in values)):
            raise ValueError("invalid_relationship")
        result[key] = list(dict.fromkeys(v.strip() for v in values))
    if not result["project_ids"]:
        raise ValueError("project_required")
    if result["classification"] != "REVIEW_REQUIRED" or result["evidence_type"] in PRIVATE_TYPES:
        raise ValueError("restricted_ingestion_disabled")
    if result["evidence_type"] not in COLLECTIONS or result["pgdt_lens"] not in LENSES | {None}:
        raise ValueError("invalid_collection")
    if type(result.get("preservation_requested", False)) is not bool:
        raise ValueError("invalid_preservation_request")
    stamp = datetime.fromisoformat(result["used_at"].replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("timezone_required")
    result["used_at"] = stamp.astimezone(timezone.utc).isoformat()
    if result["originating_workflow"] == "codex-gate3-public":
        if os.getenv("SOURCE_HUB_GATE3_PUBLIC") != "1":
            raise ValueError("gate3_source_not_authorized")
        from source_policy import validate_event
        return validate_event(result)
    if result["publication_date"] and date.fromisoformat(result["publication_date"]).isoformat() != result["publication_date"]:
        raise ValueError("invalid_publication_date")
    if result["source_url"] == GATE2_URL:
        if (os.getenv("SOURCE_HUB_GATE2_IANA") != "1"
            or result["originating_workflow"] != GATE2_WORKFLOW
            or result["capture_method"] != "authorized_api"
            or result["project_ids"] != ["CRSIS47-GATE2"]
            or result["evidence_type"] != "historical_evidence"
            or result["claim_ids"] or result["external_ids"] or result["doi"]
            or result.get("preservation_requested")):
            raise ValueError("gate2_source_not_authorized")
        return result
    url = urlsplit(result["source_url"])
    if (url.scheme != "https" or url.netloc.lower() != "example.org" or url.query
        or not re.fullmatch(r"/synthetic/[a-zA-Z0-9/_-]+", url.path)):
        raise ValueError("synthetic_sources_only")
    result["source_url"] = urlunsplit(("https", "example.org", url.path.rstrip("/"), "", ""))
    if result["doi"]:
        doi = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", result["doi"], flags=re.I)
        doi = unquote(doi).lower()
        if not re.fullmatch(r"10\.5555/synthetic[-a-z0-9._]+", doi):
            raise ValueError("synthetic_doi_only")
        result["doi"] = doi
    return result

def connect(path):
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    if os.name == "nt":
        db.execute("PRAGMA temp_store=MEMORY")
    return db

def initialize(path):
    if Path(path).resolve() == Path(server.DB).resolve():
        raise ValueError("private_and_public_databases_must_differ")
    with closing(connect(path)) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.executescript(SCHEMA)
        private_store.migrate(db)

def enqueue(path, key, raw):
    if not isinstance(key, str) or not ID.fullmatch(key):
        raise ValueError("invalid_idempotency_key")
    event = validate(raw)
    payload = encode(event)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    with closing(connect(path)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        previous = db.execute("SELECT digest,receipt FROM intake_events WHERE key=?", (key,)).fetchone()
        if previous:
            if previous["digest"] != digest:
                raise Conflict("idempotency_key_reused")
            return previous["receipt"]
        if private_store.blocked(db, event['source_url']):
            raise ValueError('source_authorization_inactive')
        receipt = uuid.uuid4().hex
        db.execute("INSERT INTO intake_events(key,receipt,digest,payload,available) VALUES(?,?,?,?,?)",
                   (key, receipt, digest, payload, time.time()))
        return receipt

def file_source(db, row):
    event = json.loads(row["payload"])
    if private_store.blocked(db, event['source_url']):
        raise Conflict('source_authorization_inactive')
    if event["originating_workflow"] == "codex-gate3-public":
        from source_policy import validate_event
        try:
            validate_event(event)
        except ValueError as exc:
            raise Conflict("source_policy_changed") from exc
    identities = [("url", event["source_url"])]
    if event["doi"]:
        identities.append(("doi", event["doi"]))
    matches = {match[0] for identity in identities if (match := db.execute(
        "SELECT source_id FROM aliases WHERE kind=? AND value=?", identity).fetchone())}
    if len(matches) > 1:
        raise Conflict("identity_collision")
    source = next(iter(matches), "SRC-" + uuid.uuid4().hex)
    metadata_keys = ("source_url", "doi", "title", "authors", "publisher", "publication_date",
                     "pgdt_lens", "evidence_type")
    incoming = {key: event[key] for key in metadata_keys}
    current = db.execute("SELECT metadata FROM registry WHERE id=?", (source,)).fetchone()
    if current:
        merged = json.loads(current[0])
        conflict = []
        for key, value in incoming.items():
            if not merged[key]:
                merged[key] = value
            elif value and value != merged[key]:
                conflict.append(key)
        if "doi" in conflict:
            raise Conflict("doi_conflict")
        db.execute("UPDATE registry SET metadata=? WHERE id=?", (encode(merged), source))
        action = "METADATA_CONFLICT" if conflict else "SOURCE_USED"
    else:
        merged, conflict, action = incoming, [], "CAPTURED"
        db.execute("INSERT INTO registry(id,metadata,collection,classification,discovered_at) VALUES(?,?,?,?,?)",
                   (source, encode(merged), COLLECTIONS[event["evidence_type"]], event["classification"], event["used_at"]))
    for kind, value in identities:
        db.execute("INSERT OR IGNORE INTO aliases VALUES(?,?,?)", (kind, value, source))
    # Preserve the relationship scope of this event; subsequent deliveries only add edges.
    db.executemany("INSERT OR IGNORE INTO relationships VALUES(?,?,?)", (
        (source, project, claim) for project in event["project_ids"] for claim in event["claim_ids"] or [""]
    ))
    db.execute("INSERT INTO audit(source_id,receipt,action,detail,at) VALUES(?,?,?,?,?)",
               (source, row["receipt"], action, encode({"metadata": merged, "conflict_fields": conflict,
                "preservation": "blocked_rights_or_storage" if event.get("preservation_requested") else "not_requested"}), now()))
    return source

def process_one(path, processor=file_source):
    with closing(connect(path)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("""SELECT * FROM intake_events WHERE status='queued' AND available<=?
                            ORDER BY available,rowid LIMIT 1""", (time.time(),)).fetchone()
        if row is None:
            return False
        db.execute("SAVEPOINT filing")
        attempts = row["attempts"] + 1
        try:
            source = processor(db, row)
        except (Conflict, sqlite3.Error) as exc:
            db.execute("ROLLBACK TO filing")
            db.execute("RELEASE filing")
            terminal = isinstance(exc, Conflict) or attempts >= 3
            code = str(exc) if isinstance(exc, Conflict) else "storage_processing_error"
            db.execute("UPDATE intake_events SET status=?,attempts=?,available=?,error=? WHERE receipt=?",
                       ("failed" if terminal else "queued", attempts, time.time() + 2 ** attempts, code, row["receipt"]))
            logging.warning("source_intake receipt=%s attempt=%s code=%s", row["receipt"], attempts, code)
        else:
            db.execute("RELEASE filing")
            db.execute("UPDATE intake_events SET status='filed',attempts=?,source_id=?,error=NULL WHERE receipt=?",
                       (attempts, source, row["receipt"]))
        return True

def receipt(path, identifier):
    with closing(connect(path)) as db:
        row = db.execute("SELECT receipt,status,attempts,source_id,error FROM intake_events WHERE receipt=?",
                         (identifier,)).fetchone()
        return dict(row) if row else None

class IntakeHandler(server.Handler):
    def authorized(self):
        actual = self.headers.get("Authorization", "").encode("utf-8")
        if not hmac.compare_digest(actual, self.server.bearer):
            self.respond(401, {"error": "unauthorized"})
            return False
        return True

    def do_POST(self):
        if not self.authorized():
            return
        if self.path != "/api/source-events":
            self.respond(404, {"error": "not_found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 65536 or self.headers.get("Transfer-Encoding"):
                raise ValueError()
            if self.headers.get_content_type() != "application/json":
                raise ValueError()
            event = json.loads(self.rfile.read(length))
            identifier = enqueue(self.server.private_path, self.headers.get("Idempotency-Key"), event)
            self.respond(202, receipt(self.server.private_path, identifier))
        except Conflict:
            self.respond(409, {"error": "idempotency_key_reused"})
        except (ValueError, TimeoutError, RecursionError):
            self.respond(400, {"error": "invalid_or_disallowed_event"})
        except sqlite3.Error:
            self.respond(503, {"error": "temporarily_unavailable"})

    def do_GET(self):
        if not self.authorized():
            return
        match = re.fullmatch(r"/api/source-events/([a-f0-9]{32})", self.path)
        try:
            result = receipt(self.server.private_path, match[1]) if match else None
            self.respond(200 if result else 404, result or {"error": "not_found"})
        except sqlite3.Error:
            self.respond(503, {"error": "temporarily_unavailable"})

    def setup(self):
        self.request.settimeout(10)
        super().setup()

def http_service(path, token, port):
    if not token or len(token) < 32:
        raise ValueError("SOURCE_HUB_INTAKE_TOKEN must have at least 32 characters")
    initialize(path)
    service = ThreadingHTTPServer(("127.0.0.1", port), IntakeHandler)
    service.private_path = path
    service.bearer = ("Bearer " + token).encode()
    return service

def run_worker(path, stop):
    review_enabled = os.getenv("SOURCE_HUB_PUBLIC_REVIEW") == "1"
    review_due = 0
    while not stop.is_set():
        try:
            filed_or_processed = process_one(path)
        except sqlite3.Error:
            logging.warning("source_intake worker storage_unavailable")
            filed_or_processed = False
        if review_enabled and time.monotonic() >= review_due:
            from publication_review import refresh
            try:
                refresh(path)
            except (OSError, ValueError, sqlite3.Error):
                logging.warning("source_intake publication_review_refresh_failed")
            review_due = time.monotonic() + 30
        if not filed_or_processed:
            stop.wait(0.25)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-db", default=os.getenv("SOURCE_HUB_PRIVATE_DB"))
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("command", choices=("serve", "drain", "failures"))
    args = parser.parse_args()
    if not args.private_db:
        parser.error('set --private-db or SOURCE_HUB_PRIVATE_DB')
    managed = os.getenv("SOURCE_HUB_PERSISTENT") == "1" or os.name == "nt"
    path = private_store.provision(args.private_db) if managed else args.private_db
    initialize(path)
    if args.command == "serve":
        from windows_security import configured_token
        try:
            token = configured_token()
        except (ValueError, OSError):
            parser.exit(1, "Intake credential is unavailable or invalid.\n")
        with http_service(path, token, args.port) as service:
            stop = threading.Event()
            worker = threading.Thread(target=run_worker, args=(path, stop), daemon=True)
            worker.start()
            try:
                service.serve_forever()
            finally:
                stop.set()
                worker.join()
    elif args.command == "drain":
        while process_one(path):
            pass
    else:
        with closing(connect(path)) as db:
            rows = db.execute("SELECT receipt, attempts, error FROM intake_events WHERE status='failed'")
            print(encode([dict(row) for row in rows]))

if __name__ == "__main__":
    main()
