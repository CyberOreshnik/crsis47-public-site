// Run with Node 22+: node --test source-hub-api/cloudflare-pilot/worker.test.mjs
import test from "node:test";
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
const load=async name=>JSON.parse(await readFile(new URL("../"+name,import.meta.url),"utf8"));
const literature=await load("reviewed-literature.json"), government=await load("reviewed-government-evidence.json");
const source=await readFile(new URL("./worker.mjs",import.meta.url),"utf8");
const worker=new Function("literature","government",source.replace(/^import .*;\n/gm,"").replace("export default","return"))(literature,government);
const env={CURSOR_SECRET:"synthetic-test-only-secret-1234567890"};
const req=(path,method="GET",e=env,headers={})=>worker.fetch(new Request("https://pilot.invalid"+path,{method,headers}),e);
test("health",async()=>assert.equal((await req("/health")).status,200));
test("deny writes and private routes",async()=>{for(const method of ["POST","PUT","PATCH","DELETE"])assert.equal((await req("/api/sources",method)).status,405);assert.equal((await req("/private")).status,404)});
test("missing credential fails closed",async()=>assert.equal((await req("/api/sources","GET",{})).status,503));
test("invalid inputs",async()=>{for(const q of ["limit=26","limit=0","q=ab","q=%00abc","q=abc&q=def","unknown=1","from=2026-02-30","cursor=bad"])assert.equal((await req("/api/sources?"+q)).status,400,q)});
test("public manifest membership and pagination",async()=>{let cursor=null;const items=[];do{const res=await req("/api/sources?limit=7"+(cursor?"&cursor="+encodeURIComponent(cursor):""));assert.equal(res.status,200);const body=await res.json();assert.ok(body.items.length<=7);items.push(...body.items);cursor=body.nextCursor;}while(cursor&&items.length<=literature.length+government.length);assert.equal(items.length,literature.length+government.length);assert.equal(new Set(items.map(x=>x.id)).size,items.length);assert.deepEqual(items.map(x=>x.url).sort(),[...literature,...government].map(x=>x.url).sort());assert.ok(items.every(x=>x.review_status==="approved"));});
test("cursor tampering and filter binding",async()=>{const {nextCursor}=await (await req("/api/sources?limit=1")).json();assert.ok(nextCursor);assert.equal((await req("/api/sources?cursor="+encodeURIComponent(nextCursor+"x"))).status,400);assert.equal((await req("/api/sources?q=CMS&cursor="+encodeURIComponent(nextCursor))).status,400)});
test("CORS exact origin",async()=>{assert.equal((await req("/health","GET",env,{Origin:"https://cyberoreshnik.github.io"})).headers.get("Access-Control-Allow-Origin"),"https://cyberoreshnik.github.io");assert.equal((await req("/health","GET",env,{Origin:"https://other.invalid"})).headers.get("Access-Control-Allow-Origin"),null)});
test("journal filtering",async()=>{const body=await (await req("/api/sources?type=Journal%20article")).json();assert.equal(body.items.length,literature.length)});
