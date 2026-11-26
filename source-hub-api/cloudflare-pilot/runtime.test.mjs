import test from "node:test";
import assert from "node:assert/strict";
import {Miniflare} from "miniflare";
import {build} from "esbuild";
const result=await build({entryPoints:["source-hub-api/cloudflare-pilot/worker.mjs"],bundle:true,format:"esm",write:false,platform:"browser"});
const secret="synthetic-local-only-secret-1234567890";
const options={modules:true,script:result.outputFiles[0].text,compatibilityDate:"2025-01-01",bindings:{CURSOR_SECRET:secret}};
test("local workerd runtime",async()=>{
 const mf=new Miniflare(options);
 try {
 const health=await mf.dispatchFetch("http://localhost/health");
 assert.equal(health.status,503);
 const {revision}=await health.json();
 await mf.setOptions({...options,bindings:{...options.bindings,APPROVED_MANIFEST_REVISION:revision}});
 assert.equal((await mf.dispatchFetch("http://localhost/health")).status,200);
 let cursor=null;const ids=[];
 do {const res=await mf.dispatchFetch("http://localhost/api/sources?limit=7"+(cursor?"&cursor="+encodeURIComponent(cursor):""));assert.equal(res.status,200);const p=await res.json();ids.push(...p.items.map(x=>x.id));cursor=p.nextCursor;}while(cursor&&ids.length<=30);
 assert.equal(ids.length,30);assert.equal(new Set(ids).size,30);
 assert.equal((await mf.dispatchFetch("http://localhost/api/sources?project=unknown")).status,400);
 assert.equal((await mf.dispatchFetch("http://localhost/private")).status,404);
 }finally{await mf.dispose();}
});
