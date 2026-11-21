"""Install additive Research & Laboratories links and reviewed public modules after frozen release assembly."""
from pathlib import Path
import shutil
site=Path("site")
for name in ("source-hub","labs/solarwinds-005"):
    src=Path(name)
    dest=site/name
    assert (src/"index.html").is_file(), name
    dest.mkdir(parents=True,exist_ok=True)
    shutil.copy2(src/"index.html",dest/"index.html")
page=site/"index.html"
assert page.is_file()
html=page.read_text(encoding="utf-8")
anchor='<details id="division-detail-03"><summary>Division 03 — Research Labs & Prototypes</summary>'
assert anchor in html,"Expected approved research division not found"
if 'href="labs/solarwinds-005/"' not in html:
    html=html.replace(anchor,anchor+'<p><a href="labs/solarwinds-005/">Launch TIMEPIECE — SolarWinds 005 interactive lab →</a></p>',1)
anchor2='<div class="research-details"><h3>Explore the four divisions</h3>'
assert anchor2 in html,"Expected approved research details not found"
if 'href="source-hub/"' not in html:
    html=html.replace(anchor2,'<div class="research-details"><p><a class="glossary-feature" href="source-hub/"><span class="glossary-feature-title">SOURCE HUB — SCHOLARLY &amp; INVESTIGATIVE EVIDENCE</span><span class="glossary-feature-sub">Search research journals and evidence through PGDT.</span><span class="glossary-feature-action">OPEN THE SOURCE HUB →</span></a></p><h3>Explore the four divisions</h3>',1)
page.write_text(html,encoding="utf-8")
for p in (site/"source-hub/index.html",site/"labs/solarwinds-005/index.html"):
    text=p.read_text(encoding="utf-8")
    text=text.replace('../approved-website/index.html#research','../index.html#research')
    if p.parent.name=="solarwinds-005":
        text=text.replace('../index.html#research','../../index.html#research')
    p.write_text(text,encoding="utf-8")
print("PASS: public Research & Laboratories includes Source Hub and TIMEPIECE launch links")
