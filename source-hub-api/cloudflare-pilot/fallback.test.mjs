import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
const script=fs.readFileSync("source-hub/index.html","utf8").match(/<script>([\s\S]*?)<\/script>/)[1];
async function run(search,fetcher){
 const el=()=>({value:"",hidden:false,textContent:"",children:[],addEventListener(){},replaceChildren(){this.children=[]},append(...x){this.children.push(...x)}});
 const elements=Object.fromEntries(["search","type","lens","count","results","first","next","filters","collection","project","verification"].map(k=>[k,el()]));
 vm.runInNewContext(script,{document:{querySelector:()=>({content:"https://pilot.invalid/"}),getElementById:k=>elements[k],createElement:el},window:{addEventListener(){}},fetch:fetcher,URL,URLSearchParams,AbortController,location:{href:"https://example.org/source-hub/"+search,search},history:{}});
 await new Promise(setImmediate);return elements;
}
test("network failure displays labeled offline preview",async()=>{const e=await run("",async()=>{throw Error("offline")});assert.match(e.count.textContent,/Offline venue preview only/);assert.equal(e.results.children.length,4);assert.equal(e.next.hidden,true)});
test("advanced filters never silently discarded",async()=>{const e=await run("?project=unknown",async()=>({ok:false,status:503}));assert.match(e.count.textContent,/cannot apply these filters/);assert.equal(e.results.children.length,0)});
test("stale cursor prompts restart",async()=>{const e=await run("?cursor=old",async()=>({ok:false,status:409}));assert.match(e.count.textContent,/First page/);assert.equal(e.results.children.length,0)});
