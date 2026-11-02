"""Apply only the reviewed fragment targets to the reconstructed QA copy."""
from pathlib import Path
import hashlib, json
SOURCE = "d2788ea5a9783766edfb6862a3046ebb3ff11b97"
EXPECTED = "f204f7b9ddd84de79a8eca0817eb71154dc64c369a0fea01c67ee125393a4d8f"
changes = []
for name in ("index.html", "Binance_First_Case_Study_Free.html"):
    p = Path("site/case-studies") / name
    original = p.read_bytes()
    assert hashlib.sha256(original).hexdigest() == EXPECTED, f"Unexpected input: {p}"
    text = original.decode("utf-8")
    for anchor, section in (("case-studies", "index-view"), ("binance", "article-view")):
        marker = f'<section id="{section}"'
        assert text.count(marker) == 1 and f'id="{anchor}"' not in text
        text = text.replace(marker, f'<span id="{anchor}"></span>' + marker, 1)
    p.write_bytes(text.encode("utf-8"))
    changes.append({"path": str(p), "before_sha256": EXPECTED,
                    "after_sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
Path("navigation-repair.json").write_text(json.dumps({
    "controlled_source_commit": SOURCE,
    "scope": "QA reconstruction only; original archive unchanged; no deployment",
    "changes": changes}, indent=2), encoding="utf-8")
print("PASS: four fragment targets added; eight navigation references repaired")

# Record the patched QA tree separately from the original reconstruction manifest.
manifest = {p.relative_to(Path("site")).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in Path("site").rglob("*") if p.is_file()}
Path("qa-site-manifest.json").write_text(json.dumps({
    "controlled_source_commit": SOURCE, "files": manifest}, indent=2), encoding="utf-8")
