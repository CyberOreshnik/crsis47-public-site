import json
import sqlite3
import unittest
from unittest.mock import patch

from publication_review import candidates, identity


class ReceiptReviewTest(unittest.TestCase):
    def test_review_requires_filed_current_policy_and_unique_public_identity(self):
        with sqlite3.connect(":memory:") as db:
            db.executescript("""
              CREATE TABLE registry(id, classification);
              CREATE TABLE intake_events(source_id, status, payload);
              CREATE TABLE source_controls(url, state);
              INSERT INTO registry VALUES ('candidate','REVIEW_REQUIRED'),('secret','RESTRICTED');
            """)
            base = dict(originating_workflow="codex-gate3-public", evidence_type="book",
                        title="Public book", authors=["Author"], publisher="Publisher",
                        publication_date="2023-06", doi="10.1000/book",
                        external_ids=["private"], claim_ids=["private"])
            def add(url, doi, *, status="filed", source="candidate", **fields):
                event = dict(base, source_url="https://example.org/" + url, **fields)
                event["doi"] = doi
                db.execute("INSERT INTO intake_events VALUES (?,?,?)", (source, status, json.dumps(event)))
            add("pending", None, status="queued")
            add("secret", None, source="secret")
            add("withdrawn", None)
            add("old", None, project_ids=["CRSIS47-GATE3"])
            add("invalid", None, invalid=True)
            add("existing", None)
            add("doi-alias", "10.1000/already")
            add("future", "10.1000/book")
            add("same-book", "10.1000/BOOK")
            add("future/", None)
            db.execute("INSERT INTO source_controls VALUES (?,?)", ("https://example.org/withdrawn","suspended"))

            def validate(event):
                if event.get("invalid"):
                    raise ValueError("outdated policy")

            published = identity("https://example.org/existing/", "10.1000/ALREADY")
            with patch("publication_review.source_policy.validate_event", side_effect=validate):
                result = candidates(db, published)
                self.assertEqual(result, candidates(db, published))
            self.assertEqual([row["url"] for row in result], ["https://example.org/future"])
            self.assertEqual(set(result[0]), {"url","title","authors","publisher","publication_date","doi","evidence_type"})


if __name__ == "__main__":
    unittest.main()
