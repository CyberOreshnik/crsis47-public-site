import literature from "../reviewed-literature.json";
import government from "../reviewed-government-evidence.json";
const origin="https://cyberoreshnik.github.io";
const filters=["q","type","lens","from","to","status","collection","project","verification"];
const allowed=new Set([...filters,"limit","cursor"]);
const enc=new TextEncoder();
async function hash(s){return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",enc.encode(s))),x=>x.toString(16).padStart(2,"0")).join("");}
async function records(){
 const out=[],seen=new Set();
 for(const [kind,rows] of [["journal",literature],["government",government]]) for(const r of rows){
  const u=new URL(r.url); if(u.protocol!=="https:"||u.username||u.password)throw Error("invalid manifest");
  const identity=kind==="journal"?(r.doi?.toLowerCase()||r.url):r.url;
  const id=(kind==="journal"?"JOURNAL-":"GOV-")+(await hash(identity)).slice(0,32);
  if(seen.has(id))throw Error("duplicate manifest");seen.add(id);
  out.push({id, title:r.title, url:r.url, description:kind==="journal"?[r.authors.join(", "),r.publisher,r.doi,r.access].filter(Boolean).join(" · "):r.description, source_type:kind==="journal"?"Journal article":"Primary evidence", review_status:"approved", publication_date:r.publication_date, lenses:kind==="journal"?[]:r.lenses, collection:kind==="journal"?"journal-articles":"government-evidence", verification:kind==="journal"?"REVIEWED":"", project_ids:[], citation:kind==="journal"?{source_id:id,authors:r.authors,publisher:r.publisher,doi:r.doi,access:r.access}:undefined, source_status:kind==="government"?r.status:undefined});
 }
 return out.sort((a,b)=>a.id<b.id?-1:a.id>b.id?1:0);
}
let snapshot;
async function getSnapshot(){if(!snapshot)snapshot=records().then(async items=>({items,revision:await hash(JSON.stringify(items))})).catch(e=>{snapshot=undefined;throw e});return snapshot;}
function reply(request,status,data){const headers={"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store","X-Content-Type-Options":"nosniff","Vary":"Origin"};if(request.headers.get("Origin")===origin)headers["Access-Control-Allow-Origin"]=origin;return new Response(JSON.stringify(data),{status,headers});}
async function sign(value,secret){const key=await crypto.subtle.importKey("raw",enc.encode(secret),{name:"HMAC",hash:"SHA-256"},false,["sign"]);return Array.from(new Uint8Array(await crypto.subtle.sign("HMAC",key,enc.encode(value))),x=>x.toString(16).padStart(2,"0")).join("");}
function equal(a,b){if(a.length!==b.length)return false;let n=0;for(let i=0;i<a.length;i++)n|=a.charCodeAt(i)^b.charCodeAt(i);return n===0;}
export default {async fetch(request,env){
 const respond=(s,d)=>reply(request,s,d);
 if(request.method!=="GET")return respond(405,{error:"Method not allowed"});
 if(request.url.length>2048)return respond(414,{error:"Request too long"});
 const u=new URL(request.url);
 if(!["/api/sources","/health"].includes(u.pathname))return respond(404,{error:"Endpoint not found"});
 try{
 const {items,revision}=await getSnapshot();
 if(u.pathname==="/health")return respond(typeof env.CURSOR_SECRET==="string"&&env.CURSOR_SECRET.length>=32&&env.APPROVED_MANIFEST_REVISION===revision?200:503,{status:typeof env.CURSOR_SECRET==="string"&&env.CURSOR_SECRET.length>=32&&env.APPROVED_MANIFEST_REVISION===revision?"ok":"not-ready",revision,mode:"public-manifest-pilot"});
 if(typeof env.CURSOR_SECRET!=="string"||env.CURSOR_SECRET.length<32)return respond(503,{error:"Search temporarily unavailable"});
 if(env.APPROVED_MANIFEST_REVISION!==revision)return respond(503,{error:"Public manifest authorization unavailable"});
 const p=u.searchParams;
 for(const k of p.keys())if(!allowed.has(k)||p.getAll(k).length!==1||p.get(k).length>(k==="cursor"?512:128))return respond(400,{error:"Invalid parameters"});
 const f=Object.fromEntries(filters.map(k=>[k,(p.get(k)||"").trim()]));
 if(f.project)return respond(400,{error:"Project filtering is not supported by this pilot"});
 const rawLimit=p.get("limit")||"25";
 if(!/^[0-9]+$/.test(rawLimit))return respond(400,{error:"Invalid limit"});
 const limit=Number(rawLimit);
 if(!Number.isInteger(limit)||limit<1||limit>25||(f.q&&(f.q.length<3||f.q.includes("\u0000"))))return respond(400,{error:"Invalid parameters"});
 for(const k of ["from","to"])if(f[k]&&(!/^\d{4}-\d{2}-\d{2}$/.test(f[k])||!Number.isFinite(Date.parse(f[k]))||new Date(f[k]).toISOString().slice(0,10)!==f[k]))return respond(400,{error:"Invalid date"});
 if(f.from&&f.to&&f.from>f.to)return respond(400,{error:"Invalid date range"});
 const fingerprint=await hash(JSON.stringify(f));let last="";
 if(p.has("cursor")){
 const parts=p.get("cursor").split(".");if(parts.length!==2||!equal(await sign(parts[0],env.CURSOR_SECRET),parts[1]))return respond(400,{error:"Invalid cursor"});
 let c;try{c=JSON.parse(atob(parts[0]));}catch{return respond(400,{error:"Invalid cursor"});}
 if(c.f!==fingerprint||typeof c.last!=="string")return respond(400,{error:"Invalid cursor"});
 if(c.rev!==revision)return respond(409,{error:"Collection changed. Restart at the first page."});last=c.last;
 }
 const matches=items.filter(r=>r.id>last&&(!f.q||[r.title,r.description].join(" ").toLowerCase().includes(f.q.toLowerCase()))&&(!f.type||r.source_type===f.type)&&(!f.lens||r.lenses.includes(f.lens))&&(!f.status||r.review_status===f.status)&&(!f.collection||r.collection===f.collection)&&(!f.project||r.project_ids.includes(f.project))&&(!f.verification||r.verification===f.verification)&&(!f.from||(r.publication_date&&r.publication_date>=f.from))&&(!f.to||(r.publication_date&&r.publication_date<=f.to)));
 const page=matches.slice(0,limit);let nextCursor=null;
 if(matches.length>limit){const raw=btoa(JSON.stringify({last:page.at(-1).id,f:fingerprint,rev:revision}));nextCursor=raw+"."+await sign(raw,env.CURSOR_SECRET);}
 return respond(200,{items:page,nextCursor});
 }catch{return respond(503,{error:"Search temporarily unavailable"});}
}};
