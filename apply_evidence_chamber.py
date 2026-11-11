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
css += """
.crsis47-case-study-collection{max-width:1120px;margin:48px auto;padding:34px 24px;color:#172c29}
.crsis47-case-eyebrow{font-size:12px;letter-spacing:.16em;font-weight:700;color:#766029}
.crsis47-case-study-collection h2{font:normal clamp(30px,4vw,48px)/1.12 Georgia,serif;margin:12px 0 16px}
.crsis47-case-intro{max-width:720px;line-height:1.65;margin-bottom:25px}
.crsis47-case-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}
.crsis47-case-grid article{border:1px solid #c6b78f;background:#101e32;color:#f9f5e8;padding:26px;border-radius:8px}
.crsis47-case-grid article span{font-size:11px;letter-spacing:.09em;color:#e1c58b}
.crsis47-case-grid h3{font:normal 27px/1.2 Georgia,serif;margin:15px 0}
.crsis47-case-grid p{color:#e3e6e9;line-height:1.5}
.crsis47-case-grid a{color:#ffe0a0;font-weight:700;text-underline-offset:4px}
.crsis47-case-all{margin-top:20px;font-weight:700}
.crsis47-case-study-nav{font-weight:700}
@media(max-width:680px){.crsis47-case-grid{grid-template-columns:1fr}.crsis47-case-study-collection{padding:24px 16px}}
"""
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
  // Keep the approved case-study catalog discoverable in the existing navigation.
  if(header&&!header.querySelector('.crsis47-case-study-nav')){
    const nav=header.querySelector('nav');
    if(nav){
      const a=document.createElement('a');a.className='crsis47-case-study-nav';
      a.href=root+'case-studies/index.html';a.textContent='Case Studies 001–004';
      nav.prepend(a);
    }
  }
  const existingCases=document.getElementById('crsis47-case-study-collection');
  if(!home()){existingCases?.remove()}
  else if(!existingCases){
    const main=document.querySelector('main');
    if(main){
      const section=make('section','crsis47-case-study-collection');
      section.id='crsis47-case-study-collection';
      section.setAttribute('aria-labelledby','crsis47-case-study-heading');
      section.innerHTML=`<p class="crsis47-case-eyebrow">CRSIS-47 PROFESSIONAL CASE STUDIES</p>
<h2 id="crsis47-case-study-heading">Follow the evidence. Make the decision.</h2>
<p class="crsis47-case-intro">Explore the CRSIS-47 case-study progression, from incident assessment to leadership under uncertainty and operational resilience.</p>
<div class="crsis47-case-grid">
<article><span>001 · COMPLIMENTARY</span><h3>Binance</h3><p>Incident response and evidence assessment.</p><a href="/crsis47-public-site/case-studies/Binance_First_Case_Study_Free.html">Read free case study</a></article>
<article><span>002 · PROFESSIONAL EDITION · $5</span><h3>Leadership Under Uncertainty</h3><p>Leadership decisions under evolving evidence.</p><a href="https://payhip.com/b/kvM9I">View professional edition</a></article>
<article><span>003 · PROFESSIONAL EDITION · $5</span><h3>FORTRESS America</h3><p>Assessing a reported 90-day resilience commitment.</p><a href="https://payhip.com/b/wym8f">View professional edition</a></article>
<article><span>004 · IN DEVELOPMENT</span><h3>CrowdStrike Outage</h3><p>Cyber resilience and the consequences of non-malicious failure.</p><a href="/crsis47-public-site/case-studies/index.html">Explore the series</a></article>
</div><p class="crsis47-case-all"><a href="/crsis47-public-site/case-studies/index.html">Explore all case studies and available languages</a></p>`;
      const first=main.querySelector('section');
      if(first)first.insertAdjacentElement('afterend',section);else main.prepend(section);
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
