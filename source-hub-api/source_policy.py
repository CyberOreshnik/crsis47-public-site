"""Exact-document policy for the controlled development research worker."""
from datetime import date
from functools import lru_cache
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

POLICY_PATH = Path(__file__).with_name("approved_sources.json")

@lru_cache(maxsize=1)
def load():
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    if policy["version"] != 1 or policy["workflow"] != "codex-gate3-public":
        raise ValueError("unsupported_source_policy")
    entries = {}
    ids = set()
    types = {kind: collection for collection, values in policy["collections"].items() for kind in values}
    for entry in policy["sources"]:
        url = urlsplit(entry["url"])
        if (url.scheme != "https" or not url.hostname or url.netloc != url.hostname
            or not url.path or url.query or url.fragment or entry["url"] in entries
            or entry["id"] in ids or entry["evidence_type"] not in types
            or not entry["identity"] or not entry["relationships"]):
            raise ValueError("invalid_source_policy")
        if entry["publication_date"]:
            stamp = entry["publication_date"]
            if not re.fullmatch(r"\d{4}-\d{2}(?:-\d{2})?", stamp):
                raise ValueError("invalid_policy_date")
            date.fromisoformat(stamp if len(stamp) == 10 else stamp + "-01")
        if entry["doi"] and not re.fullmatch(r"10\.\d{4,9}/[a-z0-9._;()/:-]+", entry["doi"]):
            raise ValueError("invalid_policy_doi")
        entries[entry["url"]] = dict(entry, logical_collection=types[entry["evidence_type"]])
        ids.add(entry["id"])
    return entries

def validate_event(event):
    entry = load().get(event["source_url"])
    if entry is None:
        raise ValueError("source_not_in_policy")
    expected = ("title", "publisher", "publication_date", "authors", "evidence_type", "doi")
    if any(event[field] != entry[field] for field in expected):
        raise ValueError("source_metadata_mismatch")
    if len(event["project_ids"]) != 1 or entry["relationships"].get(event["project_ids"][0]) != event["claim_ids"]:
        raise ValueError("source_relationship_not_in_policy")
    references = event["external_ids"]
    if (len(references) != 2 or references[0] != entry["id"]
        or not re.fullmatch(r"sha256:[a-f0-9]{64}", references[1])
        or event["capture_method"] != "authorized_api" or event.get("preservation_requested")
        or event["pgdt_lens"] is not None):
        raise ValueError("source_provenance_not_in_policy")
    return event
