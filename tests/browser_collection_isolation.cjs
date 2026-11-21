// Browser network-isolation regression: run after site build using Playwright Chromium.
// npm install --no-save playwright && npx playwright install --with-deps chromium
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const {spawn}=require('node:child_process');
const fs=require('node:fs');
const path=require('node:path');
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
 const server=spawn('python3',['-m','http.server',String(PORT),'--bind','127.0.0.1','--directory',ROOT],{stdio:'ignore'});
 let browser;
 try{
  for(let i=0;i<50;i++){try{const r=await fetch('http://127.0.0.1:'+PORT+'/');if(r.ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
  browser=await chromium.launch({headless:true});
  const findings=[];
  for(const route of routes){
   const page=await browser.newPage();
   const data=[];
   const failures=[];
   page.on('request',r=>{const u=new URL(r.url());if(/\.(json|ndjson|csv|sqlite|db)(?:$|\?)/i.test(u.pathname)||u.pathname.includes('/api/'))data.push(u.pathname);});
   page.on('requestfailed',r=>failures.push(r.url()));
   const response=await page.goto('http://127.0.0.1:'+PORT+route.path,{waitUntil:'networkidle',timeout:30000});
   assert.equal(response.status(),200,route.name+' missing route');
   const foreign=data.filter(p=>{
    const collection=route.name.toLowerCase().replace(/ /g,'-');
    return ['source-hub','labs','glossary','research','books','case-studies'].some(k=>p.includes('/'+k+'/')&&k!==collection);
   });
   assert.deepEqual(foreign,[],route.name+' loaded another collection dataset');
   findings.push({collection:route.name,requests:data,failedRequests:failures});
   await page.close();
  }
  console.log(JSON.stringify({status:'PASS',scope:'browser network request isolation for built routes',findings},null,2));
 }finally{if(browser)await browser.close();server.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
