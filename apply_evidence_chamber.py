"""Integrate the approved Evidence Chamber identity into the built static site.
Fail closed if the owner-approved artwork is absent. Do not change case-study or checkout links.
"""
from pathlib import Path
import hashlib,json,re
site=Path("site")
source=Path("brand/evidence-chamber/crsis47-evidence-chamber-approved.png")
assert source.is_file(), "Approved shield source PNG missing: do not deploy placeholders"
asset=site/"assets/brand/crsis47-evidence-chamber-approved.png"
asset.parent.mkdir(parents=True,exist_ok=True)
asset.write_bytes(source.read_bytes())
assert asset.is_file(), "Approved shield asset missing: do not deploy placeholders"
expected="178737391e814ee911de2082573c8d6986f3dada748ef2f2c2050017988b8ee0"
assert hashlib.sha256(asset.read_bytes()).hexdigest()==expected,"Shield image does not match approved original"
root="/crsis47-public-site/"
css=(Path("brand/evidence-chamber/evidence-chamber.css").read_text(encoding="utf8"))
(site/"evidence-chamber.css").write_text(css,encoding="utf8")
# Inject only on English home page, preserving existing React application and links.
p=site/"index.html"
html=p.read_text(encoding="utf8")
assert "</head>" in html and "</body>" in html
style=f'<link rel="stylesheet" href="{root}evidence-chamber.css">'
script=f'<script src="{root}evidence-chamber.js" defer></script>'
assert "evidence-chamber.js" not in html
html=html.replace("</head>",style+"</head>").replace("</body>",script+"</body>")
p.write_text(html,encoding="utf8")
# Additive DOM insertion only, with MutationObserver for React hydration.
# The observer keeps existing React-controlled navigation, content, and purchase links untouched.
js=r'''(() => {
const root='/crsis47-public-site/';
const image=root+'assets/brand/crsis47-evidence-chamber-approved.png';
const make=(tag,cls)=>{const e=document.createElement(tag);e.className=cls;return e};
const logo=(alt,width)=>{const i=document.createElement('img');i.src=image;i.alt=alt;i.width=width;i.decoding='async';return i};
const add=()=>{
  const header=document.querySelector('header');
  if(header&&!document.getElementById('crsis47-evidence-nav')){
    const a=make('a','crsis47-brand crsis47-brand--nav');a.id='crsis47-evidence-nav';a.href=root;a.setAttribute('aria-label','CRSIS-47 home');
    a.append(logo('',48));header.prepend(a);
  }
  const main=document.querySelector('main');
  if(main&&!document.getElementById('crsis47-evidence-hero')){
    const hero=make('div','crsis47-brand-hero');hero.id='crsis47-evidence-hero';
    hero.append(logo('CRSIS-47 — The Evidence Chamber',300));
    const p=make('p','crsis47-brand-hero__caption');p.textContent='WHERE EVIDENCE BECOMES JUDGMENT';hero.append(p);const first=main.firstElementChild; if(first)first.insertAdjacentElement('afterend',hero);else main.append(hero);
  }
  const footer=document.querySelector('footer');
  if(footer&&!document.getElementById('crsis47-evidence-footer')){
    const div=make('div','crsis47-brand crsis47-brand--footer');div.id='crsis47-evidence-footer';div.append(logo('',64));
    const s=document.createElement('span');s.textContent='CRSIS-47 · THE EVIDENCE CHAMBER';div.append(s);footer.prepend(div);
  }
};
const observer=new MutationObserver(add);observer.observe(document,{subtree:true,childList:true});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',add,{once:true});else add();
})();'''
(site/"evidence-chamber.js").write_text(js,encoding="utf8")
manifest_path=site/"deployment-manifest.json"
manifest=json.loads(manifest_path.read_text(encoding="utf8"))
for name in ["index.html","evidence-chamber.css","evidence-chamber.js","assets/brand/crsis47-evidence-chamber-approved.png"]:
 manifest["files"][name]=hashlib.sha256((site/name).read_bytes()).hexdigest()
manifest["evidence_chamber"]={"approval_date":"2026-11-10","placements":["homepage hero","navigation header","footer"],"source_sha256":expected}
manifest_path.write_text(json.dumps(manifest,indent=2),encoding="utf8")
print("PASS: owner-approved shield hash validated and homepage identity integrated")
