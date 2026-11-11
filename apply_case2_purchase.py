"""Add the approved Payhip offer without changing archived releases or downloads."""
from pathlib import Path
import hashlib,json
site=Path('site')
url='https://payhip.com/b/kvM9I'
card='''<section id="case-study-2-offer" lang="en" dir="ltr" aria-labelledby="case2-title" style="max-width:1100px;margin:64px auto;padding:40px 28px;background:#101e32;color:#fff;border:1px solid #c7a768;border-radius:12px;box-sizing:border-box"><p style="color:#e1c58b;letter-spacing:.12em;font-size:.8rem;text-transform:uppercase">CRSIS-47 · Case Study 002 · Professional Edition</p><h2 id="case2-title" style="color:#fff;font-size:clamp(1.8rem,4vw,2.8rem);line-height:1.2;margin:16px 0">Leadership Under Uncertainty</h2><p style="font-size:1.1rem;line-height:1.7;max-width:760px">Explore leadership decisions under uncertainty with this cybersecurity case study and its accompanying learning materials.</p><p style="line-height:1.7">By Constantin Jean-Pierre · English edition · Digital download</p><a href="https://payhip.com/b/kvM9I" style="display:inline-block;background:#e1c58b;color:#101e32;padding:15px 24px;border-radius:5px;font-weight:700;text-decoration:underline;text-underline-offset:4px">Get the Professional Edition — $5 USD</a><p style="font-size:.9rem;line-height:1.6;margin-top:18px">Purchase and download through Payhip. Any applicable taxes are shown at checkout.</p></section>'''
# Keep the existing React-rendered release intact: add the offer after hydration.
js='''(() => { const add = () => { if(!location.pathname.includes('/case-studies/')) { document.getElementById('case-study-2-offer')?.remove(); return; } if(document.getElementById('case-study-2-offer')) return; const main=document.querySelector('main'); if(!main) return; const holder=document.createElement('div'); holder.innerHTML=CARD; main.appendChild(holder.firstElementChild); if(location.hash==='#case-study-2-offer') document.getElementById('case-study-2-offer').scrollIntoView(); }; const observer=new MutationObserver(add); observer.observe(document,{childList:true,subtree:true}); if(document.readyState==='complete') add(); else window.addEventListener('load',add,{once:true}); })();'''.replace('CARD',json.dumps(card))
(site/'case2-offer.js').write_text(js,encoding='utf8')
# Discoverability across existing site pages, preserving every locale's content.
changed=[]
for p in site.rglob('*.html'):
 text=p.read_text(encoding='utf8')
 relative=p.relative_to(site)
 is_home=relative.name=='index.html' and (len(relative.parts)==1 or (len(relative.parts)==2 and relative.parts[0] in {'fr','ht','es','pt-BR','pt-PT','ru','ar','zh-Hans','zh-Hant','ja','fa','he','tr'}))
 is_case=relative.parts[0]=='case-studies'
 if '<main' not in text or not (is_case): continue
 tag='<script src="/crsis47-public-site/case2-offer.js?v=4" defer></script>'
 if tag not in text:
  assert '</body>' in text
  text=text.replace('</body>',tag+'</body>')
  p.write_text(text,encoding='utf8');changed.append(str(p.relative_to(site)))
# Case-study classroom pages use article layouts rather than main.
for p in (site/'case-studies').rglob('index.html'):
 text=p.read_text(encoding='utf8')
 if '<main' not in text and 'id="case-study-2-offer"' not in text:
  text=text.replace('</body>',card+'</body>');p.write_text(text,encoding='utf8');changed.append(str(p.relative_to(site)))
catalog=site/'case-studies/index.html'
catalog.write_bytes(Path('case_studies_catalog.html').read_bytes())
changed.append('case-studies/index.html')
# Clean visibly corrupted navigation glyphs in retained classroom pages.
for p in (site/'case-studies').rglob('*.html'):
 text=p.read_text(encoding='utf8')
 fixed=text.replace('Author website ?', 'Author website').replace('class="arrow" aria-hidden="true">?</span>', 'class="arrow" aria-hidden="true">Read case study</span>')
 if p==site/'case-studies/Binance_First_Case_Study_Free.html':
  fixed=fixed.replace('href="#case-studies"', 'href="/crsis47-public-site/case-studies/index.html#case-studies"')
 if fixed!=text:
  p.write_text(fixed,encoding='utf8');changed.append(str(p.relative_to(site)))
# Normalize legacy release paths AFTER all approved classroom overlays.
# Original ZIP and approved source hashes remain untouched.
for asset in site.rglob('*'):
 if asset.is_file() and asset.suffix.lower() in {'.html','.css','.js','.json','.xml','.txt'} and asset.name!='deployment-manifest.json':
  original=asset.read_text(encoding='utf8')
  fixed=original.replace('/crsis47-public-site./','/crsis47-public-site/')
  if fixed!=original:
   asset.write_text(fixed,encoding='utf8')
   rel=str(asset.relative_to(site))
   if rel not in changed: changed.append(rel)
assert 'case2-offer.js' not in (site/'index.html').read_text()
manifest_path=site/'deployment-manifest.json'
m=json.loads(manifest_path.read_text())
for name in changed+['case2-offer.js']:
 m['files'][name]=hashlib.sha256((site/name).read_bytes()).hexdigest()
m['case_study_2_offer']={'product_url':url,'price_usd':5,'edition':'Professional','language':'en','files_changed':changed}
manifest_path.write_text(json.dumps(m,indent=2),encoding='utf8')
print(f'PASS: Case Study 2 purchase offer added to {len(changed)} pages; original archives unchanged')
