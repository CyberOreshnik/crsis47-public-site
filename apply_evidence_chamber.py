"""Integrate the approved Evidence Chamber identity into the built static site.
Fail closed if the owner-approved artwork is absent. Do not change case-study or checkout links.
"""
from pathlib import Path
import hashlib,json,re
site=Path("site")
expected_hash=json.loads(Path("brand/evidence-chamber/approved-artwork-manifest.json").read_text())["header_shield"]["sha256"]
source=Path("brand/evidence-chamber/crsis47-header-shield-approved.png")
assert source.is_file(), "Approved shield source PNG missing: do not deploy placeholders"
asset=site/"assets/brand/crsis47-header-shield-approved.png"
asset.parent.mkdir(parents=True,exist_ok=True)
assert hashlib.sha256(source.read_bytes()).hexdigest()==expected_hash, "Source PNG checksum mismatch"
asset.write_bytes(source.read_bytes())
assert asset.is_file(), "Approved shield asset missing: do not deploy placeholders"
expected=expected_hash
assert hashlib.sha256(asset.read_bytes()).hexdigest()==expected,"Shield image does not match approved original"
closing_source=Path("brand/evidence-chamber/crsis47-closing-composition-approved.png")
closing_expected=json.loads(Path("brand/evidence-chamber/approved-artwork-manifest.json").read_text())["closing_composition"]["sha256"]
assert closing_source.is_file() and hashlib.sha256(closing_source.read_bytes()).hexdigest()==closing_expected, "Approved closing composition missing or mismatched"
closing_asset=site/"assets/brand/crsis47-closing-composition-approved.png"
closing_asset.write_bytes(closing_source.read_bytes())
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
const image=root+'assets/brand/crsis47-header-shield-approved.png';
const closing=root+'assets/brand/crsis47-closing-composition-approved.png';
const home=()=>['/crsis47-public-site/','/crsis47-public-site/index.html'].includes(location.pathname);
const make=(tag,cls)=>{const e=document.createElement(tag);e.className=cls;return e};
const add=()=>{
  const header=document.querySelector('header');
  const old=document.getElementById('crsis47-evidence-nav');
  if(old)old.remove();
  if(header&&!header.querySelector('.crsis47-header-shield')){
    const links=[...header.querySelectorAll('a')];
    const brand=links.find(a=>{try{return new URL(a.href).pathname.replace(/index\\.html$/,'')===root}catch{return false}}) || links.find(a=>/CRSIS/.test(a.textContent||''));
    if(brand){
      const img=document.createElement('img');img.src=image;img.alt='CRSIS-47 Evidence Chamber shield';img.className='crsis47-header-shield';img.width=38;img.height=38;img.decoding='async';
      brand.classList.add('crsis47-header-brand-link');brand.prepend(img);
    }
  }
  const panel=document.getElementById('crsis47-t47-research-panel');
  const signature=document.getElementById('crsis47-evidence-footer');
  if(!home()){panel?.remove();signature?.remove();return}
  const main=document.querySelector('main');
  if(main&&!panel&&!main.querySelector('.crsis47-t47-panel')){
    const section=make('section','crsis47-t47-panel');section.id='crsis47-t47-research-panel';section.setAttribute('aria-label','T plus 47 assessment protocol');
    const dial=make('div','crsis47-t47-dial');
    const mark=make('strong','crsis47-t47-mark');mark.textContent='T+47';
    const caption=make('span','crsis47-t47-caption');caption.textContent='ASSESSMENT PROTOCOL';
    dial.append(mark,caption);section.append(dial);
    const first=main.querySelector('section');
    if(first)first.insertAdjacentElement('afterend',section);else main.prepend(section);
  }
  const footer=document.querySelector('footer');
  if(footer&&!signature){
    const wrap=make('div','crsis47-evidence-footer-signature');wrap.id='crsis47-evidence-footer';
    const img=document.createElement('img');img.src=closing;img.alt='CRSIS-47 Evidence Chamber closing composition';img.decoding='async';img.loading='lazy';
    wrap.append(img);footer.insertAdjacentElement('afterend',wrap);
  }
};
let scheduled=false;const observer=new MutationObserver(()=>{if(scheduled)return;scheduled=true;requestAnimationFrame(()=>{scheduled=false;add()})});
observer.observe(document,{subtree:true,childList:true});
window.addEventListener('popstate',add);
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',add,{once:true});else add();
})();'''
(site/"evidence-chamber.js").write_text(js,encoding="utf8")
manifest_path=site/"deployment-manifest.json"
manifest=json.loads(manifest_path.read_text(encoding="utf8"))
for name in ["index.html","evidence-chamber.css","evidence-chamber.js","assets/brand/crsis47-header-shield-approved.png","assets/brand/crsis47-closing-composition-approved.png"]:
 manifest["files"][name]=hashlib.sha256((site/name).read_bytes()).hexdigest()
manifest["evidence_chamber"]={"approval_date":"2026-11-10","placements":["navigation header","homepage research panel","footer final signature"],"source_sha256":expected}
manifest_path.write_text(json.dumps(manifest,indent=2),encoding="utf8")
print("PASS: approved assets validated; header, T+47 research panel, and closing signature integrated")
