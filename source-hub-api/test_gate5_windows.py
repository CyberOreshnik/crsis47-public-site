"""Native Windows acceptance using disposable files and generated test credentials."""
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
from urllib.error import HTTPError

import codex_capture
import ingest
import private_store
import test_gate4
import windows_security

def rejected(action, error=ValueError):
    try:
        action()
    except error:
        return
    raise AssertionError("operation expected to fail was accepted")

def run(root):
    os.environ.pop("SOURCE_HUB_INTAKE_TOKEN", None)
    credential = root / "credential" / "intake.dpapi"
    os.environ["SOURCE_HUB_TOKEN_FILE"] = str(credential)
    rejected(windows_security.configured_token)
    windows_security.rotate(credential)
    old = windows_security.configured_token()
    assert old and old.encode() not in credential.read_bytes()
    report = test_gate4.run(root, old)
    registry = root / "private" / "registry.db"
    previous = private_store.inspect(registry)
    with closing(ingest.connect(registry)) as db:
        receipt = db.execute("SELECT receipt FROM intake_events WHERE status='filed' ORDER BY receipt LIMIT 1").fetchone()[0]
    windows_security.rotate(credential)
    new = windows_security.configured_token()
    assert new and new != old and new.encode() not in credential.read_bytes()
    with test_gate4.service(registry, new) as endpoint:
        try:
            codex_capture.wait_for_receipt(endpoint, old, receipt)
        except HTTPError as exc:
            assert exc.code == 401
            exc.close()
        else:
            raise AssertionError("rotated token accepted")
        assert codex_capture.wait_for_receipt(endpoint, new, receipt)["status"] == "filed"
    assert private_store.inspect(registry) == previous

    unsafe = root / "unsafe"
    unsafe.mkdir()
    rejected(lambda: private_store.provision(unsafe / "registry.db"))
    tampered = private_store.provision(root / "tampered" / "registry.db")
    subprocess.run(["icacls", str(tampered), "/grant", "*S-1-1-0:(R)"],
                   check=True, capture_output=True)
    rejected(lambda: private_store.private_path(tampered))

    corrupted = private_store.provision(root / "corrupt" / "snapshot.db")
    corrupted.write_bytes(b"DISPOSABLE CORRUPTED SQLITE BACKUP")
    failed_target = root / "no-restore" / "registry.db"
    rejected(lambda: private_store.copy_verified(corrupted, failed_target), sqlite3.DatabaseError)
    assert not failed_target.exists()
    recovered = root / "alternate-restore" / "registry.db"
    assert private_store.copy_verified(root / "backup" / "snapshot.db", recovered) == previous
    assert ingest.receipt(recovered, receipt) == ingest.receipt(registry, receipt)
    for path in Path("site").rglob("*"):
        if path.is_file():
            assert path.suffix.lower() != ".dpapi"
            content = path.read_bytes()
            assert new.encode() not in content and old.encode() not in content
    credential.write_text("invalid-protected-credential", encoding="ascii")
    rejected(windows_security.configured_token)
    return dict(report, platform="windows-native-ntfs", acl="inherited directory and broad file grant rejected",
                dpapi="same-user decrypt verified; invalid blob rejected",
                rotation="old token HTTP 401; new token retrieved intact receipt",
                corruption="damaged copy rejected; verified alternate backup restored")

if __name__ == "__main__":
    assert os.name == "nt", "Run on native Windows"
    with tempfile.TemporaryDirectory(prefix="crsis47-gate5-", dir=os.environ["LOCALAPPDATA"]) as directory:
        print(json.dumps(run(Path(directory).resolve()), indent=2))
