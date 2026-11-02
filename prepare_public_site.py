from pathlib import Path
import base64, hashlib, io, zipfile, json, re
parts=sorted(Path("release").glob("part-*.b64"))
assert len(parts)==46, "Incomplete release"
data=b"".join(base64.b64decode(p.read_text().strip(),validate=True) for p in parts)
assert hashlib.sha256(data).hexdigest()=="de3c2d2a293c5298c3593b8c958e0ccd3c72825493f1fcfab9950abd804a6c30", "Archive checksum mismatch"
out=Path("site"); out.mkdir(exist_ok=True)
forbidden={".doc",".docx",".pdf",".xlsx",".xls",".ppt",".pptx",".zip",".db",".sqlite",".pem",".key",".map"}
with zipfile.ZipFile(io.BytesIO(data)) as z:
 for item in z.infolist():
  p=Path(item.filename)
  assert not p.is_absolute() and ".." not in p.parts, "Unsafe archive path"
  assert not any(v.lower() in {"private","confidential","manuscripts","credentials","secrets",".git"} for v in p.parts), "Private path"
  assert p.suffix.lower() not in forbidden, "Restricted file"
  if item.is_dir(): continue
  payload=z.read(item)
  if p.suffix in {".html",".js",".css",".json",".txt",".rsc",".xml"}:
   text=payload.decode("utf-8")
   assert not re.search(r"libfile_[a-f0-9]{32}|[A-Za-z]:[\\/]Users[\\/]",text), "Private marker"
   text=text.replace("/crsis47-author-website","/crsis47-public-site.")
   payload=text.encode("utf-8")
  target=out/p; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(payload)
(out/".nojekyll").write_text("")
assert (out/"index.html").is_file()
assert (out/"case-studies/index.html").is_file()
assert (out/"case-studies/Binance_First_Case_Study_Free.html").is_file()
case=(out/"case-studies/index.html").read_text()
assert "By Constantin Jean-Pierre" in case and "download" in case
assert "noindex" not in case.split("</head>")[0]
for p in out.rglob("*.html"):
 for dest in re.findall(r'(?:href|src)="([^"]+)"',p.read_text()):
  if dest.startswith("/") and not dest.startswith("//"):
   assert dest.startswith("/crsis47-public-site./"), (str(p),dest)
manifest={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob("*") if p.is_file()}
(out/"deployment-manifest.json").write_text(json.dumps({"source_commit":"f414f6eccdc271c5a03d4d763e16a2a2b51f6c02","archive_sha256":hashlib.sha256(data).hexdigest(),"files":manifest},indent=2))
print("PASS",len(manifest),"public files; verified archive; deployment paths updated")
