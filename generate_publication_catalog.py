"""Generate additive, data-driven catalog pages without changing approved homepage or case-study pages."""
from pathlib import Path
from html import escape
import json, re
root=Path("site")
data=json.loads(Path("content/publications.json").read_text(encoding="utf-8"))
base="/crsis47-public-site"
assert data["schema_version"]==1
items=data["books"]+data["cases"]
assert len({i["id"] for i in items})==len(items)
assert all(i["kind"] in ("book","case-study") for i in items)
assert all(i["status"] in ("unpublished","free","available","in-development","planned","archived") for i in items)
assert all(not i.get("url") or i["url"].startswith(("https://","/crsis47-public-site/")) for i in items)
def card(i):
 title=escape(i["title"]); number=escape(i["number"]); status=escape(i["status"].replace("-"," ").title())
 desc=escape(i.get("description",""))
 href=i.get("url")
 action=('<a class="action" href="'+escape(href,quote=True)+'">'+("Purchase / Details" if i["status"]=="available" else "View details")+'</a>') if href else '<span class="pending">Details forthcoming</span>'
 cover=i.get("cover")
 img=('<img loading="lazy" alt="'+escape(title+' cover',quote=True)+'" src="'+escape(cover,quote=True)+'">') if cover else ''
 return '<article class="item">'+img+'<div><span class="meta">'+escape(i["kind"].title())+' '+number+' · '+status+'</span><h2>'+title+'</h2><p>'+desc+'</p>'+action+'</div></article>'
style="""<style>:root{color-scheme:light}*{box-sizing:border-box}body{margin:0;background:#f5f2e9;color:#15243a;font:16px/1.6 system-ui,Arial,sans-serif}a{color:inherit}a:focus-visible{outline:3px solid #a47725;outline-offset:3px}.wrap{max-width:1150px;margin:auto;padding:24px}header{background:#101e32;color:#fff}nav{display:flex;gap:24px;flex-wrap:wrap}nav a{padding:12px 0}h1{font:clamp(32px,5vw,55px) Georgia,serif}h2{font:26px Georgia,serif;margin:5px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,330px),1fr));gap:18px}.item{background:#fff;border:1px solid #d5c7a8;border-radius:8px;padding:20px;display:flex;gap:18px;min-height:185px}.item img{width:90px;height:138px;object-fit:cover;flex-shrink:0}.meta{font-size:12px;letter-spacing:.05em;text-transform:uppercase;color:#66552d}.item p{font-size:14px}.action{display:inline-block;background:#15243a;color:white;padding:9px 14px;border-radius:4px}.pending{font-size:13px;color:#555}footer{margin-top:40px;border-top:1px solid #d5c7a8} </style>"""
def page(title,entries):
 body=''.join(card(i) for i in entries)
 html='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+escape(title)+' | CRSIS-47</title><meta name="description" content="Browse the growing CRSIS-47 book and professional case-study collections.">'+style+'</head><body><header><div class="wrap"><strong>CRSIS-47 · THE EVIDENCE CHAMBER</strong><nav aria-label="Publication navigation"><a href="'+base+'/">Home</a><a href="'+base+'/collections/">All Publications</a><a href="'+base+'/books/">Books</a><a href="'+base+'/case-studies/">Case Studies</a></nav></div></header><main class="wrap"><h1>'+escape(title)+'</h1><p>Continuously expanding collection. Publication status is shown for each title.</p><div class="grid">'+body+'</div></main><footer><div class="wrap">CRSIS-47 · The Evidence Chamber</div></footer></body></html>'
 return html
for folder,title,entries in [("books","Books",data["books"]),("collections","Books & Case Studies",items)]:
 p=root/folder/"index.html";p.parent.mkdir(parents=True,exist_ok=True);p.write_text(page(title,entries),encoding="utf-8")
print("PASS: generated",len(data["books"]),"books and",len(data["cases"]),"case studies; approved homepage unchanged")
