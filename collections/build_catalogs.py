"""Build reusable, independently paged public collection manifests.

Never rewrites approved site templates or cover images. Only published, explicitly
public records are eligible for the generated catalog. Default-deny.
"""
import argparse,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def build(root=ROOT):
 registry=json.loads((root/"collections/registry.json").read_text())
 out=root/"collections/generated"
 out.mkdir(parents=True,exist_ok=True)
 manifest={}
 for collection in registry["collections"]:
  cid=collection["id"]
  source=root/"collections/content"/(cid+".json")
  if not source.exists():
   continue
  items=json.loads(source.read_text())
  assert isinstance(items,list)
  ids=set()
  eligible=[]
  for item in items:
   assert isinstance(item,dict)
   assert re.fullmatch(r"[a-z0-9][a-z0-9-]{0,100}",item["id"])
   assert item["id"] not in ids,("duplicate",cid,item["id"])
   ids.add(item["id"])
   assert isinstance(item.get("title"),str) and item["title"].strip()
   assert isinstance(item.get("slug"),str) and re.fullmatch(r"[a-z0-9-]+",item["slug"])
   assert isinstance(item.get("language"),str) and item["language"]
   assert isinstance(item.get("version"),str) and item["version"]
   if item.get("visibility")=="public" and item.get("publication_status")=="published":
    eligible.append({k:item[k] for k in ("id","title","slug","language","version")})
  eligible.sort(key=lambda x:x["id"])
  size=collection["page_size"]
  pages=[]
  for start in range(0,len(eligible),size):
   filename=f"{cid}-{len(pages)+1:04d}.json"
   (out/filename).write_text(json.dumps({"collection":cid,"page":len(pages)+1,"items":eligible[start:start+size]},ensure_ascii=False,indent=2)+"\n")
   pages.append(filename)
  manifest[cid]={"count":len(eligible),"page_size":size,"pages":pages}
 (out/"index.json").write_text(json.dumps(manifest,indent=2)+"\n")
 return manifest
if __name__=="__main__":
 print(json.dumps(build(),indent=2))
