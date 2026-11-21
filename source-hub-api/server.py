"""Zero-cost local Source Hub API prototype; stdlib SQLite + HTTP only."""
import base64
import hashlib
import hmac
import json
import os
import sqlite3
import secrets
import re
from contextlib import closing
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

DB = os.environ.get("SOURCE_HUB_DB", "source-hub.db")
SECRET = os.environ.get("SOURCE_HUB_CURSOR_SECRET", "").encode() or secrets.token_bytes(32)
ORIGIN = os.getenv("SOURCE_HUB_ALLOWED_ORIGIN")

class StaleCursor(ValueError):
 pass
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
CREATE INDEX IF NOT EXISTS source_public_approved ON sources(visibility,review_status,id);
CREATE TABLE IF NOT EXISTS revision(id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL, epoch TEXT NOT NULL);
INSERT OR IGNORE INTO revision VALUES(1,0,lower(hex(randomblob(16))));
CREATE VIRTUAL TABLE IF NOT EXISTS source_text USING fts5(title,description,content='sources',content_rowid='id',tokenize='trigram');
CREATE TRIGGER IF NOT EXISTS source_insert AFTER INSERT ON sources BEGIN
 
 INSERT INTO source_text(rowid,title,description) VALUES(new.id,new.title,new.description);
 UPDATE revision SET version=version+1 WHERE id=1;
END;
CREATE TRIGGER IF NOT EXISTS source_update AFTER UPDATE ON sources BEGIN
 INSERT INTO source_text(source_text,rowid,title,description) VALUES('delete',old.id,old.title,old.description);
 INSERT INTO source_text(rowid,title,description) VALUES(new.id,new.title,new.description);
 UPDATE revision SET version=version+1 WHERE id=1;
END;
CREATE TRIGGER IF NOT EXISTS source_delete AFTER DELETE ON sources BEGIN
 INSERT INTO source_text(source_text,rowid,title,description) VALUES('delete',old.id,old.title,old.description);
 
 UPDATE revision SET version=version+1 WHERE id=1;
END;
"""
def initialize():
 with closing(sqlite3.connect(DB)) as db:
  db.execute("PRAGMA journal_mode=WAL")
  db.executescript("BEGIN IMMEDIATE;" + SCHEMA + "INSERT INTO source_text(source_text) VALUES('rebuild');COMMIT;")

def connect():
 db=sqlite3.connect(DB)
 db.row_factory=sqlite3.Row
 return db
def token(last, fingerprint, revision, epoch):
 raw=json.dumps({"last":last,"f":fingerprint,"revision":revision,"epoch":epoch},separators=(",",":")).encode()
 sig=hmac.new(SECRET,raw,hashlib.sha256).digest()
 return base64.urlsafe_b64encode(raw+sig).decode().rstrip("=")
def untoken(value, fingerprint):
 try:
  data=base64.urlsafe_b64decode(value+"="*(-len(value)%4))
  raw,sig=data[:-32],data[-32:]
  if not hmac.compare_digest(hmac.new(SECRET,raw,hashlib.sha256).digest(),sig): raise ValueError()
  payload=json.loads(raw)
  if payload["f"]!=fingerprint or type(payload["last"]) is not int: raise ValueError()
  return payload["last"],payload["revision"],payload["epoch"]
 except (ValueError, TypeError, KeyError): raise ValueError("Invalid cursor") from None
def search(params):
 allowed={"q","type","lens","from","to","status","limit","cursor"}
 if set(params)-allowed or any(len(v)!=1 for v in params.values()): raise ValueError("Invalid parameters")
 get=lambda k:params.get(k,[""])[0].strip()
 if any(len(get(k))>(512 if k=="cursor" else 128) for k in allowed): raise ValueError("Parameter too long")
 limit=int(get("limit") or "25")
 if limit<1 or limit>25: raise ValueError("Limit must be 1..25")
 filters={k:get(k) for k in ("q","type","lens","from","to","status")}
 fingerprint=hashlib.sha256(json.dumps(filters,sort_keys=True).encode()).hexdigest()
 for key in ("from","to"):
  value=filters[key]
  if value and (not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}",value) or date.fromisoformat(value).isoformat()!=value):
   raise ValueError("Dates must use YYYY-MM-DD")
 if filters["from"] and filters["to"] and filters["from"]>filters["to"]: raise ValueError("Invalid date range")
 cursor=untoken(get("cursor"),fingerprint) if get("cursor") else None
 clauses=["visibility='public'","review_status='approved'","id>?"];args=[cursor[0] if cursor else 0]
 for key,col in (("type","source_type"),("lens","pgdt_lens"),("status","review_status")):
  if filters[key]:clauses.append(col+"=?");args.append(filters[key])
 if filters["from"]:clauses.append("publication_date>=?");args.append(filters["from"])
 if filters["to"]:clauses.append("publication_date<=?");args.append(filters["to"])
 if filters["q"]:
  term=filters["q"]
  if len(term)<3 or "\x00" in term: raise ValueError("Search needs three or more characters")
  clauses.append("id IN (SELECT rowid FROM source_text WHERE source_text MATCH ?)")
  args.append('"' + term.replace('"','""') + '"')
 with closing(connect()) as db:
  db.execute("PRAGMA query_only=ON")
  db.execute("BEGIN")
  revision,epoch=db.execute("SELECT version,epoch FROM revision WHERE id=1").fetchone()
  if cursor and cursor[1:]!=(revision,epoch): raise StaleCursor("Collection changed. Restart at the first page.")
  rows=db.execute("SELECT id,substr(title,1,256) AS title,substr(description,1,1024) AS description,substr(source_type,1,64) AS source_type,substr(pgdt_lens,1,64) AS pgdt_lens,substr(publication_date,1,10) AS publication_date,review_status,CASE WHEN length(url)<=2048 THEN url END AS url FROM sources WHERE "+" AND ".join(clauses)+" ORDER BY id LIMIT ?",args+[limit+1]).fetchall()
 more=len(rows)>limit;items=[dict(x) for x in rows[:limit]]
 return {"items":items,"nextCursor":token(items[-1]["id"],fingerprint,revision,epoch) if more else None}
class Handler(BaseHTTPRequestHandler):
 def log_message(self, format, *args):
  pass

 def do_GET(self):
  try:
   if len(self.path)>2048:
    self.respond(414,{"error":"Request too long"});return
   parsed=urlsplit(self.path)
   if parsed.path!="/api/sources":
    self.respond(404,{"error":"Endpoint not found"});return
   self.respond(200,search(parse_qs(parsed.query,keep_blank_values=True,max_num_fields=8,errors="strict")))
  except StaleCursor as exc:
   self.respond(409,{"error":str(exc)})
  except ValueError:
   self.respond(400,{"error":"Invalid parameters or cursor"})
  except sqlite3.Error:
   self.respond(503,{"error":"Search temporarily unavailable"})

 def respond(self,status,payload):
  body=json.dumps(payload,ensure_ascii=False).encode()
  self.send_response(status)
  self.send_header("Content-Type","application/json; charset=utf-8")
  self.send_header("Content-Length",str(len(body)))
  self.send_header("X-Content-Type-Options","nosniff")
  self.send_header("Cache-Control","no-store")
  self.send_header("Vary","Origin")
  if ORIGIN and self.headers.get("Origin")==ORIGIN:
   self.send_header("Access-Control-Allow-Origin",ORIGIN)
  self.end_headers()
  self.wfile.write(body)

if __name__=="__main__":
 initialize()
 print("Local-only API at http://127.0.0.1:8765/api/sources")
 ThreadingHTTPServer(("127.0.0.1",8765),Handler).serve_forever()
