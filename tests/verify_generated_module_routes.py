"""Gate 2: inspect generated site files, not only source-code declarations.

Run after generate_uniform_site.py and publish_research_modules.py.
"""
import json,re
from pathlib import Path
root=Path(__file__).resolve().parents[1]
site=root/"site"
registry=json.loads((root/"collections/registry.json").read_text())
published=json.loads((site/"collections/registry.json").read_text())
assert published==registry,"Published registry differs from approved source"
expected={"timepiece":"labs/solarwinds-005/index.html",
          "glossary":"glossary.html",
          "research":"research/index.html",
          "source-hub":"source-hub/index.html"}
for cid,path in expected.items():
 target=site/path
 assert target.is_file(),f"{cid}: missing generated route {path}"
 content=target.read_text(encoding="utf-8")
 assert "<html" in content.lower(),f"{cid}: generated route is not HTML"
 assert len(content)>500,f"{cid}: generated page suspiciously short"
 print(f"PASS: {cid} generated route {path} ({len(content)} characters)")
for collection in published["collections"]:
 assert collection["page_size"]>0
 assert collection["route"].startswith("/")
assert (root/"labs/catalog.json").is_file(),"TIMEPIECE manifest missing"
# Source Hub is a static frontend; a production API must not be presumed.
source=(site/"source-hub/index.html").read_text(encoding="utf-8")
assert 'name="source-hub-api" content=""' in source,"Unexpected production API activation"
print("PASS: Gate 2 published module routes, shared registry, and unconfigured hosted API verified")
