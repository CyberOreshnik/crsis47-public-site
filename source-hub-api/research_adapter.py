"""Explicit research-workflow adapter for synthetic SOURCE_USED events only.

This is a client, not a ChatGPT/Zotero hook. An authorized caller must explicitly
invoke it after using a source. No discovery, crawling, or automatic publishing.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

FIELDS = ("event_type", "schema_version", "source_url", "doi", "title", "authors",
          "publisher", "publication_date", "used_at", "project_ids", "claim_ids",
          "evidence_type", "classification", "originating_workflow", "capture_method",
          "pgdt_lens", "external_ids", "preservation_requested")

def make_event(record):
    """Map an explicit source-use record without inventing missing bibliographic facts."""
    if not isinstance(record, dict):
        raise ValueError("record must be an object")
    event = {key: record[key] for key in FIELDS if key in record}
    event["event_type"] = "SOURCE_USED"
    event["schema_version"] = 1
    if record.get("classification", "REVIEW_REQUIRED") != "REVIEW_REQUIRED":
        raise ValueError("restricted classification cannot be downgraded")
    event["classification"] = "REVIEW_REQUIRED"
    event["capture_method"] = "authorized_api"
    event.setdefault("originating_workflow", "explicit-research-adapter")
    for key in ("doi", "title", "publisher", "publication_date"):
        event.setdefault(key, None)
    for key in ("authors", "claim_ids"):
        event.setdefault(key, [])
    # Enforce existing intake policy: no restricted sources or non-synthetic URLs.
    from ingest import validate
    return validate(event)

def stable_key(event):
    raw = json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "research-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]

def submit(event, endpoint, token, timeout=10):
    if not endpoint.startswith("http://127.0.0.1:") and not endpoint.startswith("http://localhost:"):
        raise ValueError("only local loopback intake is authorized")
    if not token or len(token) < 32:
        raise ValueError("SOURCE_HUB_INTAKE_TOKEN is required")
    body = json.dumps(event, sort_keys=True).encode("utf-8")
    request = Request(endpoint.rstrip("/") + "/api/source-events", body, {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + token,
        "Idempotency-Key": stable_key(event),
    }, method="POST")
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)

def main():
    parser = argparse.ArgumentParser(description="Explicit synthetic research-to-Source-Hub adapter")
    parser.add_argument("record", help="JSON source-use record; must use example.org/synthetic")
    parser.add_argument("--submit", action="store_true", help="Send to approved local intake; default dry-run")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8766")
    args = parser.parse_args()
    event = make_event(json.loads(Path(args.record).read_text(encoding="utf-8")))
    if args.submit:
        result = submit(event, args.endpoint, os.getenv("SOURCE_HUB_INTAKE_TOKEN"))
        print(json.dumps({"receipt": result.get("receipt"), "status": result.get("status")}))
    else:
        print(json.dumps({"mode": "dry-run", "idempotency_key": stable_key(event),
                          "event": event}, indent=2))

if __name__ == "__main__":
    main()
