// Browser network-isolation regression: run after site build using Playwright Chromium.
// npm install --no-save playwright && npx playwright install --with-deps chromium
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const {spawn}=require('node:child_process');
const fs=require('node:fs');
const path=require('node:path');
const os=require('node:os');
const PORT=8768;
const ROOT=path.resolve('site');
const routes=[
  {name:'Books',path:'/index.html#books'},
  {name:'Case Studies',path:'/index.html#case-studies'},
  {name:'TIMEPIECE',path:'/labs/solarwinds-005/'},
  {name:'Glossary',path:'/glossary.html'},
  {name:'Source Hub',path:'/source-hub/'},
  {name:'Research',path:'/research/'}
];
(async()=>{
 assert.ok(fs.existsSync(ROOT),'Build site/ first; cannot claim browser coverage without a built website');
 const mount=fs.mkdtempSync(path.join(os.tmpdir(),'crsis-browser-'));
 fs.symlinkSync(ROOT,path.join(mount,'crsis47-public-site'),'dir');
 const server=spawn('python3',['-m','http.server',String(PORT),'--bind','127.0.0.1','--directory',mount],{stdio:'ignore'});
 let browser;
 try{
  for(let i=0;i<50;i++){try{const r=await fetch('http://127.0.0.1:'+PORT+'/crsis47-public-site/');if(r.ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
  browser=await chromium.launch({headless:true});
  const findings=[];
  const screenshotDir=path.resolve('preview-screenshots');
  fs.mkdirSync(screenshotDir,{recursive:true});
  for(const route of routes){
   const page=await browser.newPage();
   const data=[];
   const failures=[];
   const transfers=[];
   page.on('response',async response=>{try{const req=response.request();const type=req.resourceType();const body=await response.body();transfers.push({type,bytes:body.length,status:response.status(),path:new URL(response.url()).pathname});}catch{}});
   page.on('request',r=>{const u=new URL(r.url());if(/\.(json|ndjson|csv|sqlite|db)(?:$|\?)/i.test(u.pathname)||u.pathname.includes('/api/'))data.push(u.pathname);});
   page.on('requestfailed',r=>failures.push(r.url()));
   const response=await page.goto('http://127.0.0.1:'+PORT+'/crsis47-public-site'+route.path,{waitUntil:'networkidle',timeout:30000});
   assert.equal(response.status(),200,route.name+' missing route');
   const foreign=data.filter(p=>{
    const collection=route.name.toLowerCase().replace(/ /g,'-');
    return ['source-hub','labs','glossary','research','books','case-studies'].some(k=>p.includes('/'+k+'/')&&k!==collection);
   });
   assert.deepEqual(foreign,[],route.name+' loaded another collection dataset');
   assert.deepEqual(failures,[],route.name+' had failed network requests');
   if(route.name==='Books'||route.name==='Case Studies'){
    const kind=route.name==='Books'?'books':'case-studies';
    const cabinet=page.locator('[data-collection="'+kind+'"][data-page-size="4"]');
    assert.ok(await cabinet.count()>0,route.name+' missing approved four-item cabinet contract');
    const markup=await cabinet.innerHTML();
    assert.ok(markup.length>100,route.name+' rendered an empty catalog cabinet');
   }
   // Gate 4: accessibility and asset integrity for every approved collection route.
   const gate4=await page.evaluate(()=>{
    const images=[...document.images];
    const broken=images.filter(i=>i.complete&&i.naturalWidth===0).map(i=>i.getAttribute('src'));
    const unnamed=[...document.querySelectorAll('button')].filter(b=>!((b.innerText||'').trim()||b.getAttribute('aria-label')||b.getAttribute('title')));
    const unlabelledImages=images.filter(i=>!i.hasAttribute('alt')).map(i=>i.getAttribute('src'));
    const htmlLang=document.documentElement.getAttribute('lang');
    return {broken,unnamedButtons:unnamed.length,unlabelledImages,htmlLang};
   });
   assert.deepEqual(gate4.broken,[],route.name+' has broken images');
   assert.ok(gate4.htmlLang,route.name+' missing HTML language declaration');
   assert.deepEqual(gate4.unlabelledImages,[],route.name+' images missing alt attribute');
   assert.equal(gate4.unnamedButtons,0,route.name+' contains unnamed buttons');
   // Gate 4: inspect real navigation targets without following external links.
   const nav=await page.evaluate(()=>{
    const anchors=[...document.querySelectorAll('a[href]')];
    const unsafe=anchors.filter(a=>/^javascript:/i.test(a.getAttribute('href')||'')).map(a=>a.outerHTML.slice(0,160));
    const empty=anchors.filter(a=>!(a.textContent||'').trim()&&!a.getAttribute('aria-label')&&!a.querySelector('img[alt]')).map(a=>a.outerHTML.slice(0,160));
    return {unsafe,empty};
   });
   assert.deepEqual(nav.unsafe,[],route.name+' contains unsafe JavaScript links');
   assert.deepEqual(nav.empty,[],route.name+' has links without accessible names');
   // Gate 4: check a narrow mobile viewport for horizontal document overflow.
   await page.setViewportSize({width:390,height:844});
   const mobile=await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,viewport:document.documentElement.clientWidth}));
   assert.ok(mobile.scroll<=mobile.viewport+2,route.name+' has horizontal overflow at 390px');
   await page.setViewportSize({width:1280,height:800});
   await page.screenshot({path:path.join(screenshotDir,route.name.toLowerCase().replace(/[^a-z]+/g,'-')+'-desktop.png'),fullPage:true});
   findings.push({collection:route.name,requests:data,failedRequests:failures,totalResponseBytes:transfers.reduce((n,x)=>n+x.bytes,0),dataResponseBytes:transfers.filter(x=>/\.(json|ndjson|csv|sqlite|db)$/.test(x.path)||x.path.includes('/api/')).reduce((n,x)=>n+x.bytes,0),responseCount:transfers.length});
   await page.close();
  }
  console.log(JSON.stringify({status:'PASS',scope:'browser network request isolation for built routes',findings},null,2));
 }finally{if(browser)await browser.close();server.kill();fs.rmSync(mount,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exitCode=1;});
