"""Create an offline review copy; never modify the production-ready site directory."""
from pathlib import Path
import shutil, re, sys
root=Path(__file__).resolve().parents[1]
source=root/"site"
dest=root/"offline-preview"
if not (source/"index.html").is_file():
    raise SystemExit("Build site/ before offline packaging")
if dest.exists(): shutil.rmtree(dest)
shutil.copytree(source,dest)
prefix="/crsis47-public-site/"
changed=0
for p in dest.rglob("*"):
    if not p.is_file() or p.suffix.lower() not in {".html",".css",".js",".json",".svg",".webmanifest"}: continue
    try: original=p.read_text(encoding="utf-8")
    except UnicodeError: continue
    if prefix not in original: continue
    depth=len(p.relative_to(dest).parts)-1
    relative="../"*depth or "./"
    revised=original.replace(prefix,relative)
    p.write_text(revised,encoding="utf-8")
    changed+=1
assert (dest/"index.html").is_file()
home=(dest/"index.html").read_text(encoding="utf-8")
assert prefix not in home
assert 'href="./' in home or 'src="./' in home
print(f"Offline review copy: {changed} text assets rewritten; original site/ untouched")
