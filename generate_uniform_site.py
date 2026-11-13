"""Generate every public catalog/detail page from one catalog and shared brand shell.
No network or third-party service is used during builds.
"""
from pathlib import Path
from html.parser import HTMLParser
from html import escape,unescape
from urllib.parse import urlsplit
import json,re,hashlib,sys
from uniform.search_support import search_body,home_search,tag_glossary,make_index
ROOT=Path(__file__).resolve().parent
U=ROOT/'uniform';S=ROOT/'site'
B='/crsis47-public-site/'
CONTENT=json.loads((U/'content.json').read_text(encoding='utf8'))
CAT=json.loads((U/'catalog.json').read_text(encoding='utf8'))
LANGS=[('en','English'),('fr','Français'),('ht','Kreyòl ayisyen'),('es','Español'),('pt-BR','Português brasileiro'),('pt-PT','Português europeu'),('ru','Русский'),('ar','العربية'),('zh-Hans','简体中文'),('zh-Hant','繁體中文'),('ja','日本語'),('fa','فارسی'),('he','עברית'),('tr','Türkçe')]
STRINGS=set();MAP={}
VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
def clean(s):return re.sub(r'\s+',' ',s).strip()
def translatable(s):
 s=clean(s)
 return bool(s and re.search(r'[A-Za-z]{2}',s) and not re.fullmatch(r'[\d\s+—–:./<>=%()$·−-]+',s) and s not in ['CRSIS-47','T+47','T+0','TTCD','PGDT','MALICIOUS','BENIGN','UNCERTAIN','CRSIS','T+47 Theory','People, Governance, Data, Technology','Time to Confident Detection','Constantin Jean-Pierre','Constantine Jean-Pierre'])
def T(s,lang):
 k=clean(s)
 if translatable(k):STRINGS.add(k)
 return MAP.get(lang,{}).get(k,k)
def loc(lang,route=''):return B+('' if lang=='en' else lang+'/')+route
def asset(p):return B+p
def fix_url(v,lang,route):
 if not v:return v
 if v.startswith(('https://','http://','mailto:','tel:','data:')):return v
 if v.startswith('#'):
  targets={'#books':'books/','#case-studies':'case-studies/','#research':'research/','#about':'about/','#contact':'contact/'}
  if v in targets:return loc(lang,targets[v])
  return v
 if v.startswith(B):return v
 if v.startswith('/crsis47-public-site./'):return v.replace('/crsis47-public-site./',B)
 if v.startswith(('case00','shield.','cinematic.','founder-','research_division','covers/')):return asset(v)
 if v.startswith('books/'):return loc(lang,v)
 if v=='glossary.html':return loc(lang,v)
 return v
class Localize(HTMLParser):
 def __init__(self,lang,route):
  super().__init__(convert_charrefs=False);self.lang=lang;self.route=route;self.out=[];self.stack=[]
 def skipped(self):return bool(self.stack and self.stack[-1][1])
 def start(self,tag,attrs,closed=False):
  d=dict(attrs);skip=self.skipped() or tag in ['script','style'] or 'data-preserved' in d
  output=[]
  for k,v in attrs:
   if v is None:output.append(k);continue
   if k in ['href','src']:v=fix_url(v,self.lang,self.route)
   if not skip and k in ['alt','aria-label','placeholder','title'] and v:v=T(v,self.lang)
   output.append(k+'="'+escape(v,quote=True)+'"')
  self.out.append('<'+tag+(' '+' '.join(output) if output else '')+('/>' if closed else '>'))
  if tag not in VOID and not closed:self.stack.append((tag,skip))
 def handle_starttag(self,t,a):self.start(t,a)
 def handle_startendtag(self,t,a):self.start(t,a,True)
 def handle_endtag(self,tag):
  self.out.append('</'+tag+'>')
  for i in range(len(self.stack)-1,-1,-1):
   if self.stack[i][0]==tag:self.stack=self.stack[:i];break
 def handle_data(self,data):
  if self.skipped() or not clean(data):self.out.append(data);return
  k=clean(unescape(data));value=T(k,self.lang)
  self.out.append((' ' if data[:1].isspace() else '')+escape(value)+(' ' if data[-1:].isspace() else ''))
 def handle_entityref(self,name):self.out.append('&'+name+';')
 def handle_charref(self,name):self.out.append('&#'+name+';')
 def handle_comment(self,data):pass
def localize(text,lang,route):
 p=Localize(lang,route);p.feed(text);return ''.join(p.out)
def preserved(text):return '<div data-preserved>'+text+'</div>'
def nav(lang,route):
 labels=[('Case Studies','case-studies/'),('Books','books/'),('Research & Laboratories','research/'),('Glossary','glossary.html'),('About','about/'),('Contact','contact/'),('Search','search/')]
 links=''.join('<a href="'+loc(lang,r)+'"'+(' aria-current="page"' if r==route else '')+'>'+escape(T(n,lang))+'</a>' for n,r in labels)
 languages=''.join('<a lang="'+c+'" hreflang="'+c+'" href="'+loc(c,route)+'"'+(' aria-current="page"' if c==lang else '')+'>'+n+'</a>' for c,n in LANGS)
 return '<header><nav class="nav" aria-label="'+escape(T('Main navigation',lang))+'"><a class="brand" href="'+loc(lang)+'"><img src="'+asset('shield.png')+'" width="57" height="62" alt="CRSIS-47 Evidence Chamber shield"><span>CRSIS-47</span></a><div class="links">'+links+'<details class="language-menu"><summary>'+dict(LANGS)[lang]+'</summary><div class="language-panel"><strong>'+escape(T('Choose your language',lang))+'</strong>'+languages+'</div></details></div></nav></header>'
def controls(lang):return '<div class="shelf-controls"><small>'+escape(T('SCROLL TO EXPLORE',lang))+'</small><button type="button" aria-label="'+escape(T('Previous items',lang))+'">←</button><button type="button" aria-label="'+escape(T('Next items',lang))+'">→</button></div>'
def bookcard(b,lang):
 copy=b.get('copy',{}).get(lang,b.get('copy',{}).get('en',{}))
 title=copy.get('title',b['title']);desc=copy.get('hook',b['description'])
 route='books/'+b['slug']+'/'
 return '<article class="file book-file"><div><span class="tag">'+escape(T('Book',lang))+' '+b['id']+'</span><a class="book-cover-link" href="'+loc(lang,route)+'"><img class="book-cover" src="'+asset(b['cover'])+'" alt="'+escape(title)+'" loading="lazy"></a><h3 data-preserved><a href="'+loc(lang,route)+'">'+escape(title)+'</a></h3><p data-preserved>'+escape(desc)+'</p></div><a class="collection-action" href="'+loc(lang,route)+'">'+escape(T('Read the synopsis',lang))+'</a></article>'
def price_label(c):return chr(36)+format(float(c['price_usd']),'g')
def casecard(c,lang):
 route='case-studies/'+c['slug']+'/'
 cover='<div class="case-cover-frame"><a href="'+loc(lang,route)+'" aria-label="'+escape(T('Read case details',lang))+'"><img class="case-cover" src="'+asset(c['cover'])+'" alt="'+escape(T(c['title'],lang))+'" loading="lazy"></a></div>' if c['cover'] else '<div class="case-cover-frame case-cover-pending"><span>CASE '+c['id']+'</span><strong>'+escape(T(c['title'],lang))+'</strong><small>'+escape(T('Cover awaiting approval',lang))+'</small></div>'
 if c['purchase_url']:action='<a href="'+c['purchase_url']+'">'+escape(T('View professional edition',lang))+' — '+price_label(c)+'</a>'
 elif c.get('article'):action='<a href="'+loc(lang,route)+'">'+escape(T('Read the free edition',lang))+'</a>'
 else:action='<a href="'+loc(lang,route)+'">'+escape(T('View case details',lang))+'</a>'
 return '<article class="file book-file case-file"><div><span class="tag">'+escape(T(c['status'],lang))+'</span>'+cover+'<h3><a href="'+loc(lang,route)+'">'+escape(T(c['title'],lang))+'</a></h3><p>'+escape(T(c['description'],lang))+'</p></div>'+action+'</article>'
def cabinet(kind,lang,shelf=True):
 items=CAT['books' if kind=='books' else 'cases'];name='Books' if kind=='books' else 'Case Studies'
 cards=''.join(bookcard(i,lang) if kind=='books' else casecard(i,lang) for i in items)
 return '<div class="cabinet"><div class="cabinet-top"><strong>'+escape(T(name,lang))+' / '+str(len(items))+'</strong>'+ (controls(lang) if shelf else '')+'</div><div class="'+('shelf' if shelf else 'catalog-grid')+'">'+cards+'</div>'+('<p class="cabinet-hint">'+escape(T('Scroll to browse the complete collection',lang))+'</p>' if shelf else '')+'</div>'
def collection(kind,lang,home=False):
 title='Books File Cabinet' if kind=='books' else 'Case Study File Cabinet'
 intro='A growing collection on cybersecurity, leadership, uncertainty, and the human cost of decisions.' if kind=='books' else 'Investigations in the CRSIS-47 case-study progression. Availability is stated for each edition.'
 return '<section class="wrap" id="'+kind+'"><div class="eyebrow">'+escape(T('The Author Collection' if kind=='books' else 'The Professional Collection',lang))+'</div><'+('h2' if home else 'h1')+' class="section-title">'+escape(T(title,lang))+'</'+('h2' if home else 'h1')+'><p class="intro">'+escape(T(intro,lang))+'</p>'+cabinet(kind,lang,home)+'</section>'
def detail_book(b,lang):
 copy=b.get('copy',{}).get(lang,b.get('copy',{}).get('en',{}))
 title=copy.get('title',b['title'])
 facts='<dl class="detail-facts">'+''.join('<div><dt>'+escape(k)+'</dt><dd>'+escape(v)+'</dd></div>' for k,v in [(k,('T+47 / '+str(int(b['id']))+' / '+str(len(CAT['books']))) if i==0 else v) for i,(k,v) in enumerate(copy.get('facts',[]))])+'</dl>'
 return '<section class="wrap detail-page"><a class="back-link" href="'+loc(lang,'books/')+'">← '+escape(T('The T+47 collection',lang))+'</a><div class="book-layout"><aside><img class="detail-book-cover" src="'+asset(b['cover'])+'" alt="'+escape(title)+'"><p class="tag">T+47 / '+b['id']+'</p></aside><article class="detail-copy"><div class="eyebrow">'+escape(T('Book',lang))+' '+b['id']+'</div>'+preserved('<h1>'+escape(title)+'</h1><p class="detail-hook">'+escape(copy.get('hook',b['description']))+'</p>')+'<h2>'+escape(T('Synopsis',lang))+'</h2>'+preserved(''.join('<p>'+escape(p)+'</p>' for p in copy.get('paragraphs',[]))+facts)+'<a class="button secondary" href="'+loc(lang,'books/')+'">'+escape(T('Browse all books',lang))+'</a></article></div></section>'
def detail_case(c,lang):
 back='<a class="back-link" href="'+loc(lang,'case-studies/')+'">← '+escape(T('All case studies',lang))+'</a>'
 title='<div class="eyebrow">'+escape(T('Case Study',lang))+' '+c['id']+'</div><h1>'+escape(T(c['title'],lang))+'</h1><p class="tag">'+escape(T(c['status'],lang))+'</p>'
 if c.get('article'):
  return '<section class="wrap detail-page">'+back+title+'<div class="detail-tools"><button class="button print-page" type="button">'+escape(T('Print or save PDF',lang))+'</button></div><div class="reader-copy" data-preserved>'+c['article'].get(lang,c['article']['en'])+'</div></section>'
 body='<p class="detail-hook">'+escape(T(c['description'],lang))+'</p>'
 if c['purchase_url']:
  body+='<p>'+escape(T('English professional edition · Digital download',lang))+' · '+price_label(c)+' USD</p><a class="button" href="'+c['purchase_url']+'">'+escape(T('View professional edition on Payhip',lang))+'</a><p class="detail-note">'+escape(T('Purchase and download through Payhip. Product language, included files and any applicable taxes are stated there.',lang))+'</p>'
 else:
  body+='<p class="detail-note">'+escape(T('This edition is in development or editorial review. It is not yet offered for purchase.',lang))+'</p>'
 visual='<div class="case-cover-frame detail-case-cover"><img class="case-cover" src="'+asset(c['cover'])+'" alt="'+escape(T(c['title'],lang))+'"></div>' if c['cover'] else ''
 return '<section class="wrap detail-page" id="case-studies">'+back+'<div class="case-detail-layout"><div>'+title+body+'</div>'+visual+'</div><div class="detail-tools"><a class="button secondary" href="'+loc(lang,'case-studies/')+'">'+escape(T('Browse all case studies',lang))+'</a></div></section>'
def standalone(name,lang):
 raw=CONTENT['sections'][name]
 raw=re.sub(r'<h2([^>]*)>(.*?)</h2>',r'<h1\1>\2</h1>',raw,count=1,flags=re.S)
 return localize(raw,lang,name+'/')
def page_body(route,lang):
 if not route:
  return localize(CONTENT['sections']['hero'],lang,route)+home_search(lang,T,loc)+collection('case-studies',lang,True)+collection('books',lang,True)+localize(CONTENT['sections']['research'],lang,route)+localize(CONTENT['sections']['about'],lang,route)+localize(CONTENT['sections']['contact'],lang,route)+localize(CONTENT['sections']['closing'],lang,route)
 if route=='search/':return search_body(lang,T,loc)
 if route=='books/':return collection('books',lang)
 if route=='case-studies/':return collection('case-studies',lang)
 if route in ['research/','about/','contact/']:return standalone(route[:-1],lang)
 if route=='updates/':return '<section class="wrap detail-page"><h1>'+escape(T('Publications & Updates',lang))+'</h1><p>'+escape(T('Explore the current books, case studies and research pages. Availability and research status are stated with each item.',lang))+'</p><div class="actions"><a class="button" href="'+loc(lang,'books/')+'">'+escape(T('Books',lang))+'</a><a class="button secondary" href="'+loc(lang,'case-studies/')+'">'+escape(T('Case Studies',lang))+'</a></div></section>'
 if route=='glossary.html':
  raw=(U/'glossary_body.html').read_text(encoding='utf8')
  return localize(tag_glossary(raw),lang,route)
 for b in CAT['books']:
  if route=='books/'+b['slug']+'/':return detail_book(b,lang)
 for c in CAT['cases']:
  if route=='case-studies/'+c['slug']+'/':return detail_case(c,lang)
 raise ValueError(route)
def title_for(route,lang):
 if not route:return 'CRSIS-47 | The Evidence Chamber'
 for b in CAT['books']:
  if route=='books/'+b['slug']+'/':return b.get('copy',{}).get(lang,b.get('copy',{}).get('en',{})).get('title',b['title'])+' | CRSIS-47'
 for c in CAT['cases']:
  if route=='case-studies/'+c['slug']+'/':return T(c['title'],lang)+' | CRSIS-47'
 return T({'books/':'Books','case-studies/':'Case Studies','research/':'Research & Laboratories','about/':'About','contact/':'Contact','updates/':'Publications & Updates','glossary.html':'Research Glossary','search/':'Search'}[route],lang)+' | CRSIS-47'
def page(route,lang):
 body=page_body(route,lang);rtl=lang in ['ar','fa','he']
 note='' if lang=='en' else '<div class="translation-note">'+escape(T('Machine-assisted translation. The English original governs technical terminology. Product language is stated separately.',lang))+' <a href="'+loc('en',route)+'" lang="en">English</a></div>'
 alternates=''.join('<link rel="alternate" hreflang="'+c+'" href="https://cyberoreshnik.github.io'+loc(c,route)+'">' for c,_ in LANGS)
 footer='<footer class="footer"><a href="'+loc(lang)+'">CRSIS-47 · The Evidence Chamber</a><p>'+escape(T('Where Evidence Becomes Judgment',lang))+'</p><a href="#top">'+escape(T('Return to top',lang))+' ↑</a></footer>'
 return '<!doctype html><html lang="'+lang+'" dir="'+('rtl' if rtl else 'ltr')+'"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+escape(title_for(route,lang))+'</title><link rel="canonical" href="https://cyberoreshnik.github.io'+loc(lang,route)+'">'+alternates+'<link rel="icon" type="image/png" href="'+asset('shield.png')+'"><link rel="stylesheet" href="'+asset('uniform/site.css')+'"><script src="'+asset('uniform/site.js')+'" defer></script></head><body id="top"><a class="skip-link" href="#main">'+escape(T('Skip to content',lang))+'</a>'+nav(lang,route)+note+'<main id="main">'+body+'</main>'+footer+'</body></html>'
def routes():return ['', 'books/','case-studies/','research/','about/','contact/','updates/','glossary.html','search/']+['books/'+b['slug']+'/' for b in CAT['books']]+['case-studies/'+c['slug']+'/' for c in CAT['cases']]
def target(lang,route):
 prefix='' if lang=='en' else lang+'/'
 return S/prefix/(route if route.endswith('.html') else route+'index.html')
def redirect(path,destination):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0;url='+destination+'"><link rel="canonical" href="https://cyberoreshnik.github.io'+destination+'"><title>CRSIS-47</title></head><body><a href="'+destination+'">CRSIS-47 · Continue</a></body></html>',encoding='utf8')
def main():
 global MAP
 for lang,_ in LANGS:
  p=U/'translations'/f'{lang}.json'
  if p.is_file():MAP[lang]=json.loads(p.read_text(encoding='utf8'))
 # Collect every translatable English source string before requiring completeness.
 for route in routes():page(route,'en')
 T('Machine-assisted translation. The English original governs technical terminology. Product language is stated separately.','en')
 (U/'strings.json').write_text(json.dumps(sorted(STRINGS),ensure_ascii=False,indent=2),encoding='utf8')
 if '--collect' in sys.argv:
  print('Source strings:',len(STRINGS));return
 missing={lang:[s for s in STRINGS if s not in MAP.get(lang,{})] for lang,_ in LANGS if lang!='en'}
 assert not any(missing.values()),{lang:len(v) for lang,v in missing.items() if v}
 output={}
 for item in CAT['books']:
  assert item.get('copy',{}).get('en',{}).get('paragraphs'),('Missing approved synopsis',item['slug'])
 for lang,_ in LANGS:
  for route in routes():
   path=target(lang,route);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(page(route,lang),encoding='utf8')
   output[path.relative_to(S).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
  search_index=make_index(CAT,lang,T,loc,localize,(U/'glossary_body.html').read_text(encoding='utf8'))
  index_path=S/('' if lang=='en' else lang)/'search-index.json'
  index_path.write_text(json.dumps(search_index,ensure_ascii=False,separators=(',',':')),encoding='utf8')
  output[index_path.relative_to(S).as_posix()]=hashlib.sha256(index_path.read_bytes()).hexdigest()
  redirect(S/'languages'/lang/'index.html',loc(lang,'case-studies/001-binance/'))
  if lang!='en':
   redirect(S/'case-studies'/lang/'index.html',loc(lang,'case-studies/001-binance/'))
   redirect(S/'case-studies'/lang/'Binance_First_Case_Study_Free.html',loc(lang,'case-studies/001-binance/'))
  prefix='' if lang=='en' else lang+'/'
  redirect(S/prefix/'case-studies/Binance_First_Case_Study_Free.html',loc(lang,'case-studies/001-binance/'))
  for old in ['404/index.html','_not-found/index.html']:
   redirect(S/prefix/old,loc(lang))
 redirect(S/'404.html',loc('en'))
 public= S/'uniform';public.mkdir(exist_ok=True)
 for name in ['site.css','site.js']:
  (public/name).write_bytes((U/name).read_bytes());output['uniform/'+name]=hashlib.sha256((public/name).read_bytes()).hexdigest()
 manifest={'version':'uniform-catalog-1','languages':[c for c,_ in LANGS],'books':len(CAT['books']),'cases':len(CAT['cases']),'files':output}
 (S/'uniform-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
 m=json.loads((S/'deployment-manifest.json').read_text(encoding='utf8'));m['uniform_website']=manifest;m['files'].update(output)
 (S/'deployment-manifest.json').write_text(json.dumps(m,indent=2),encoding='utf8')
 urls=['https://cyberoreshnik.github.io'+loc(lang,route) for lang,_ in LANGS for route in routes()]
 (S/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+escape(u)+'</loc></url>' for u in urls)+'</urlset>',encoding='utf8')
 print('PASS:',len(output),'uniform files;',len(LANGS),'languages;',len(CAT['books']),'books;',len(CAT['cases']),'cases')
if __name__=='__main__':main()
