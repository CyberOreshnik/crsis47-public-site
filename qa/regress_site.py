#!/usr/bin/env python3
"""Non-deploying regression against reconstructed, checksum-verified website."""
from pathlib import Path
from html.parser import HTMLParser
import json, hashlib, sys
root=Path("site")
class Scan(HTMLParser):
 def __init__(self): super().__init__(); self.refs=[]; self.ids=set(); self.dupes=[]; self.lang=None; self.title=False
 def handle_starttag(self,tag,attrs):
  d=dict(attrs)
  if tag=="html": self.lang=d.get("lang")
  if "id" in d:
   if d["id"] in self.ids:self.dupes.append(d["id"])
   self.ids.add(d["id"])
  for k in ("href","src"):
   if d.get(k): self.refs.append(d[k])
issues=[]; counts={"html":0,"assets":0,"links":0}
for p in root.rglob("*.html"):
 counts["html"]+=1
 s=Scan()
 try:s.feed(p.read_text(encoding="utf-8"))
 except Exception as e:issues.append(f"{p}: parse error {e}");continue
 if s.dupes:issues.append(f"{p}: duplicate IDs {s.dupes}")
 for link in s.refs:
  if link.startswith(("https:","http:","mailto:","tel:","data:","javascript:","//")):continue
  target,_,frag=link.partition("#")
  target=target.split("?")[0]
  if target.startswith("/crsis47-public-site./"): dest=root/target[len("/crsis47-public-site./"):]
  elif target.startswith("/"): issues.append(f"{p}: unexpected root path {link}");continue
  elif target:dest=p.parent/target
  else:dest=p
  if target:
   if dest.is_dir():dest=dest/"index.html"
   if not dest.is_file():issues.append(f"{p}: missing local asset {link}");continue
   counts["assets"]+=1
  if frag and not target and frag not in s.ids:issues.append(f"{p}: missing fragment {link}")
  counts["links"]+=1
report={"status":"PASS" if not issues else "FAIL","counts":counts,"issues":issues[:250],"issue_count":len(issues)}
Path("qa-results.json").write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
if issues:sys.exit(1)
