"""Add the approved Payhip offer without changing archived releases or downloads."""
from pathlib import Path
import hashlib,json
site=Path('site')
url='https://payhip.com/b/kvM9I'
card='''<section id="case-study-2-offer" lang="en" dir="ltr" aria-labelledby="case2-title" style="max-width:1100px;margin:64px auto;padding:40px 28px;background:#101e32;color:#fff;border:1px solid #c7a768;border-radius:12px;box-sizing:border-box"><p style="color:#e1c58b;letter-spacing:.12em;font-size:.8rem;text-transform:uppercase">CRSIS-47 · Case Study 2 · Professional Edition</p><h2 id="case2-title" style="color:#fff;font-size:clamp(1.8rem,4vw,2.8rem);line-height:1.2;margin:16px 0">Leadership Under Uncertainty</h2><p style="font-size:1.1rem;line-height:1.7;max-width:760px">Explore leadership decisions under uncertainty with this cybersecurity case study and its accompanying learning materials.</p><p style="line-height:1.7">By Constantin Jean-Pierre · English edition · Digital download</p><a href="https://payhip.com/b/kvM9I" style="display:inline-block;background:#e1c58b;color:#101e32;padding:15px 24px;border-radius:5px;font-weight:700;text-decoration:underline;text-underline-offset:4px">Get the Professional Edition — $5 USD</a><p style="font-size:.9rem;line-height:1.6;margin-top:18px">Purchase and download through Payhip. Any applicable taxes are shown at checkout.</p></section>'''
# Keep the existing React-rendered release intact: add the offer after hydration.
js='''(() => { const add = () => { if(document.getElementById('case-study-2-offer')) return; const main=document.querySelector('main'); if(!main) return; const holder=document.createElement('div'); holder.innerHTML=CARD; main.appendChild(holder.firstElementChild); if(location.hash==='#case-study-2-offer') document.getElementById('case-study-2-offer').scrollIntoView(); }; const observer=new MutationObserver(add); observer.observe(document.body,{childList:true,subtree:true}); add(); })();'''.replace('CARD',json.dumps(card))
(site/'case2-offer.js').write_text(js,encoding='utf8')
# Discoverability across existing site pages, preserving every locale's content.
changed=[]
for p in site.rglob('*.html'):
 text=p.read_text(encoding='utf8')
 if '<main' not in text: continue
 tag='<script src="/crsis47-public-site./case2-offer.js" defer></script>'
 if tag not in text:
  assert '</body>' in text
  text=text.replace('</body>',tag+'</body>')
  p.write_text(text,encoding='utf8');changed.append(str(p.relative_to(site)))
# Case-study classroom pages use article layouts rather than main.
for p in (site/'case-studies').rglob('index.html'):
 text=p.read_text(encoding='utf8')
 if '<main' not in text and 'id="case-study-2-offer"' not in text:
  text=text.replace('</body>',card+'</body>');p.write_text(text,encoding='utf8');changed.append(str(p.relative_to(site)))
assert 'case2-offer.js' in (site/'index.html').read_text()
manifest_path=site/'deployment-manifest.json'
m=json.loads(manifest_path.read_text())
for name in changed+['case2-offer.js']:
 m['files'][name]=hashlib.sha256((site/name).read_bytes()).hexdigest()
m['case_study_2_offer']={'product_url':url,'price_usd':5,'edition':'Professional','language':'en','files_changed':changed}
manifest_path.write_text(json.dumps(m,indent=2),encoding='utf8')
print(f'PASS: Case Study 2 purchase offer added to {len(changed)} pages; original archives unchanged')
