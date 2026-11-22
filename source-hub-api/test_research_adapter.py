"""Regression tests for the explicit synthetic research workflow adapter."""
import json
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_adapter

class ResearchAdapterTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads((Path(__file__).parent / "synthetic-event.json").read_text())

    def test_maps_and_deduplicates(self):
        event = research_adapter.make_event(self.record)
        self.assertEqual(event["event_type"], "SOURCE_USED")
        self.assertEqual(event["project_ids"], ["CASE-001", "CASE-002"])
        self.assertEqual(research_adapter.stable_key(event), research_adapter.stable_key(
            research_adapter.make_event(dict(self.record))))
        self.assertEqual(event["classification"], "REVIEW_REQUIRED")

    def test_rejects_real_and_restricted_sources(self):
        for updates in (
            {"source_url": "https://news.example.com/article"},
            {"evidence_type": "validator_record"},
            {"classification": "RESTRICTED", "evidence_type": "engineering_archive"},
        ):
            with self.subTest(updates=updates), self.assertRaises(ValueError):
                research_adapter.make_event(dict(self.record, **updates))

    def test_rejects_remote_host(self):
        event = research_adapter.make_event(self.record)
        with self.assertRaises(ValueError):
            research_adapter.submit(event, "https://api.example.org", "x" * 40)

    def test_no_implicit_network(self):
        with patch.object(research_adapter, "urlopen", side_effect=AssertionError("network invoked")):
            event = research_adapter.make_event(self.record)
            self.assertTrue(research_adapter.stable_key(event).startswith("research-"))

if __name__ == "__main__":
    unittest.main()
