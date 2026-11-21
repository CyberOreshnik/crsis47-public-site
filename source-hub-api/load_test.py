"""Deterministic 500k-record zero-cost Source Hub validation. Run: python3 source-hub-api/load_test.py"""
import importlib.util, json, os, sqlite3, statistics, tempfile, time
from pathlib import Path
N=int(os.environ.get("SOURCE_HUB_TEST_RECORDS","500000"))
path=Path(__file__).with_name("server.py")
spec=importlib.util.spec_from_file_location("source_hub_api",path)
api=importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)
with tempfile.TemporaryDirectory() as directory:
 api.DB=str(Path(directory)/"sources.sqlite")
 db=api.connect()
 start=time.perf_counter()
 for first in range(1,N+1,5000):
  rows=[(i,f"Evidence {i:07d}",f"Synthetic incident evidence {i}",["Journal","Article","Primary evidence"][i%3],["People","Governance","Data","Technology"][i%4],f"202{(i%6)}-01-01","approved" if i%7 else "pending","restricted" if i%11==0 else ("draft" if i%13==0 else "public"),f"https://example.org/{i}") for i in range(first,min(first+5000,N+1))]
  db.executemany("INSERT INTO sources(id,title,description,source_type,pgdt_lens,publication_date,review_status,visibility,url) VALUES(?,?,?,?,?,?,?,?,?)",rows)
 db.commit()
 seed_seconds=round(time.perf_counter()-start,3)
 print("seeded",N,"records in",seed_seconds,"seconds")
 timings=[]
 for q in ({"limit":["25"]},{"type":["Journal"],"lens":["Data"]},{"q":["Evidence 004"]},{"status":["approved"]}):
  started=time.perf_counter();res=api.search(q);timings.append((time.perf_counter()-started)*1000)
  assert len(res["items"])<=25
  assert all(x["id"]%11!=0 and x["id"]%13!=0 for x in res["items"])
  print("query",q,"results",len(res["items"]),"ms",round(timings[-1],2),"payload_bytes",len(json.dumps(res)))
 seen=set();cursor=None;pages=0
 while True:
  params={"limit":["25"]}
  if cursor:params["cursor"]=[cursor]
  result=api.search(params)
  for item in result["items"]:
   assert item["id"] not in seen,("duplicate",item["id"])
   seen.add(item["id"])
  pages+=1;cursor=result["nextCursor"]
  if not cursor:break
 expected=sum(i%11!=0 and i%13!=0 for i in range(1,N+1))
 assert len(seen)==expected,(len(seen),expected)
 try:api.search({"limit":["26"]});raise AssertionError("limit bypass")
 except ValueError:pass
 try:api.search({"cursor":["tampered"]});raise AssertionError("cursor bypass")
 except ValueError:pass
 print(json.dumps({"records":N,"public_records":expected,"pages":pages,"unique_ids":len(seen),"sample_latency_ms":timings,"status":"PASS"},indent=2))
