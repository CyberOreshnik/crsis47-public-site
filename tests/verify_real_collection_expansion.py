"""Gate 1: prove real uniform website templates accept content-only additions.

Synthetic records are injected into an in-memory copy of the approved catalog.
No production content, approved artwork, or website template is modified.
"""
import copy,hashlib,importlib.util,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("uniform_generator",ROOT/"generate_uniform_site.py")
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
baseline=copy.deepcopy(mod.CAT)
assert len(baseline["books"])>=1 and len(baseline["cases"])>=1
existing_routes=mod.routes()
existing_pages={route:hashlib.sha256(mod.page(route,"en").encode()).hexdigest()
                for route in ("","books/","case-studies/")}
book=copy.deepcopy(baseline["books"][-1])
book.update(id="99",slug="gate1-synthetic-book",title="Gate 1 Synthetic Book",
            description="Non-public test fixture for template expansion")
# Existing approved book detail template requires a substantive synopsis.
book.setdefault("copy",{})["en"]={
 "title":"Gate 1 Synthetic Book",
 "hook":"Non-public integration fixture",
 "paragraphs":["Synthetic content used only for an automated acceptance test."],
 "facts":[]
}
case=copy.deepcopy(baseline["cases"][-1])
case.update(id="099",slug="099-gate1-synthetic-case",title="Gate 1 Synthetic Case",
            description="Non-public test fixture for case expansion",
            cover=None,status="In development",purchase_url=None,price_usd=None,
            available=False,article=None)
try:
 mod.CAT["books"].append(book)
 mod.CAT["cases"].append(case)
 book_route="books/"+book["slug"]+"/"
 case_route="case-studies/"+case["slug"]+"/"
 assert book_route in mod.routes() and case_route in mod.routes()
 assert book_route not in existing_routes and case_route not in existing_routes
 with tempfile.TemporaryDirectory() as directory:
  mod.S=Path(directory)
  for route in (book_route,case_route):
   path=mod.target("en",route)
   path.parent.mkdir(parents=True,exist_ok=True)
   path.write_text(mod.page(route,"en"),encoding="utf-8")
   assert path.exists() and "<h1>" in path.read_text()
  book_html=(mod.S/book_route/"index.html").read_text()
  case_html=(mod.S/case_route/"index.html").read_text()
  assert "Gate 1 Synthetic Book" in book_html
  assert "Gate 1 Synthetic Case" in case_html
  assert "Cover awaiting approval" not in case_html # detail page has no fake cover
  assert "gate1-synthetic-book" in mod.page("books/","en")
  assert "099-gate1-synthetic-case" in mod.page("case-studies/","en")
  assert 'data-page-size="4"' in mod.page("books/","en")
  assert 'data-page-size="4"' in mod.page("case-studies/","en")
 # The original homepage and collection pages necessarily change when a new
 # item is added; their templates, design tokens, and existing items do not.
 assert all(item in mod.CAT["books"] for item in baseline["books"])
 assert all(item in mod.CAT["cases"] for item in baseline["cases"])
 assert len(mod.CAT["books"])==len(baseline["books"])+1
 assert len(mod.CAT["cases"])==len(baseline["cases"])+1
finally:
 mod.CAT=baseline
assert {route:hashlib.sha256(mod.page(route,"en").encode()).hexdigest()
        for route in existing_pages}==existing_pages
print("PASS: synthetic Book and Case Study content entries produce real English detail pages and collection cards without template edits; approved output restored")
