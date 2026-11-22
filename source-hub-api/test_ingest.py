import json
import os
from pathlib import Path
import secrets
import sqlite3
import statistics
import tempfile
import threading
import time
import unittest
from contextlib import closing
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import ingest
import project
import server

def fixture(**changes):
    return dict({
        "event_type": "SOURCE_USED", "source_url": "https://example.org/synthetic/article",
        "doi": "10.5555/synthetic-1", "title": "Synthetic example", "authors": [],
        "publisher": None, "publication_date": None, "used_at": "2026-11-22T17:00:00Z",
        "project_ids": ["CASE-001"], "claim_ids": ["C001"], "evidence_type": "scholarly_article",
        "classification": "REVIEW_REQUIRED", "originating_workflow": "synthetic-test",
        "capture_method": "authorized_api",
    }, **changes)

class IntakeTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.private = str(Path(self.directory.name) / "registry.db")
        previous = server.DB
        self.addCleanup(setattr, server, "DB", previous)
        server.DB = str(Path(self.directory.name) / "public.db")
        ingest.initialize(self.private)
        server.initialize()

    def file(self, key, event):
        receipt = ingest.enqueue(self.private, key, event)
        self.assertTrue(ingest.process_one(self.private))
        result = ingest.receipt(self.private, receipt)
        self.assertEqual(result["status"], "filed")
        return result["source_id"]

    def test_new_idempotent_and_multi_project(self):
        event = fixture(title=None)
        source = self.file("first", event)
        same_receipt = ingest.enqueue(self.private, "first", event)
        self.assertEqual(ingest.receipt(self.private, same_receipt)["source_id"], source)
        with self.assertRaises(ingest.Conflict):
            ingest.enqueue(self.private, "first", fixture())
        self.assertEqual(self.file("second", fixture(source_url="https://example.org/synthetic/alias",
                                                     project_ids=["CASE-002"])), source)
        self.assertEqual(self.file("third", fixture(doi=None, title="Different title")), source)
        with closing(ingest.connect(self.private)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM registry").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM relationships").fetchone()[0], 2)
            entries = db.execute("SELECT action,detail FROM audit ORDER BY sequence").fetchall()
            self.assertIsNone(json.loads(entries[0][1])["metadata"]["title"])
            self.assertEqual(entries[-1][0], "METADATA_CONFLICT")
            self.assertEqual(json.loads(entries[-1][1])["metadata"]["title"], "Synthetic example")
        self.assertEqual(server.search({})["items"], [])
        ingest.initialize(self.private)
        self.assertEqual(ingest.receipt(self.private, same_receipt)["source_id"], source)

    def test_retry_restart_and_identity_conflict(self):
        def fail(db, row):
            ingest.file_source(db, row)
            raise sqlite3.OperationalError("synthetic failure")
        event = fixture()
        key = ingest.enqueue(self.private, "retry", event)
        ingest.process_one(self.private, fail)
        self.assertEqual(ingest.receipt(self.private, key)["attempts"], 1)
        with closing(ingest.connect(self.private)) as db, db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM registry").fetchone()[0], 0)
            db.execute("UPDATE intake_events SET available=0")
        ingest.initialize(self.private)
        ingest.process_one(self.private)
        self.assertEqual(ingest.receipt(self.private, key)["status"], "filed")
        key = ingest.enqueue(self.private, "conflict", fixture(doi="10.5555/synthetic-conflict"))
        ingest.process_one(self.private)
        self.assertEqual(ingest.receipt(self.private, key)["error"], "doi_conflict")
        key = ingest.enqueue(self.private, "terminal", fixture())
        for _ in range(3):
            with closing(ingest.connect(self.private)) as db, db:
                db.execute("UPDATE intake_events SET available=0 WHERE receipt=?", (key,))
            ingest.process_one(self.private, fail)
        self.assertEqual(ingest.receipt(self.private, key)["status"], "failed")
        self.assertEqual(ingest.receipt(self.private, key)["attempts"], 3)

    @unittest.skipIf(os.getenv("SOURCE_HUB_SKIP_SOCKET_TEST") == "1", "Local sandbox blocks loopback")
    def test_authenticated_http(self):
        token = secrets.token_hex(32)
        service = ingest.http_service(self.private, token, 0)
        thread = threading.Thread(target=service.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(service.server_close)
        self.addCleanup(thread.join)
        self.addCleanup(service.shutdown)
        endpoint = f"http://127.0.0.1:{service.server_port}/api/source-events"
        headers = {"Idempotency-Key": "http-example", "Content-Type": "application/json"}
        body = json.dumps(fixture()).encode()
        with self.assertRaises(HTTPError) as failure:
            urlopen(Request(endpoint, body, headers), timeout=3)
        self.assertEqual(failure.exception.code, 401)
        headers["Authorization"] = f"Bearer {token}"
        with urlopen(Request(endpoint, body, headers), timeout=3) as response:
            result = json.load(response)
            self.assertEqual(response.status, 202)
            self.assertEqual(result["status"], "queued")
        stop = threading.Event()
        worker = threading.Thread(target=ingest.run_worker, args=(self.private, stop))
        worker.start()
        try:
            for _ in range(30):
                with urlopen(Request(endpoint + "/" + result["receipt"], headers=headers), timeout=3) as response:
                    if json.load(response)["status"] == "filed":
                        break
                time.sleep(0.03)
            else:
                self.fail("background worker did not file the HTTP event")
        finally:
            stop.set()
            worker.join()

    def test_boundary_and_export_roundtrip(self):
        for event in [fixture(classification="RESTRICTED"), fixture(evidence_type="validator_record"),
                      fixture(source_url="https://other.example/research")]:
            with self.assertRaises(ValueError):
                ingest.enqueue(self.private, "reject", event)
        source = self.file("open", fixture(authors=["Synthetic Author"]))
        result = project.project_demo(self.private, source)
        with closing(server.connect()) as db, db:
            project.import_snapshot(db, json.loads(json.dumps(result)))
            with self.assertRaises(ValueError):
                project.import_snapshot(db, dict(result, evidence_type="validator_record"))
        page = server.search({"q":["Synthetic Author"],"project":["CASE-001"],
                              "collection":["scholarly-literature"],"verification":["CAPTURED"]})
        self.assertEqual(len(page["items"]), 1)
        self.assertEqual(page["items"][0]["citation"], result)
        self.assertNotIn("C001", json.dumps(page))
        self.assertNotIn("originating_workflow", json.dumps(page))
        self.assertNotIn("idempotency", json.dumps(page))

    def test_search_scale(self):
        first = self.file("seed", fixture())
        snapshot = ingest.encode(project.approve_snapshot(self.private, first))
        start = time.perf_counter()
        with closing(server.connect()) as db, db:
            for index in range(10000):
                item = dict(json.loads(snapshot), source_id=f"SRC-synthetic-{index:05d}",
                            title=f"Synthetic scale record {index:05d}")
                project.import_snapshot(db, item)
        seed_ms = (time.perf_counter() - start) * 1000
        self.assertEqual(len(server.search({"q":["record 04242"], "project":["CASE-001"]})["items"]), 1)
        query = {"project":["CASE-001"], "collection":["scholarly-literature"]}
        observed, times = [], []
        while True:
            start = time.perf_counter()
            page = server.search(query)
            times.append((time.perf_counter() - start) * 1000)
            self.assertLessEqual(len(page["items"]), 25)
            observed.extend(x["citation"]["source_id"] for x in page["items"])
            if not page["nextCursor"]:
                break
            query["cursor"] = [page["nextCursor"]]
        self.assertEqual(observed, [f"SRC-synthetic-{n:05d}" for n in range(10000)])
        print(json.dumps({"records":len(observed), "pages":len(times), "seed_ms":round(seed_ms,2),
                          "p50_ms":round(statistics.median(times),3),
                          "p95_ms":round(statistics.quantiles(times,n=20)[18],3)}))

if __name__ == "__main__":
    unittest.main(verbosity=2)
