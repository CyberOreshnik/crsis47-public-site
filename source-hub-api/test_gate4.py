"""Gate 4 controlled acceptance, with live public sources and a separate synthetic crash database."""
from contextlib import closing, contextmanager
import json
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import threading
from urllib.error import HTTPError

import codex_capture
import codex_research_gate4
import ingest
import private_store
import project
import research_adapter
import server

@contextmanager
def service(path, token):
    with ingest.http_service(path, token, 0) as handler:
        stop = threading.Event()
        worker = threading.Thread(target=ingest.run_worker, args=(path, stop))
        http = threading.Thread(target=handler.serve_forever)
        worker.start()
        http.start()
        try:
            yield f"http://127.0.0.1:{handler.server_port}"
        finally:
            stop.set()
            handler.shutdown()
            worker.join()
            http.join()

def reject(event, endpoint, token):
    try:
        research_adapter.submit(research_adapter.make_event(event), endpoint, token)
    except HTTPError as exc:
        if exc.code == 400:
            exc.close()
            return
        raise
    raise AssertionError("suspended source unexpectedly accepted")

def crash_test(root):
    db_path = private_store.provision(root / "crash" / "registry.db")
    # Build a populated original schema at version 0, then migrate without rewriting its tables.
    with closing(sqlite3.connect(db_path)) as db:
        db.executescript(ingest.SCHEMA)
    fixture = json.loads((Path(__file__).parent / "synthetic-event.json").read_text(encoding="utf-8"))
    fixture = research_adapter.make_event(fixture)
    with closing(sqlite3.connect(db_path)) as db, db:
        db.execute("INSERT INTO intake_events(key,receipt,digest,payload,available) VALUES(?,?,?,?,0)",
                   ("migration-fixture", "0" * 32, "fixture", ingest.encode(fixture)))
    before = private_store.inspect(db_path)
    ingest.initialize(db_path)
    migrated = private_store.inspect(db_path)
    assert before["schema_version"] == 0 and migrated["schema_version"] == 1
    assert all(migrated["counts"][key] == count for key, count in before["counts"].items())
    assert ingest.receipt(db_path, "0" * 32)["status"] == "queued"
    # The child exits after actual writes and before the transaction can commit.
    code = """
import os, sys
import ingest
def interrupt(db, row):
    ingest.file_source(db, row)
    os._exit(43)
ingest.process_one(sys.argv[1], interrupt)
"""
    terminated = subprocess.run([sys.executable, "-c", code, str(db_path)],
                                cwd=Path(ingest.__file__).parent, timeout=15).returncode
    assert terminated == 43
    assert private_store.inspect(db_path) == migrated
    assert ingest.process_one(db_path) and not ingest.process_one(db_path)
    receipt = ingest.receipt(db_path, "0" * 32)
    assert receipt["status"] == "filed"
    assert private_store.inspect(db_path)["counts"]["registry"] == 1
    backup = root / "crash-backup" / "snapshot.db"
    restored = root / "crash-restore" / "registry.db"
    expected = private_store.copy_verified(db_path, backup)
    assert private_store.copy_verified(backup, restored) == expected
    assert ingest.receipt(restored, "0" * 32) == receipt
    try:
        private_store.copy_verified(backup, restored)
    except FileExistsError:
        assert private_store.inspect(restored) == expected
    else:
        raise AssertionError("restore overwrote an existing database")
    return {"migration": "0 to 1 with existing queued event", "process_exit": terminated,
            "queued_transaction_recovered": True, "synthetic_restore": expected}

def run(root):
    os.environ["SOURCE_HUB_GATE3_PUBLIC"] = "1"
    server.DB = str(root / "public.db")
    server.initialize()
    token = secrets.token_hex(32)
    path = private_store.provision(root / "private" / "registry.db")
    with service(path, token) as endpoint:
        filed = list(codex_research_gate4.run(endpoint, token))
    assert len(filed) == 3
    first = private_store.inspect(path)
    assert first["counts"]["registry"] == first["counts"]["intake_events"] == first["counts"]["audit"] == 3
    with service(path, token) as endpoint:
        for event, receipt in filed:
            actual = codex_capture.wait_for_receipt(endpoint, token, receipt["receipt"])
            assert actual == receipt
            assert codex_capture.capture_event(event, endpoint, token) == receipt
    assert private_store.inspect(path) == first
    event, receipt = filed[0]
    url = event["source_url"]
    private_store.govern(path, url, "approve", "Controlled public document approval")
    private_store.govern(path, url, "correct", "Verify reviewed title", {"title": event["title"]})
    private_store.govern(path, url, "suspend", "Controlled suspension test")
    with service(path, token) as endpoint:
        reject(dict(event, used_at=ingest.now()), endpoint, token)
        assert codex_capture.wait_for_receipt(endpoint, token, receipt["receipt"]) == receipt
    private_store.govern(path, url, "revoke", "Controlled revocation test")
    with service(path, token) as endpoint:
        reject(dict(event, used_at=ingest.now()), endpoint, token)
    backup = root / "backup" / "snapshot.db"
    restore = root / "restored" / "registry.db"
    expected = private_store.copy_verified(path, backup)
    assert expected["counts"]["control_audit"] == 4 and expected["counts"]["intake_events"] == 3
    assert private_store.copy_verified(backup, restore) == expected == private_store.inspect(path)
    with service(restore, token) as endpoint:
        for _, original in filed:
            assert codex_capture.wait_for_receipt(endpoint, token, original["receipt"]) == original
        reject(dict(event, used_at=ingest.now()), endpoint, token)
    assert not server.search({})["items"]
    sentinels = [token.encode(), b"RESTRICTED_GATE4_SYNTHETIC_MARKER"]
    try:
        ingest.enqueue(path, "restricted-test", dict(research_adapter.make_event(event),
                       classification="RESTRICTED", title=sentinels[1].decode()))
    except ValueError:
        pass
    else:
        raise AssertionError("restricted metadata accepted")
    for _, item in filed:
        sentinels.extend([item["source_id"].encode(), item["receipt"].encode()])
        try:
            project.approve_snapshot(path, item["source_id"])
        except ValueError as exc:
            assert str(exc) == "source_not_eligible"
        else:
            raise AssertionError("private source could be projected")
    site = Path("site")
    assert (site / "source-hub/index.html").is_file()
    for file in site.rglob("*"):
        if file.is_file():
            assert not file.name.endswith((".db", ".sqlite", ".sqlite3", "-wal", "-shm", "-journal"))
            content = file.read_bytes()
            assert not any(needle in content for needle in sentinels), str(file)
    return {"status": "passed", "restart": first, "restored": expected, "public_matches": 0,
            "suspension_and_revocation": "rejected, original receipt retained",
            "crash_test": crash_test(root), "private_files_in_build": 0}

if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="crsis47-gate4-") as root:
        print(json.dumps(run(Path(root).resolve()), indent=2))
