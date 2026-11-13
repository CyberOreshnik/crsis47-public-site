"""Static, locale-aware search sources. Searches never include private product files."""
from html.parser import HTMLParser
from html import escape,unescape
import re
class Plain(HTMLParser):
 def __init__(self):super().__init__();self.parts=[];self.skip=0
 def handle_starttag(self,t,a):
  if t in ('script','style'):self.skip+=1
 def handle_endtag(self,t):
  if t in ('script','style'):self.skip=max(0,self.skip-1)
  elif t in ('p','h1','h2','h3','li','div','td','th'):self.parts.append(' ')
 def handle_data(self,s):
  if not self.skip:self.parts.append(s)
def plain(s):
 p=Plain();p.feed(s);return re.sub(r'\s+',' ',''.join(p.parts)).strip()
def glossary_blocks(raw):
 return re.findall(r'<article\b[^>]*>[\s\S]*?</article>',raw)
def tag_glossary(raw):
 seen={}
 def annotate(match):
  block=match.group(0);head=re.search(r'<h2\b[^>]*>([\s\S]*?)</h2>',block)
  term=plain(head.group(1)) if head else 'entry'
  key='term-'+(re.sub(r'[^a-z0-9]+','-',term.lower()).strip('-') or 'entry')
  seen[key]=seen.get(key,0)+1
  if seen[key]>1:key+='-'+str(seen[key])
  block=re.sub(r'\s+id="[^"]*"','',block,count=1)
  return block.replace('<article','<article id="'+key+'"',1)
 return re.sub(r'<article\b[^>]*>[\s\S]*?</article>',annotate,raw)
def search_form(lang,T,loc,home=False):
 label='Search the collection' if home else 'Search titles, topics, or glossary terms'
 return '<form class="collection-search" action="'+loc(lang,'search/')+'" method="get" role="search"><label for="'+('home-search-query' if home else 'search-query')+'">'+escape(T(label,lang))+'</label><div class="search-input-row"><input type="search" id="'+('home-search-query' if home else 'search-query')+'" name="q" maxlength="200" autocomplete="off" placeholder="'+escape(T('Try a title, topic, or acronym',lang),quote=True)+'"><button class="button" type="submit">'+escape(T('Search',lang))+'</button></div></form>'
def home_search(lang,T,loc):
 return '<section class="home-search" aria-label="'+escape(T('Search the collection',lang),quote=True)+'">'+search_form(lang,T,loc,True)+'</section>'
def search_body(lang,T,loc):
 choices=[('all','All'),('books','Books'),('cases','Case Studies'),('glossary','Glossary')]
 filters=''.join('<button type="button" data-category="'+key+'" aria-pressed="'+('true' if key=='all' else 'false')+'">'+escape(T(label,lang))+'</button>' for key,label in choices)
 messages={'results':T('Results',lang),'empty':T('No matching results. Try another term or category.',lang),'error':T('Search is temporarily unavailable. Please browse the catalogs.',lang),'more':T('Show more results',lang)}
 # data attributes are escaped; the browser never interprets query text as HTML.
 data=' '.join('data-message-'+key+'="'+escape(value,quote=True)+'"' for key,value in messages.items())
 return '<section class="wrap detail-page search-page" data-search-index="'+loc(lang,'search-index.json')+'" '+data+'><div class="eyebrow">CRSIS-47 · The Evidence Chamber</div><h1>'+escape(T('Search the Evidence Chamber',lang))+'</h1><p class="intro">'+escape(T('Find books, case studies, and glossary terms in the public collection.',lang))+'</p>'+search_form(lang,T,loc)+'<div class="search-filters" role="group" aria-label="'+escape(T('Filter search results',lang),quote=True)+'">'+filters+'</div><p id="search-status" class="search-status" role="status" aria-live="polite" aria-atomic="true">'+escape(T('Loading search results…',lang))+'</p><p id="search-empty" hidden></p><div id="search-results" class="search-results"></div><button class="button secondary" id="search-more" type="button" aria-controls="search-results" hidden>'+escape(T('Show more results',lang))+'</button><noscript><p>'+escape(T('Search requires JavaScript. You can still browse the collection using the links below.',lang))+'</p><a href="'+loc(lang,'books/')+'">'+escape(T('Books',lang))+'</a> · <a href="'+loc(lang,'case-studies/')+'">'+escape(T('Case Studies',lang))+'</a> · <a href="'+loc(lang,'glossary.html')+'">'+escape(T('Glossary',lang))+'</a></noscript></section>'
def make_index(cat,lang,T,loc,localize,glossary_raw):
 docs=[]
 for b in cat['books']:
  en=b.get('copy',{}).get('en',{});copy=b.get('copy',{}).get(lang,en)
  docs.append({'id':'book-'+b['id'],'category':'books','label':T('Books',lang),'title':copy.get('title',b['title']),'summary':copy.get('hook',b['description']),'text':' '.join(copy.get('paragraphs',[])),'aliases':' '.join([b['id'],'Book '+b['id'],b['title'],b['description'],*en.get('paragraphs',[]),*b.get('keywords',[])]),'url':loc(lang,'books/'+b['slug']+'/')})
 for c in cat['cases']:
  article=c.get('article',{});summary=T(c['description'],lang)
  docs.append({'id':'case-'+c['id'],'category':'cases','label':T('Case Studies',lang),'title':T(c['title'],lang),'summary':summary,'text':plain(article.get(lang,article.get('en',''))) or summary,'aliases':' '.join([c['id'],'Case '+c['id'],'Case'+c['id'],c['title'],c['description'],*c.get('keywords',[])]),'url':loc(lang,'case-studies/'+c['slug']+'/')})
 original=glossary_blocks(tag_glossary(glossary_raw))
 translated=glossary_blocks(localize(tag_glossary(glossary_raw),lang,'glossary.html'))
 assert len(original)==len(translated)
 for english,block in zip(original,translated):
  key=re.search(r'<article id="([^"]+)"',block).group(1)
  title=plain(re.search(r'<h2\b[^>]*>([\s\S]*?)</h2>',block).group(1))
  summary=' '.join(plain(p) for p in re.findall(r'<p\b[^>]*>([\s\S]*?)</p>',block))
  docs.append({'id':key,'category':'glossary','label':T('Glossary',lang),'title':title,'summary':summary,'text':summary,'aliases':plain(english),'url':loc(lang,'glossary.html')+'#'+key})
 return {'version':1,'language':lang,'documents':docs}
