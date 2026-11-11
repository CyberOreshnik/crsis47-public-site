"""Fail-closed recovery for CSS on audited GitHub Pages release.
Preserves approved page content, case-study catalog and Payhip destinations.
"""
from pathlib import Path
from urllib.parse import urlsplit
import re, hashlib, json
site=Path("site")
prefix="/crsis47-public-site/"
pages=[site/"index.html"]+list(site.glob("*/index.html"))
pages=[p for p in pages if p.is_file()]
assert (site/"case-studies/index.html").is_file()
modified=[]
for p in pages:
 text=p.read_text(encoding="utf-8")
 # Preserve content: only add inline fallback for existing LOCAL stylesheets.
 links=re.findall(r'<link\b[^>]*\brel=["\\']stylesheet["\\'][^>]*>',text,re.I)
 if not links:continue
 fallback=[]
 for tag in links:
  m=re.search(r'\bhref=["\\']([^"\\']+)',tag,re.I)
  if not m:continue
  href=m.group(1).split("?")[0]
  if href.startswith(("https:","http:","//","data:")):continue
  if href.startswith(prefix):asset=site/href[len(prefix):]
  elif href.startswith("/"):continue
  else:asset=p.parent/href
  assert asset.is_file(),f"Missing stylesheet: {p} -> {href}"
  css=asset.read_text(encoding="utf-8")
  # Rebase CSS relative asset URLs to canonical Pages path when inlined.
  cssdir=asset.parent.relative_to(site).as_posix()
  base=prefix+(cssdir+"/" if cssdir!="." else "")
  def rebase(m):
   quote=m.group(1);url=m.group(2).strip()
   if url.startswith(("data:","http:","https:","/","#")):return m.group(0)
   return "url("+quote+base+url+quote+")"
  css=re.sub(r'url\(\s*(["\\']?)([^)\\'"]+)\1\s*\)',rebase,css)
  css=css.replace("</style","<\/style")
  fallback.append(css)
 if fallback:
  assert "</head>" in text
  text=text.replace("</head>",'<style id="crsis47-critical-style-recovery">\n'+"\n".join(fallback)+"\n</style>\n</head>",1)
  p.write_text(text,encoding="utf-8")
  modified.append(str(p.relative_to(site)))
assert "crsis47-critical-style-recovery" in (site/"index.html").read_text(encoding="utf-8"),"No homepage stylesheet recovered"
# Validate protected case-study sales routes after the catalog overlay.
catalog=(site/"case-studies/index.html").read_text(encoding="utf-8")
for required in ["case-study-1","case-study-2-offer","case-study-3-offer","https://payhip.com/b/kvM9I","https://payhip.com/b/wym8f"]:
 assert required in catalog, f"Catalog missing {required}"
assert "/crsis47-public-site./" not in catalog
manifest=site/"deployment-manifest.json"
data=json.loads(manifest.read_text(encoding="utf-8"))
for name in modified:data["files"][name]=hashlib.sha256((site/name).read_bytes()).hexdigest()
data["style_recovery"]={"inlined_local_stylesheets":modified,"protected_checkout_links":["kvM9I","wym8f"]}
manifest.write_text(json.dumps(data,indent=2),encoding="utf-8")
print("PASS: inline stylesheet fallback on",len(modified),"homepages; case-study and checkout invariants preserved")
