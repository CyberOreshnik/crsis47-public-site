"""Prove adding an item changes only content and generated manifests, not templates."""
import importlib.util,json,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("builder",ROOT/"collections/build_catalogs.py")
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
with tempfile.TemporaryDirectory() as d:
 root=Path(d)
 (root/"collections/content").mkdir(parents=True)
 (root/"collections/registry.json").write_text((ROOT/"collections/registry.json").read_text())
 sample=lambda i,status="published",visibility="public":{"id":f"book-{i:03d}","title":f"Book {i}","slug":f"book-{i}","language":"en","version":"1.0","publication_status":status,"visibility":visibility}
 path=root/"collections/content/books.json"
 path.write_text(json.dumps([sample(i) for i in range(1,6)]+[sample(6,"draft"),sample(7,"published","private")]))
 before=mod.build(root)
 assert before["books"]["count"]==5
 assert len(before["books"]["pages"])==2 # page size four
 assert len(json.loads((root/"collections/generated/books-0001.json").read_text())["items"])==4
 assert len(json.loads((root/"collections/generated/books-0002.json").read_text())["items"])==1
 assert "book-006" not in (root/"collections/generated/books-0002.json").read_text()
 path.write_text(json.dumps([sample(i) for i in range(1,6)]+[sample(6,"draft"),sample(7,"published","private"),sample(8)]))
 after=mod.build(root)
 assert after["books"]["count"]==6
 assert len(after["books"]["pages"])==2
 assert any(x["id"]=="book-008" for x in json.loads((root/"collections/generated/books-0002.json").read_text())["items"])
 assert not (root/"approved-website").exists()
 print("PASS: adding one published item requires content-only edit; pagination and private/draft exclusion verified")

# Independently verify case-study growth and privacy boundaries.
with tempfile.TemporaryDirectory() as d:
 root=Path(d)
 (root/"collections/content").mkdir(parents=True)
 (root/"collections/registry.json").write_text((ROOT/"collections/registry.json").read_text())
 def case(i,status="published",visibility="public"):
  return {"id":f"case-{i:03d}","title":f"Case Study {i}","slug":f"case-{i}","language":"en","version":"1.0","publication_status":status,"visibility":visibility}
 path=root/"collections/content/case-studies.json"
 path.write_text(json.dumps([case(i) for i in range(1,5)]+[case(5,"draft"),case(6,"published","private")]))
 before=mod.build(root)
 assert before["case-studies"]["count"]==4
 assert len(before["case-studies"]["pages"])==1
 path.write_text(json.dumps([case(i) for i in range(1,5)]+[case(5,"draft"),case(6,"published","private"),case(7)]))
 after=mod.build(root)
 assert after["case-studies"]["count"]==5
 assert len(after["case-studies"]["pages"])==2
 second=json.loads((root/"collections/generated/case-studies-0002.json").read_text())
 assert [item["id"] for item in second["items"]]==["case-007"]
 assert not (root/"approved-website").exists()
 print("PASS: case study content-only addition creates second four-item page without publishing drafts or private records")
