"""Deterministic 500k-record zero-cost Source Hub validation. Run: python3 source-hub-api/load_test.py"""
import importlib.util, json, os, sqlite3, statistics, tempfile, time
from pathlib import Path
from threading import Thread
from urllib.request import Request, urlopen
from urllib.error import HTTPError
N=int(os.environ.get("SOURCE_HUB_TEST_RECORDS","500000"))
path=Path(__file__).with_name("server.py")
spec=importlib.util.spec_from_file_location("source_hub_api",path)
api=importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)
with tempfile.TemporaryDirectory() as directory:
 api.DB=str(Path(directory)/"sources.sqlite")
 api.initialize()
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
  assert all(x["id"]%11!=0 and x["id"]%13!=0 and x["id"]%7!=0 for x in res["items"])
  print("query",q,"results",len(res["items"]),"ms",round(timings[-1],2),"payload_bytes",len(json.dumps(res)))
 expected_ids=(i for i in range(1,N+1) if i%11 and i%13 and i%7)
 count=0;cursor=None;pages=0;page_times=[];max_payload=0
 while True:
  params={"limit":["25"]}
  if cursor:params["cursor"]=[cursor]
  started=time.perf_counter();result=api.search(params)
  page_times.append((time.perf_counter()-started)*1000)
  max_payload=max(max_payload,len(json.dumps(result).encode()))
  for item in result["items"]:
   assert item["id"]==next(expected_ids,None),("out of order",item["id"])
   count+=1
  pages+=1;cursor=result["nextCursor"]
  if not cursor:break
 expected=sum(i%11!=0 and i%13!=0 and i%7!=0 for i in range(1,N+1))
 assert next(expected_ids,None) is None and count==expected
 for sql in ("UPDATE sources SET visibility='restricted' WHERE id=1","DELETE FROM sources WHERE id=2","INSERT INTO sources SELECT id+?,title,description,source_type,pgdt_lens,publication_date,review_status,visibility,url FROM sources WHERE id=3"):
  old=api.search({})["nextCursor"]
  db.execute(sql,(N,) if "?" in sql else ());db.commit()
  try:api.search({"cursor":[old]});raise AssertionError("stale cursor accepted")
  except api.StaleCursor:pass
 plans={k:[row[3] for row in db.execute("EXPLAIN QUERY PLAN "+query)] for k,query in {"keyset":"SELECT id FROM sources WHERE visibility='public' AND review_status='approved' AND id>0 ORDER BY id LIMIT 26","text":"SELECT rowid FROM source_text WHERE source_text MATCH 'evidence'"}.items()}
 db.close()
 api.ORIGIN="https://example.org"
 with api.ThreadingHTTPServer(("127.0.0.1",0),api.Handler) as http:
  worker=Thread(target=http.serve_forever,daemon=True);worker.start()
  endpoint=f"http://127.0.0.1:{http.server_port}/api/sources"
  try:
   for origin in (api.ORIGIN,"https://other.example"):
    with urlopen(Request(endpoint,headers={"Origin":origin}),timeout=5) as response:
     assert len(json.load(response)["items"])==25
     assert response.headers.get("Access-Control-Allow-Origin")== (origin if origin==api.ORIGIN else None)
   try:urlopen(endpoint+"?limit=26",timeout=5);raise AssertionError("invalid HTTP request accepted")
   except HTTPError as error:
    assert error.code==400
    error.close()
  finally:
   http.shutdown();worker.join()
 quantiles=statistics.quantiles(page_times,n=100,method="inclusive")
 try:api.search({"limit":["26"]});raise AssertionError("limit bypass")
 except ValueError:pass
 try:api.search({"cursor":["tampered"]});raise AssertionError("cursor bypass")
 except ValueError:pass
 for invalid in ({"from":["2023-02-29"]},{"from":["2024-01-02"],"to":["2024-01-01"]},{"q":["a"]},{"lens":["Data","People"]}):
  try:api.search(invalid);raise AssertionError("invalid parameters accepted")
  except ValueError:pass
 assert api.search({"status":["pending"]})["items"]==[]
 assert api.search({"q":['" OR %_']})["items"]==[]
 print(json.dumps({"records":N,"public_records":expected,"pages":pages,"unique_ids":count,"p50_ms":quantiles[49],"p95_ms":quantiles[94],"p99_ms":quantiles[98],"max_payload_bytes":max_payload,"query_plans":plans,"sample_latency_ms":timings,"status":"PASS"},indent=2))
