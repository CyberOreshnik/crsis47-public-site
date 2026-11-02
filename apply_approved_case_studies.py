"""Overlay only approved classroom HTML; retain the original release archive."""
from pathlib import Path
import hashlib,json,re
source=Path('approved-case-studies');site=Path('site')
manifest=json.loads((source/'manifest.json').read_text(encoding='utf8'))
assert len(manifest['files'])==28 and len(manifest['languages'])==14
for name,digest in manifest['files'].items():
 p=Path(name)
 assert p.parts[0]=='case-studies' and '..' not in p.parts and p.name in {'index.html','Binance_First_Case_Study_Free.html'}
 data=(source/p).read_bytes();assert hashlib.sha256(data).hexdigest()==digest,(name,'SHA-256')
 text=data.decode('utf8');assert 'noindex' not in text.split('</head>')[0]
 assert not re.search(r'libfile_[a-f0-9]{32}|[A-Za-z]:[\\/]Users[\\/]|TRANSFER_SHA256|PRIVATE KEY',text)
 assert 'lang=' in text and 'download=' in text and 'window.print()' in text
 target=site/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
for lang in manifest['languages']:
 folder=site/'case-studies'/(lang if lang!='en' else '')
 assert (folder/'index.html').read_bytes()==(folder/'Binance_First_Case_Study_Free.html').read_bytes()
 if lang!='en':assert (folder/'index.html').read_text(encoding='utf8').count('English original</a>')==2
deployed=json.loads((site/'deployment-manifest.json').read_text())
deployed['classroom_release']={'approved_by':manifest['approved_by'],'approval_date':manifest['approval_date'],'languages':manifest['languages'],'files':manifest['files']}
for name,digest in manifest['files'].items():deployed['files'][name]=digest
(site/'deployment-manifest.json').write_text(json.dumps(deployed,indent=2),encoding='utf8')
print('PASS: 28 approved pages, 14 languages, hashes and disclosures verified; original release archive unchanged')
