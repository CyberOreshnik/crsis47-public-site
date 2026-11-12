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
css += "\n/* Design A: isolated replacement of the English homepage presentation */\nbody.crsis47-design-a #root{display:none!important}\nbody.crsis47-design-a{margin:0;background:#030d1c!important;color:#fff4d8!important}\n.crsis47-design-a-page{font-family:Georgia,'Times New Roman',serif;background:linear-gradient(130deg,#020a18,#09233a 55%,#020a18);color:#fff2d6;min-height:100vh}\n.crsis47-da-header{display:flex;align-items:center;justify-content:space-between;gap:22px;padding:12px clamp(18px,3vw,54px);border-bottom:2px solid #c99836;background:#020c1b;flex-wrap:wrap}\n.crsis47-da-brand{display:flex;align-items:center;gap:12px;color:#f5cf79;text-decoration:none;font-size:clamp(21px,2.2vw,33px);font-weight:bold}\n.crsis47-da-brand img{width:54px;height:54px;object-fit:contain}\n.crsis47-da-brand small{display:block;font-size:11px;letter-spacing:.13em}\n.crsis47-da-nav{display:flex;gap:clamp(12px,2vw,30px);flex-wrap:wrap}\n.crsis47-da-nav a,.crsis47-da-footer a{color:#fff2d6;text-decoration:none;font:16px Arial,sans-serif}\n.crsis47-da-nav a:hover,.crsis47-da-footer a:hover{text-decoration:underline;color:#ffcf67}\n.crsis47-da-hero{display:grid;grid-template-columns:minmax(200px,.85fr) minmax(280px,1.15fr) minmax(270px,.95fr);align-items:center;gap:28px;padding:44px clamp(22px,4vw,70px);background:radial-gradient(circle at 70% 45%,#123e68 0%,#031022 55%,#020915 100%);border-bottom:1px solid #a97828}\n.crsis47-da-emblem{width:100%;max-width:410px;max-height:430px;object-fit:contain;filter:drop-shadow(0 0 24px #bc842f)}\n.crsis47-da-heading{border-left:3px solid #dca53c;padding-left:22px}\n.crsis47-da-heading h1{font-size:clamp(34px,4.2vw,68px);line-height:1.06;margin:0 0 26px;color:#ffdf9a}\n.crsis47-da-heading p{font-size:clamp(16px,1.7vw,24px);line-height:1.4}\n.crsis47-da-theory{border:2px solid #c99437;border-radius:15px;background:#020a14e8;padding:22px;box-shadow:0 0 25px #bd8b2833}\n.crsis47-da-theory h2{font-size:clamp(22px,2vw,30px);color:#ffdc8b;margin:0 0 12px}\n.crsis47-da-theory p,.crsis47-da-theory li{font:15px/1.45 Arial,sans-serif}\n.crsis47-da-theory ul{padding-left:20px}\n.crsis47-da-capabilities{display:flex;justify-content:center;flex-wrap:wrap;gap:12px 26px;padding:20px;background:#06182a;border-bottom:1px solid #bc8b3c;font:14px Arial,sans-serif;color:#f6d78d}\n.crsis47-da-studies{padding:34px clamp(18px,4vw,65px) 54px}\n.crsis47-da-studies h2{text-align:center;color:#ffe2a3;font-size:clamp(28px,3vw,44px);margin:0 0 28px}\n.crsis47-da-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:18px}\n.crsis47-da-card{border:2px solid #b78a3e;border-radius:14px;overflow:hidden;background:linear-gradient(#0b233a,#020c19);display:flex;flex-direction:column}\n.crsis47-da-card-top{height:130px;display:flex;align-items:center;justify-content:center;background:linear-gradient(130deg,#092c4d,#05101c);font-size:36px;color:#d7a33b}\n.crsis47-da-card-body{padding:18px;display:flex;flex-direction:column;flex:1}\n.crsis47-da-card h3{font-size:clamp(19px,1.8vw,27px);margin:8px 0;color:#fff}\n.crsis47-da-card p{font:15px/1.45 Arial,sans-serif;color:#f2e7d4;flex:1}\n.crsis47-da-card a,.crsis47-da-card .status{display:block;text-align:center;padding:12px 8px;border-radius:8px;background:#123b30;border:1px solid #d6aa48;color:#fff2ca;text-decoration:none;font:bold 14px Arial,sans-serif}\n.crsis47-da-card .status{background:#aa8138;color:#06111c}\n.crsis47-da-all{display:block;max-width:290px;margin:28px auto 0;padding:13px;text-align:center;background:linear-gradient(#f2c65d,#a86b08);border-radius:9px;color:#06101e;font:bold 17px Arial,sans-serif;text-decoration:none}\n.crsis47-da-research{padding:35px clamp(20px,4vw,70px);border-top:1px solid #b98a36;background:#071c30}\n.crsis47-da-research h2{font-size:32px;color:#f4d185}\n.crsis47-da-research a{color:#ffe1a4}\n.crsis47-da-footer{display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap;padding:30px 5%;border-top:2px solid #d6a54b;background:#020b17}\n@media(max-width:1000px){.crsis47-da-hero{grid-template-columns:1fr 1fr}.crsis47-da-theory{grid-column:1/-1}.crsis47-da-grid{grid-template-columns:repeat(2,1fr)}}\n@media(max-width:600px){.crsis47-da-hero{grid-template-columns:1fr}.crsis47-da-emblem{max-height:250px}.crsis47-da-grid{grid-template-columns:1fr}.crsis47-da-header{justify-content:center}}\n"
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

  if(home()){
    document.body.classList.add('crsis47-design-a');
    if(!document.getElementById('crsis47-design-a-page')){
      const page=make('div','crsis47-design-a-page');page.id='crsis47-design-a-page';
      page.innerHTML=`
<header class="crsis47-da-header"><a class="crsis47-da-brand" href="/crsis47-public-site/"><img src="${image}" alt="Approved standalone CRSIS-47 shield"><span>CRSIS-47<small>THE EVIDENCE CHAMBER</small></span></a><nav class="crsis47-da-nav" aria-label="Main navigation"><a href="/crsis47-public-site/">Home</a><a href="/crsis47-public-site/case-studies/index.html">Case Studies</a><a href="/crsis47-public-site/books/">Books</a><a href="/crsis47-public-site/research/">Research</a><a href="/crsis47-public-site/resources/">Resources</a><a href="/crsis47-public-site/about/">About</a><a href="/crsis47-public-site/contact/">Contact</a></nav></header>
<main><section class="crsis47-da-hero"><img class="crsis47-da-emblem" src="${image}" alt="CRSIS-47 Evidence Chamber institutional shield"><div class="crsis47-da-heading"><h1>A question.<br>A threshold.<br>What comes next?</h1><p>The Standard is Excellence.<br>The Method is Execution.<br>The Goal is Completion.</p></div><aside class="crsis47-da-theory"><h2>THE CRSIS-47 THEORY</h2><p>A governed, evidence-driven framework for rapid and trustworthy cyber incident assessment.</p><ul><li>Progressive Testing (T+0 → T+47)</li><li>MALICIOUS · BENIGN · UNCERTAIN</li><li>Containment recommendation target under 60 seconds</li><li>TTCD from the scenario clock</li><li>NIST, ATT&CK, D3FEND and NIST AI RMF</li></ul></aside></section>
<div class="crsis47-da-capabilities"><span>Agentic Cyber Defense</span><span>Identity Telemetry</span><span>Knowledge Graph</span><span>Digital Twin</span><span>Privacy-Preserving Learning</span><span>Governed Response</span></div>
<section class="crsis47-da-studies"><h2>CRSIS-47 CASE STUDY SERIES</h2><div class="crsis47-da-grid">
<article class="crsis47-da-card"><div class="crsis47-da-card-top">001</div><div class="crsis47-da-card-body"><h3>Binance</h3><p>A test of trust, control, and decision speed.</p><a href="/crsis47-public-site/case-studies/index.html">Read Free Case Study</a></div></article>
<article class="crsis47-da-card"><div class="crsis47-da-card-top">002</div><div class="crsis47-da-card-body"><h3>Leadership Under Uncertainty</h3><p>The Russia–Ukraine false-alarm crisis.</p><a href="https://payhip.com/b/kvM9I">Professional Edition — $5</a></div></article>
<article class="crsis47-da-card"><div class="crsis47-da-card-top">003</div><div class="crsis47-da-card-body"><h3>FORTRESS America</h3><p>A 90-day resilience plan under review.</p><a href="https://payhip.com/b/wym8f">Professional Edition — $5</a></div></article>
<article class="crsis47-da-card"><div class="crsis47-da-card-top">004</div><div class="crsis47-da-card-body"><h3>The CrowdStrike Outage</h3><p>A non-malicious failure with global consequences.</p><span class="status">In Development</span></div></article>
</div><a class="crsis47-da-all" href="/crsis47-public-site/case-studies/index.html">Explore All Case Studies</a></section>
<section class="crsis47-da-research"><h2>Research &amp; Laboratories</h2><p>CRSIS-47 Research Program · Computer-Security Investigation · Research Labs &amp; Prototypes · Methodology, Validation &amp; Research Progress</p><a href="/crsis47-public-site/research/">Explore research</a></section></main>
<footer class="crsis47-da-footer"><strong>CRSIS-47 · THE EVIDENCE CHAMBER</strong><span>Evidence &nbsp; | &nbsp; Assessment &nbsp; | &nbsp; Decision &nbsp; | &nbsp; Response</span><span><a href="/crsis47-public-site/contact/">Contact</a> &nbsp; | &nbsp; <a href="/crsis47-public-site/">Home</a></span></footer>`;
      document.body.append(page);
    }
    return;
  }
  document.body.classList.remove('crsis47-design-a');
  document.getElementById('crsis47-design-a-page')?.remove();

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
<article><span>001 · COMPLIMENTARY</span><h3>Binance</h3><p>Incident response and evidence assessment.</p><a href="/crsis47-public-site/case-studies/index.html">Read free case study</a></article>
<article><span>002 · PROFESSIONAL EDITION · $5</span><h3>Leadership Under Uncertainty</h3><p>Leadership decisions under evolving evidence.</p><a href="https://payhip.com/b/kvM9I">View professional edition</a></article>
<article><span>003 · PROFESSIONAL EDITION · $5</span><h3>FORTRESS America</h3><p>Assessing a reported 90-day resilience commitment.</p><a href="https://payhip.com/b/wym8f">View professional edition</a></article>
<article><span>004 · IN DEVELOPMENT</span><h3>CrowdStrike Outage</h3><p>Cyber resilience and the consequences of non-malicious failure.</p><a href="/crsis47-public-site/case-studies/index.html">Explore the series</a></article>
</div><p class="crsis47-case-all"><a href="/crsis47-public-site/case-studies/index.html">Explore all case studies and available languages</a></p>`;
      const first=main.querySelector('section');
      if(first)first.insertAdjacentElement('afterend',section);else main.prepend(section);
    }
  }
  // The original homepage already displays T+47 prominently; do not add a second dial.
  document.getElementById('crsis47-t47-research-panel')?.remove();
  const signature=document.getElementById('crsis47-evidence-footer');
  if(!home()){signature?.remove();return}
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
manifest["evidence_chamber"]={"approval_date":"2026-11-10","placements":["navigation header","homepage case-study progression","footer final signature"],"source_sha256":expected}
manifest_path.write_text(json.dumps(manifest,indent=2),encoding="utf8")
print("PASS: approved assets validated; Design A homepage integrated")
