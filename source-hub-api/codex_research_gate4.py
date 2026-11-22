"""Use the Gate 3 research command's source policy and authenticated capture with a durable service."""
import argparse
import json
import os

import codex_capture
from codex_research_gate3 import PRIMARY, research, source_use
import source_policy

def run(endpoint, token, project_id=PRIMARY):
    entries = source_policy.load().values()
    for entry in entries:
        if project_id not in entry["relationships"]:
            raise ValueError("project is not approved for the selected sources")
        event = source_use(entry, research(entry), project_id)
        receipt = codex_capture.capture_event(event, endpoint, token)
        print(json.dumps({"policy_id": entry["id"], "source_url": entry["url"],
                          "finding": entry["use"], "source_id": receipt["source_id"],
                          "receipt": receipt["receipt"], "status": receipt["status"]}), flush=True)
        yield event, receipt

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="http://127.0.0.1:8766")
    parser.add_argument("--project", default=PRIMARY)
    args = parser.parse_args()
    try:
        from windows_security import configured_token
        token = configured_token()
        os.environ["SOURCE_HUB_GATE3_PUBLIC"] = "1"
        for _ in run(args.endpoint, token, args.project):
            pass
    except Exception as exc:
        raise SystemExit(f"Gate 4 research or filing failed ({type(exc).__name__}): {exc}") from None
