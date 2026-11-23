"""Codex's explicit synthetic research-use filing command.

Run after selecting a synthetic source for use in a research task. Requires
a locally running intake worker. Never silently drops failures or publishes.
"""
import argparse
import json
import os
from pathlib import Path
import time
from urllib.request import Request
import re

import research_adapter

def wait_for_receipt(endpoint, token, receipt, timeout=15):
    if not re.fullmatch(r"[a-f0-9]{32}", receipt):
        raise ValueError("invalid filing receipt")
    target = research_adapter.intake_origin(endpoint) + "/api/source-events/" + receipt
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        request = Request(target, headers={"Authorization": "Bearer " + token})
        with research_adapter.open_intake(request, timeout=5) as response:
            status = json.load(response)
        if status["status"] == "filed":
            return status
        if status["status"] == "failed":
            raise RuntimeError("Source Hub filing failed: " + str(status.get("error")))
        time.sleep(0.1)
    raise TimeoutError("Source Hub receipt still pending: " + receipt)

def capture_event(record, endpoint, token):
    event = research_adapter.make_event(record)
    result = research_adapter.submit(event, endpoint, token)
    if not isinstance(result.get("receipt"), str):
        raise RuntimeError("Intake did not return a filing receipt")
    return wait_for_receipt(endpoint, token, result["receipt"])

def capture(record_path, endpoint, token):
    return capture_event(json.loads(Path(record_path).read_text(encoding="utf-8")), endpoint, token)

def main():
    parser = argparse.ArgumentParser(description="File a synthetic Codex research source in local Source Hub")
    parser.add_argument("record", help="Synthetic SOURCE_USED JSON record")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8766")
    args = parser.parse_args()
    token = os.environ.get("SOURCE_HUB_INTAKE_TOKEN")
    result = capture(args.record, args.endpoint, token)
    print(json.dumps({"status": result["status"], "source_id": result["source_id"],
                      "receipt": result["receipt"]}))

if __name__ == "__main__":
    main()
