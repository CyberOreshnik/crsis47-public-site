import os
import unittest
from unittest.mock import patch

from codex_research_gate3 import PRIMARY, source_use
import research_adapter
import source_policy

class PolicyTests(unittest.TestCase):
    def test_explicit_opt_in_and_exact_policy(self):
        entries = source_policy.load()
        self.assertEqual(len(entries), 3)
        for entry in entries.values():
            event = source_use(entry, "a" * 64, PRIMARY)
            with patch.dict(os.environ, {"SOURCE_HUB_GATE3_PUBLIC": "0"}):
                with self.assertRaisesRegex(ValueError, "gate3_source_not_authorized"):
                    research_adapter.make_event(event)
            with patch.dict(os.environ, {"SOURCE_HUB_GATE3_PUBLIC": "1"}):
                accepted = research_adapter.make_event(event)
                self.assertEqual(accepted["publication_date"], entry["publication_date"])
                for change in ({"source_url": entry["url"] + "?alternate=1"},
                               {"title": "different document"}, {"classification": "RESTRICTED"},
                               {"claim_ids": ["UNRELATED"]}, {"project_ids": ["UNRELATED"]},
                               {"external_ids": [entry["id"]]}, {"preservation_requested": True}):
                    with self.subTest(change=change), self.assertRaises(ValueError):
                        research_adapter.make_event(dict(event, **change))

if __name__ == "__main__":
    unittest.main()
