"""Verify the generated site cannot carry intake files or synthetic fixture payloads."""
from pathlib import Path

site = Path("site")
hub = site / "source-hub/index.html"
assert hub.is_file(), "Build site/ before checking the boundary"
assert 'name="source-hub-api" content=""' in hub.read_text(encoding="utf-8")
for file in site.rglob("*"):
    if not file.is_file():
        continue
    assert not {"source-hub-api", ".git"}.intersection(file.parts), file
    assert not file.name.endswith((".db", ".db-wal", ".db-shm", ".sqlite", ".sqlite3", ".pem", ".key")), file
    assert file.name not in {".env", "synthetic-event.json", "registry.schema.json"}, file
    if file.suffix.lower() in {".html", ".json", ".js", ".mjs"}:
        data = file.read_bytes()
        assert b"SOURCE_HUB_INTAKE_TOKEN" not in data, file
        assert b"example.org/synthetic/demo" not in data, file
print("PASS: generated Source Hub uses static fallback and contains no intake files or synthetic fixture marker")
