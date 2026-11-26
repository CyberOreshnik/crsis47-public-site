import {chromium} from "playwright";
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
const html=await readFile("source-hub/index.html","utf8");
const browser=await chromium.launch({headless:true});
try{
 for(const width of [390,1280]){
 const page=await browser.newPage({viewport:{width,height:900}});
 await page.route("https://site.invalid/**",r=>r.fulfill({contentType:"text/html",body:html}));
 await page.goto("https://site.invalid/source-hub/");
 assert.equal(await page.locator("#results article").count(),4);
 assert.equal(await page.getByRole("heading",{name:"Source Hub",exact:true}).count(),1);
 assert.equal(await page.getByRole("searchbox",{name:"Search sources"}).count(),1);
 assert.equal(await page.locator("#count").getAttribute("aria-live"),"polite");
 await page.getByRole("searchbox").fill("Discover Data");
 await page.getByRole("button",{name:"Search",exact:true}).click();
 assert.equal(await page.locator("#results article").count(),1);
 await page.route("https://site.invalid/pilot",r=>r.fulfill({contentType:"text/html",body:html.replace('name="source-hub-api" content=""','name="source-hub-api" content="https://api.invalid/"')}));
 await page.route("https://api.invalid/**",r=>r.abort());
 await page.goto("https://site.invalid/pilot");
 await page.getByText(/Offline venue preview only/).waitFor();
 assert.equal(await page.locator("#results article").count(),4);
 assert.equal(await page.locator("#next").isVisible(),false);
 await page.close();
 }
 console.log("PASS: Chromium desktop/mobile Source Hub static search, accessible names, offline recovery");
}finally{await browser.close();}
