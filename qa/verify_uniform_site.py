from pathlib import Path
import json,hashlib,re,importlib.util,copy
root=Path('site');m=json.loads((root/'uniform-manifest.json').read_text(encoding='utf8'))
cat=json.loads(Path('uniform/catalog.json').read_text(encoding='utf8'))
langs=m['languages'];assert len(langs)==14 and len(set(langs))==14
for name,digest in m['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
for group in ['books','cases']:
 assert len({i['id'] for i in cat[group]})==len(cat[group])
 assert len({i['slug'] for i in cat[group]})==len(cat[group])
for lang in langs:
 prefix='' if lang=='en' else lang+'/'
 for route in ['','books/','case-studies/','research/','about/','contact/','updates/','glossary.html']:
  p=root/prefix/(route if route.endswith('.html') else route+'index.html');text=p.read_text(encoding='utf8')
  assert f'lang="{lang}"' in text and 'uniform/site.css' in text and 'shield.png' in text,p
  assert 'language-menu' in text and 'CRSIS-47' in text,p
  assert not re.search(r'<script[^>]*_next',text),p
 glossary=(root/prefix/'glossary.html').read_text(encoding='utf8')
 for fixed in ['Time to Confident Detection','People, Governance, Data, Technology','T+0','MALICIOUS']:assert fixed in glossary,(lang,fixed)
 assert re.search(r'(?:80\s*%|%\s*80)',glossary),(lang,'80 percent threshold')
 if lang!='en':
  translations=json.loads(Path(f'uniform/translations/{lang}.json').read_text(encoding='utf8'))
  expected=json.loads(Path('uniform/strings.json').read_text(encoding='utf8'))
  assert set(expected)<=set(translations),(lang,'missing translation')
  assert all(translations[s].strip() for s in expected)
 for b in cat['books']:assert (root/prefix/'books'/b['slug']/'index.html').is_file()
 for c in cat['cases']:assert (root/prefix/'case-studies'/c['slug']/'index.html').is_file()
spec=importlib.util.spec_from_file_location('generator','generate_uniform_site.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
for collection,route,idval in [('cases','case-studies/','007'),('books','books/','06')]:
 sample=copy.deepcopy(g.CAT[collection][-1]);sample['id']=idval;sample['slug']='future-catalog-route-check';g.CAT[collection].append(sample)
 assert route+sample['slug']+'/' in g.routes()
 assert sample['slug'] in g.collection('books' if collection=='books' else 'case-studies','en',True)
 assert g.page(route+sample['slug']+'/','en')
 if collection=='cases':
  sample['purchase_url']='https://payhip.com/b/wym8f';sample['price_usd']=11
  assert '$11' in g.detail_case(sample,'en')
 g.CAT[collection].pop()
print('PASS: uniform hashes, fourteen locale interfaces, locked glossary terms, no old app template and future item routes')
