"""Synthetic checks for the Gate 6 public payload scanner."""
from pathlib import Path
from tempfile import TemporaryDirectory
import zipfile

from gate6_close import scan

with TemporaryDirectory() as root:
    site = Path(root)
    (site / "source-hub").mkdir()
    (site / "source-hub/index.html").write_text("approved synthetic page", encoding="utf-8")
    assert scan(site) == {"status": "PASS", "files": 1, "findings": 0}
    (site / "asset.bin").write_bytes(b"SQLite format 3\x00")
    (site / "runtime.dpapi").write_bytes(b"synthetic")
    (site / "output.json").write_text("synthetic-local-marker", encoding="utf-8")
    (site / "payload.css").write_bytes(r"C:\Users\Synthetic\db".encode("utf-16-le"))
    with zipfile.ZipFile(site / "download.zip", "w") as archive:
        archive.writestr("data.sqlite-wal", "synthetic")
    assert scan(site, ["synthetic-local-marker"]) == {"status": "HOLD", "files": 6, "findings": 5}
print("PASS clean fixture and five planted findings")
