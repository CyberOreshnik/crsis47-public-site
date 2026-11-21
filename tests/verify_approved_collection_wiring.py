"""Regression contract for approved collection integration; does not mutate production."""
import json,re
from pathlib import Path
root=Path(__file__).resolve().parents[1]
registry=json.loads((root/"collections/registry.json").read_text())
collections={x["id"]:x for x in registry["collections"]}
generator=(root/"generate_uniform_site.py").read_text()
research=(root/"publish_research_modules.py").read_text()
for kind in ("books","case-studies"):
 assert collections[kind]["page_size"]==4
 assert collections[kind]["route"]=="/"+kind+"/"
 assert "COLLECTIONS[kind]['page_size']" in generator
 assert 'data-collection=' in generator
 assert 'data-page-size=' in generator
assert 'registered_collection("timepiece")["manifest"]' in research
assert 'write_page(registry_path, REGISTRY.read_text' in research
assert 'casecard(item,lang)' in generator and 'bookcard(item,lang)' in generator
assert 'faa_card()' in generator, "Approved unnumbered FAA edition must remain"
assert 'asset(b[\'cover\'])' in generator and 'asset(c[\'cover\'])' in generator
print("PASS: registry-driven collection metadata, four-item shelf, existing covers and FAA special edition retained")

# Catch accidental literal escaped newlines that can comment out required initialization.
assert "\\n    registry =" not in research
assert "\\n    labs = public_labs()" not in research
assert re.search(r"^    labs = public_labs\(\)$",research,re.M)
print("PASS: research build initialization is executable Python, not an escaped comment")
