"""Validate shared registry metadata without mutating frozen published pages."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
data=json.loads((root/"collections/registry.json").read_text())
assert data["schema_version"]==1
expected={"books","case-studies","timepiece","glossary","source-hub","research"}
entries=data["collections"]
assert {x["id"] for x in entries}==expected
assert len(entries)==len(expected)
routes=[x["route"] for x in entries]
assert len(routes)==len(set(routes))
for item in entries:
 assert item["route"].startswith("/") and ".." not in item["route"]
 assert 1<=item["page_size"]<=25
 assert item["status"] in {"existing","prototype","planned"}
 assert item["data_strategy"] in {"paged-manifest","manifest-then-on-demand-lab","indexed-api"}
 if "manifest" in item:
  assert (root/item["manifest"]).is_file()
print("PASS: six collection registry entries valid; planned entries are NOT yet integrated")
