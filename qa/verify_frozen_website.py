"""Fail closed on changed artwork, source bytes, links or page structure."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib, json, re
site=Path('site')
m=json.loads(Path('approved-website/manifest.json').read_text(encoding='utf-8'))
for name,digest in m['files'].items():
    assert hashlib.sha256((site/name).read_bytes()).hexdigest()==digest, name
class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.ids=set(); self.refs=[]; self.nav=0; self.divisions=0; self.images=[]
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if 'id' in d:
            assert d['id'] not in self.ids, ('duplicate ID',d['id'])
            self.ids.add(d['id'])
        self.nav+=tag=='nav'
        self.divisions+='research-visual-card' in d.get('class','').split()
        for attr in ('href','src'):
            if d.get(attr): self.refs.append(d[attr])
        if tag=='img': self.images.append(d['src'])
text=(site/'index.html').read_text(encoding='utf-8')
p=Page();p.feed(text)
assert p.nav==1 and p.divisions==4
for ref in p.refs:
    if ref.startswith('#'): assert ref[1:] in p.ids, ref
    elif not re.match(r'^[a-z]+:',ref): assert (site/ref).is_file(), ref
assert {'top','books','case-studies','research','about','contact','closing'}<=p.ids
assert {'shield.png','founder-headshot.png','cinematic.png','case001.png','case002.png','case003.png','case004.png'}<=set(p.images)
assert 'https://payhip.com/b/kvM9I' in p.refs and 'https://payhip.com/b/wym8f' in p.refs
assert 'crsis47-public-site./' not in text
assert 'mailto:cjean-pierre@captechu.edu' in p.refs
assert 'MutationObserver' not in text
print('PASS: frozen checksums, assets, navigation, divisions and purchase links')
