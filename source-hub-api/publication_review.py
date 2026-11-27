"""Private publication review queue derived from durable SOURCE_USED receipts."""
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from urllib.parse import urlsplit, urlunsplit

import source_policy

ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = ("reviewed-literature.json", "reviewed-journals.json", "reviewed-government-evidence.json")
PUBLIC_TYPES = {"book", "scholarly_article", "historical_evidence",
                "public_research_guidance", "public_technical_guidance", "public_governance_guidance"}
CITATION_FIELDS = ("title", "authors", "publisher", "publication_date", "doi", "evidence_type")


def identity(url, doi):
    u = urlsplit(url)
    if u.scheme != "https" or not u.hostname or u.username or u.password:
        return set()
    canonical = urlunsplit(("https", u.netloc.lower(), u.path.rstrip("/") or "/", u.query, ""))
    keys = {("url", canonical)}
    if doi:
        keys.add(("doi", doi.casefold()))
    return keys


def public_keys(directory):
    keys = set()
    present = False
    for name in MANIFESTS:
        path = directory / name
        if path.is_file():
            present = True
            for item in json.loads(path.read_bytes()):
                keys.update(identity(item["url"], item.get("doi")))
    if not present:
        raise ValueError("public manifest unavailable")
    return keys


def candidates(db, published):
    seen = set(published)
    result = []
    rows = db.execute("""
        SELECT e.payload FROM intake_events e
        JOIN registry r ON r.id = e.source_id
        WHERE e.status = 'filed' AND r.classification = 'REVIEW_REQUIRED'
          AND NOT EXISTS (
              SELECT 1 FROM source_controls c
              WHERE c.url = json_extract(e.payload, '$.source_url') AND c.state != 'approved'
          )
        ORDER BY e.rowid
    """)
    for (payload,) in rows:
        event = json.loads(payload)
        if event.get("originating_workflow") != "codex-gate3-public" or event.get("evidence_type") not in PUBLIC_TYPES:
            continue
        if any(project.startswith("CRSIS47-GATE3") for project in event.get("project_ids", [])):
            continue
        try:
            source_policy.validate_event(event)
        except ValueError:
            continue
        keys = identity(event["source_url"], event["doi"])
        if not keys or keys & seen or not event["title"] or not event["publisher"]:
            continue
        result.append(dict({key: event[key] for key in CITATION_FIELDS}, url=event["source_url"]))
        seen.update(keys)
    return result


def refresh(path):
    from private_store import private_path
    registry = private_path(path)
    target = registry.parent / "source-hub-public-review.json"
    if target.exists() and os.name == "nt":
        from windows_security import file
        file(target)
    if target.is_symlink():
        raise ValueError("review output cannot be a symbolic link")
    published = public_keys(ROOT / "source-hub-api")
    with closing(sqlite3.connect(registry.as_uri() + "?mode=ro", uri=True, timeout=5)) as db:
        records = candidates(db, published)
    raw = (json.dumps({"status":"review_required","citations":records},
                      ensure_ascii=False, indent=2) + "\n").encode()
    if target.is_file() and target.read_bytes() == raw:
        return
    fd, staged = tempfile.mkstemp(prefix=".public-review-", dir=registry.parent)
    try:
        with os.fdopen(fd, "wb") as file_handle:
            file_handle.write(raw)
            file_handle.flush()
            os.fsync(file_handle.fileno())
        os.replace(staged, target)
    finally:
        Path(staged).unlink(missing_ok=True)
