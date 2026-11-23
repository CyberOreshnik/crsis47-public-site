"""Controlled Codex research task: verify IANA's documentation-domain policy and file its source."""
from contextlib import closing
from hashlib import sha256
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import secrets
import tempfile
import threading
from urllib.request import Request, build_opener

import codex_capture
import ingest
import project
import research_adapter
import server

class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

def research():
    request = Request(ingest.GATE2_URL, headers={"User-Agent": "CRSIS47-Gate2/1.0"})
    with build_opener(research_adapter.NoRedirect()).open(request, timeout=20) as response:
        if response.geturl() != ingest.GATE2_URL or response.headers.get_content_type() != "text/html":
            raise ValueError("unexpected public source response")
        content = response.read(524289)
    if len(content) > 524288:
        raise ValueError("public source exceeds size limit")
    document = VisibleText()
    document.feed(content.decode("utf-8"))
    evidence = " ".join(" ".join(document.parts).split()).lower()
    for phrase in ("example domains", "example.org", "maintained for documentation purposes",
                   "not available for registration or transfer"):
        if phrase not in evidence:
            raise ValueError("expected IANA policy evidence was not found")
    return {
        "question": "Is example.org suitable as an illustrative domain in documentation?",
        "finding": "IANA maintains example.org for documentation and excludes it from registration or transfer.",
        "source_url": ingest.GATE2_URL,
        "response_sha256": sha256(content).hexdigest(),
    }

def run(directory):
    previous = server.DB
    prior_opt_in = os.environ.pop("SOURCE_HUB_GATE2_IANA", None)
    server.DB = str(directory / "public.db")
    private = str(directory / "private.db")
    try:
        result = research()
        event = {
            "source_url": result["source_url"], "title": "Example Domains",
            "publisher": "Internet Assigned Numbers Authority", "used_at": ingest.now(),
            "project_ids": ["CRSIS47-GATE2"], "evidence_type": "historical_evidence",
            "originating_workflow": ingest.GATE2_WORKFLOW,
        }
        try:
            research_adapter.make_event(event)
        except ValueError as exc:
            if str(exc) != "gate2_source_not_authorized":
                raise
        else:
            raise RuntimeError("public source was accepted without opt-in")
        os.environ["SOURCE_HUB_GATE2_IANA"] = "1"
        token = secrets.token_hex(32)
        server.initialize()
        with ingest.http_service(private, token, 0) as service:
            stop = threading.Event()
            worker = threading.Thread(target=ingest.run_worker, args=(private, stop))
            http = threading.Thread(target=service.serve_forever)
            worker.start()
            http.start()
            try:
                endpoint = f"http://127.0.0.1:{service.server_port}"
                first = codex_capture.capture_event(event, endpoint, token)
                replay = codex_capture.capture_event(event, endpoint, token)
                second = codex_capture.capture_event(
                    dict(event, used_at=ingest.now()), endpoint, token)
            finally:
                stop.set()
                service.shutdown()
                worker.join()
                http.join()
        source_id = first["source_id"]
        with closing(ingest.connect(private)) as db:
            rows = db.execute("SELECT id,metadata FROM registry").fetchall()
            count = db.execute("SELECT COUNT(*) FROM intake_events WHERE status='filed'").fetchone()[0]
            if (len(rows) != 1 or rows[0]["id"] != source_id
                or json.loads(rows[0]["metadata"])["source_url"] != result["source_url"] or count != 2):
                raise RuntimeError("unexpected registry or receipt state")
        if (first != replay or second["receipt"] == first["receipt"] or second["source_id"] != source_id
            or server.search({})["items"]):
            raise RuntimeError("deduplication or isolation check failed")
        try:
            project.approve_snapshot(private, source_id)
        except ValueError as exc:
            if str(exc) != "source_not_eligible":
                raise
        else:
            raise RuntimeError("live evidence was eligible for public projection")
        site = Path("site")
        if not (site / "source-hub/index.html").is_file():
            raise RuntimeError("build site before running the Gate 2 isolation demonstration")
        for path in site.rglob("*"):
            if path.is_file() and path.suffix in {".html", ".js", ".json", ".mjs"}:
                if source_id.encode() in path.read_bytes():
                    raise RuntimeError("private source ID found in static build")
        return dict(result, status="filed", source_id=source_id, receipt=first["receipt"],
                    replay_receipt=replay["receipt"], second_use_receipt=second["receipt"],
                    registry_rows=len(rows), filed_events=count, public_matches=0,
                    public_projection="denied", static_build_source_id="absent")
    finally:
        server.DB = previous
        if prior_opt_in is None:
            os.environ.pop("SOURCE_HUB_GATE2_IANA", None)
        else:
            os.environ["SOURCE_HUB_GATE2_IANA"] = prior_opt_in

if __name__ == "__main__":
    # A fresh isolated registry per demonstration, outside the repository and web root.
    try:
        with tempfile.TemporaryDirectory(prefix="crsis47-gate2-") as temporary:
            directory = Path(temporary).resolve()
            if directory.is_relative_to(Path(__file__).resolve().parents[1]):
                raise ValueError("temporary directory must be outside the checkout")
            print(json.dumps(run(directory), indent=2))
    except Exception as exc:
        # Report transport or validation failure without logging credentials or raw input.
        raise SystemExit(f"Gate 2 source workflow failed ({type(exc).__name__}): {exc}") from None
