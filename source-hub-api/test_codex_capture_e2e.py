"""Synthetic Codex research-use -> local intake -> private filing -> approved public index."""
import json
import secrets
import sys
import tempfile
import threading
import time
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ingest
import project
import research_adapter
import server

class CodexEndToEnd(unittest.TestCase):
    def test_source_use_to_private_receipt_and_explicit_public_projection(self):
        with tempfile.TemporaryDirectory() as directory:
            private = str(Path(directory) / "private.db")
            public = str(Path(directory) / "public.db")
            previous = server.DB
            server.DB = public
            try:
                ingest.initialize(private)
                server.initialize()
                event = research_adapter.make_event(json.loads(
                    (Path(__file__).parent / "synthetic-event.json").read_text(encoding="utf-8")))
                token = secrets.token_hex(32)
                with ingest.http_service(private, token, 0) as service:
                    worker_stop = threading.Event()
                    worker = threading.Thread(target=ingest.run_worker, args=(private, worker_stop))
                    server_thread = threading.Thread(target=service.serve_forever)
                    worker.start()
                    server_thread.start()
                    try:
                        endpoint = f"http://127.0.0.1:{service.server_port}"
                        first = research_adapter.submit(event, endpoint, token)
                        again = research_adapter.submit(event, endpoint, token)
                        self.assertEqual(first["receipt"], again["receipt"])
                        for _ in range(100):
                            status = ingest.receipt(private, first["receipt"])
                            if status["status"] == "filed":
                                break
                            time.sleep(0.05)
                        self.assertEqual(status["status"], "filed")
                        self.assertTrue(status["source_id"].startswith("SRC-"))
                        # Private intake MUST NOT silently appear in public search.
                        self.assertEqual(server.search({})["items"], [])
                        with closing(ingest.connect(private)) as db:
                            self.assertEqual(db.execute("SELECT COUNT(*) FROM registry").fetchone()[0], 1)
                            self.assertEqual(db.execute("SELECT COUNT(*) FROM relationships").fetchone()[0], 2)
                        # The projection is deliberately separate from automatic filing.
                        # No publication is performed by this test.
                    finally:
                        service.shutdown()
                        worker_stop.set()
                        worker.join(timeout=5)
                        server_thread.join(timeout=5)
            finally:
                server.DB = previous

if __name__ == "__main__":
    unittest.main()
