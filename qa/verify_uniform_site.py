from pathlib import Path
import json,hashlib,re,importlib.util,copy,sys
sys.path.insert(0,str(Path.cwd()))
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
 index=g.make_index(g.CAT,'en',g.T,g.loc,g.localize,(g.U/'glossary_body.html').read_text(encoding='utf8'))
 assert any(sample['slug'] in d['url'] for d in index['documents'])
 g.CAT[collection].pop()
print('PASS: uniform hashes, fourteen locale interfaces, locked glossary terms, no old app template and future item routes')

# Search must include the current catalog and public glossary in each selected locale.
from uniform.search_support import glossary_blocks,tag_glossary
glossary_count=len(glossary_blocks(tag_glossary(Path('uniform/glossary_body.html').read_text(encoding='utf8'))))
for lang in langs:
 prefix='' if lang=='en' else lang+'/'
 index=json.loads((root/prefix/'search-index.json').read_text(encoding='utf8'))
 assert index['language']==lang
 documents=index['documents']
 assert len(documents)==len(cat['books'])+len(cat['cases'])+glossary_count
 assert len({d['id'] for d in documents})==len(documents)
 assert sum(d['category']=='books' for d in documents)==len(cat['books'])
 assert sum(d['category']=='cases' for d in documents)==len(cat['cases'])
 assert sum(d['category']=='glossary' for d in documents)==glossary_count
 for d in documents:
  assert d['title'] and d['url'].startswith('/crsis47-public-site/'+prefix)
  rel,_,fragment=d['url'].removeprefix('/crsis47-public-site/').partition('#')
  dest=root/rel
  if dest.is_dir():dest=dest/'index.html'
  assert dest.is_file(),d['url']
  if fragment:assert 'id="'+fragment+'"' in dest.read_text(encoding='utf8'),d['url']
 search_page=(root/prefix/'search/index.html').read_text(encoding='utf8')
 assert 'role="search"' in search_page and 'aria-live="polite"' in search_page
 for category in ['all','books','cases','glossary']:assert 'data-category="'+category+'"' in search_page
 assert 'home-search-query' in (root/prefix/'index.html').read_text(encoding='utf8')
print('PASS: localized search indexes, category totals, unique results, valid routes, glossary anchors and accessible controls')
