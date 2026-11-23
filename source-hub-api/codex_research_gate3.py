"""Run the authorized Gate 3 question and file each used source automatically."""
from contextlib import closing
from hashlib import sha256
import json
import os
from pathlib import Path
import secrets
import tempfile
import threading
from urllib.request import Request, build_opener

import codex_capture
from codex_research import VisibleText
import ingest
import project
from research_adapter import NoRedirect, submit
import server
import source_policy
from urllib.error import HTTPError

PRIMARY = "CRSIS47-GATE3"
SECONDARY = "CRSIS47-GATE3-BOOK-DEMO"
WORKFLOW = "codex-gate3-public"

def research(entry):
    request = Request(entry["url"], headers={"User-Agent": "CRSIS47-Gate3/1.0"})
    with build_opener(NoRedirect()).open(request, timeout=20) as response:
        if response.geturl() != entry["url"] or response.headers.get_content_type() != "text/html":
            raise ValueError("unexpected source identity or format")
        body = response.read(524289)
    if len(body) > 524288:
        raise ValueError("public source exceeds size limit")
    html = VisibleText()
    html.feed(body.decode("utf-8"))
    plain = " ".join(" ".join(html.parts).split()).casefold()
    if any(fragment.casefold() not in plain for fragment in entry["identity"]):
        raise ValueError("document identity or evidence locator did not match policy")
    return sha256(body).hexdigest()

def source_use(entry, digest, project_id):
    return dict({key: entry[key] for key in (
        "title", "publisher", "doi", "authors", "publication_date", "evidence_type"
    )}, source_url=entry["url"], used_at=ingest.now(), project_ids=[project_id],
        claim_ids=entry["relationships"][project_id], originating_workflow=WORKFLOW,
        external_ids=[entry["id"], "sha256:" + digest])

def reject_http(event, endpoint, token):
    try:
        submit(event, endpoint, token)
    except HTTPError as exc:
        with exc:
            if exc.code == 400:
                return
        raise
    raise RuntimeError("disallowed source was accepted")

def run(directory):
    previous_db = server.DB
    previous_flag = os.environ.get("SOURCE_HUB_GATE3_PUBLIC")
    server.DB = str(directory / "public.db")
    private = str(directory / "private.db")
    os.environ["SOURCE_HUB_GATE3_PUBLIC"] = "1"
    token = secrets.token_hex(32)
    try:
        server.initialize()
        evidence = []
        with ingest.http_service(private, token, 0) as service:
            stop = threading.Event()
            worker = threading.Thread(target=ingest.run_worker, args=(private, stop))
            http = threading.Thread(target=service.serve_forever)
            worker.start()
            http.start()
            try:
                endpoint = f"http://127.0.0.1:{service.server_port}"
                for entry in source_policy.load().values():
                    digest = research(entry)
                    event = source_use(entry, digest, PRIMARY)
                    first = codex_capture.capture_event(event, endpoint, token)
                    second_event = source_use(entry, digest, SECONDARY)
                    second = codex_capture.capture_event(second_event, endpoint, token)
                    replay = codex_capture.capture_event(event, endpoint, token)
                    if (first["source_id"] != second["source_id"] or first["receipt"] == second["receipt"]
                        or first != replay):
                        raise RuntimeError("event replay or cross-project deduplication failed")
                    evidence.append(dict(event, source_id=first["source_id"], receipt=first["receipt"],
                                         second_receipt=second["receipt"], replay_receipt=replay["receipt"],
                                         logical_collection=entry["logical_collection"],
                                         use=entry["use"], second_claim_ids=second_event["claim_ids"]))
                first_event = ingest.validate(dict(event, event_type="SOURCE_USED", doi=event["doi"],
                    capture_method="authorized_api", classification="REVIEW_REQUIRED"))
                reject_http(dict(first_event, source_url="https://www.rfc-editor.org/rfc/rfc2607.html"), endpoint, token)
                reject_http(dict(first_event, classification="RESTRICTED"), endpoint, token)
                reject_http(dict(first_event, doi="10.17487/rfc2607"), endpoint, token)
            finally:
                stop.set()
                service.shutdown()
                worker.join()
                http.join()
        if len(evidence) < 3 or len({item["source_id"] for item in evidence}) != len(evidence):
            raise RuntimeError("three distinct sources must be filed")
        with closing(ingest.connect(private)) as db:
            count = db.execute("SELECT COUNT(*) FROM registry").fetchone()[0]
            filed = db.execute("SELECT COUNT(*) FROM intake_events WHERE status='filed'").fetchone()[0]
            total_events = db.execute("SELECT COUNT(*) FROM intake_events").fetchone()[0]
            if count != len(evidence) or filed != 2 * count or filed != total_events:
                raise RuntimeError("unexpected private registry or queue counts")
            for item in evidence:
                row = db.execute("SELECT metadata,publication FROM registry WHERE id=?", (item["source_id"],)).fetchone()
                stored = json.loads(row[0])
                edges = [tuple(edge) for edge in db.execute(
                    "SELECT project,claim FROM relationships WHERE source_id=? ORDER BY project,claim",
                    (item["source_id"],))]
                wanted = sorted([(PRIMARY, claim) for claim in item["claim_ids"]]
                                + [(SECONDARY, claim) for claim in item["second_claim_ids"]])
                if (row[1] != "UNAPPROVED" or any(stored[k] != item[k] for k in (
                    "title", "publisher", "doi", "publication_date", "authors", "source_url"
                )) or edges != wanted):
                    raise RuntimeError("stored metadata or relationships did not match policy")
                if item["doi"] and db.execute("SELECT source_id FROM aliases WHERE kind='doi' AND value=?",
                                              (item["doi"],)).fetchone()[0] != item["source_id"]:
                    raise RuntimeError("DOI index does not resolve the canonical source")
                item["verified_relationships"] = edges
        if server.search({})["items"]:
            raise RuntimeError("private source entered public search")
        for item in evidence:
            try:
                project.approve_snapshot(private, item["source_id"])
            except ValueError as exc:
                if str(exc) != "source_not_eligible":
                    raise
            else:
                raise RuntimeError("real source was export eligible")
        site = Path("site")
        if not (site / "source-hub/index.html").is_file():
            raise RuntimeError("generated website is required")
        identifiers = [item["source_id"].encode() for item in evidence]
        for path in site.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".html", ".js", ".json", ".mjs"}:
                body = path.read_bytes()
                if any(identifier in body for identifier in identifiers):
                    raise RuntimeError("private registry identifier in generated website")
        return {"status": "filed", "question": "What do IANA and the RFCs say about using example.org in technical documentation?",
                "answer": "Use example.org for documentation. Let applications handle it normally and avoid relying on its web service in production.",
                "registry_rows": count, "filed_events": filed, "public_matches": 0,
                "blocked": ["unauthorized URL on approved host", "restricted classification", "mismatched DOI"],
                "public_projection": "denied", "static_build_source_ids": "absent", "sources": evidence}
    finally:
        server.DB = previous_db
        if previous_flag is None:
            os.environ.pop("SOURCE_HUB_GATE3_PUBLIC", None)
        else:
            os.environ["SOURCE_HUB_GATE3_PUBLIC"] = previous_flag

if __name__ == "__main__":
    try:
        with tempfile.TemporaryDirectory(prefix="crsis47-gate3-") as temporary:
            directory = Path(temporary).resolve()
            if directory.is_relative_to(Path(__file__).resolve().parents[1]):
                raise ValueError("temporary directory must be outside checkout")
            print(json.dumps(run(directory), indent=2))
    except Exception as exc:
        raise SystemExit(f"Gate 3 research or filing failed ({type(exc).__name__}): {exc}") from None
