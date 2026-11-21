"""Zero-cost local Source Hub API prototype; stdlib SQLite + HTTP only."""
import base64
import hashlib
import hmac
import json
import os
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

DB = os.environ.get("SOURCE_HUB_DB", "source-hub.db")
SECRET = os.environ.get("SOURCE_HUB_CURSOR_SECRET", "local-development-only").encode()
SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
 id INTEGER PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL,
 source_type TEXT NOT NULL, pgdt_lens TEXT NOT NULL,
 publication_date TEXT, review_status TEXT NOT NULL,
 visibility TEXT NOT NULL CHECK(visibility IN ('public','draft','restricted')),
 url TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS source_public_order ON sources(visibility,id);
CREATE INDEX IF NOT EXISTS source_type_order ON sources(visibility,source_type,id);
CREATE INDEX IF NOT EXISTS source_lens_order ON sources(visibility,pgdt_lens,id);
CREATE INDEX IF NOT EXISTS source_date_order ON sources(visibility,publication_date,id);
"""
def connect():
 db=sqlite3.connect(DB)
 db.row_factory=sqlite3.Row
 db.executescript(SCHEMA)
 return db
def token(last, fingerprint):
 raw=json.dumps({"last":last,"f":fingerprint},separators=(",",":")).encode()
 sig=hmac.new(SECRET,raw,hashlib.sha256).digest()
 return base64.urlsafe_b64encode(raw+sig).decode().rstrip("=")
def untoken(value, fingerprint):
 try:
  data=base64.urlsafe_b64decode(value+"="*(-len(value)%4))
  raw,sig=data[:-32],data[-32:]
  if not hmac.compare_digest(hmac.new(SECRET,raw,hashlib.sha256).digest(),sig): raise ValueError()
  payload=json.loads(raw)
  if payload["f"]!=fingerprint or type(payload["last"]) is not int: raise ValueError()
  return payload["last"]
 except Exception: raise ValueError("Invalid cursor")
def search(params):
 allowed={"q","type","lens","from","to","status","limit","cursor"}
 if set(params)-allowed or any(len(v)!=1 for v in params.values()): raise ValueError("Invalid parameters")
 get=lambda k:params.get(k,[""])[0].strip()
 limit=int(get("limit") or "25")
 if limit<1 or limit>25: raise ValueError("Limit must be 1..25")
 filters={k:get(k) for k in ("q","type","lens","from","to","status")}
 fingerprint=hashlib.sha256(json.dumps(filters,sort_keys=True).encode()).hexdigest()
 last=untoken(get("cursor"),fingerprint) if get("cursor") else 0
 clauses=["visibility='public'","id>?" ];args=[last]
 for key,col in (("type","source_type"),("lens","pgdt_lens"),("status","review_status")):
  if filters[key]:clauses.append(col+"=?");args.append(filters[key])
 if filters["from"]:clauses.append("publication_date>=?");args.append(filters["from"])
 if filters["to"]:clauses.append("publication_date<=?");args.append(filters["to"])
 if filters["q"]:
  clauses.append("(title LIKE ? OR description LIKE ?)")
  pattern="%"+filters["q"].replace("%","\\%").replace("_","\\_")+"%"
  args.extend([pattern,pattern])
 with connect() as db:
  rows=db.execute("SELECT id,title,description,source_type,pgdt_lens,publication_date,review_status,url FROM sources WHERE "+" AND ".join(clauses)+" ORDER BY id LIMIT ?",args+[limit+1]).fetchall()
 more=len(rows)>limit;items=[dict(x) for x in rows[:limit]]
 return {"items":items,"nextCursor":token(items[-1]["id"],fingerprint) if more else None}
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  parsed=urlsplit(self.path)
  if parsed.path!="/api/sources":self.send_error(404);return
  try:body=json.dumps(search(parse_qs(parsed.query,keep_blank_values=True))).encode();status=200
  except (ValueError,sqlite3.Error) as exc:body=json.dumps({"error":str(exc)}).encode();status=400
  self.send_response(status);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
if __name__=="__main__":
 print("Local-only API at http://127.0.0.1:8765/api/sources")
 ThreadingHTTPServer(("127.0.0.1",8765),Handler).serve_forever()
