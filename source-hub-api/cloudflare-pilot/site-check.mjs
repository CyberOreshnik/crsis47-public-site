import {chromium} from "playwright";
import {execFileSync} from "node:child_process";
import {readFile,stat} from "node:fs/promises";
import {resolve,dirname} from "node:path";
import assert from "node:assert/strict";
const baseline="245761b3b83dcb17d1d9b0bc9180f01fb3df3c40";
const files=execFileSync("git",["ls-files"],{encoding:"utf8"}).trim().split("\n");
const pages=files.filter(x=>x.endsWith(".html"));
const browser=await chromium.launch();
const issues=[];
try{
const page=await browser.newPage();
for(const file of pages){
 const html=await readFile(file,"utf8");
 await page.setContent(html,{waitUntil:"domcontentloaded"});
 const links=await page.locator("a[href],img[src]").evaluateAll(es=>es.map(e=>e.getAttribute(e.tagName==="A"?"href":"src")));
 for(const link of links){
 if(!link||/^(?:[a-z]+:|\/\/|#)/i.test(link))continue;
 const path=link.split(/[?#]/)[0];if(!path)continue;
 const target=resolve(path.startsWith("/")?".":dirname(file),decodeURIComponent(path.replace(/^\//,"")));
 try{const s=await stat(target);if(s.isDirectory())await stat(resolve(target,"index.html"));}catch{issues.push({file,link});}
 }
}
console.log(JSON.stringify({pages:pages.length,localLinkIssues:issues},null,2));
assert.equal(issues.length,0,"Local link failures require review");
}finally{await browser.close();}
