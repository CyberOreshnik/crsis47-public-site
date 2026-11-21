"""Install the reviewed public research modules into generated Pages output."""
import hashlib
import json
import re
from pathlib import Path

SITE = Path("site")
BASE = "/crsis47-public-site/"
MODULES = ("source-hub", "labs/solarwinds-005")
OLD_BACK_LINK = "../approved-website/index.html#research"
LAB_INTRO = (
    '<div class="research-lab-intro">'
    '<img src="' + BASE + 'shield.png" alt="CRSIS-47 Evidence Chamber shield" width="72" '
    'style="display:block;height:auto;margin:1rem 0">'
    '<h3>SolarWinds 005 Decision Lab</h3>'
    '<p>Try a short exercise inspired by the SolarWinds case. You’ll decide how a team '
    'should respond to a software update as new information comes in.</p>'
    '<p>Read the evidence, choose what to do, and explain your decision. '
    'You’ll see what happens before moving to the next round.</p>'
    '<p><a class="button" href="' + BASE + MODULES[1] + '/">Start the SolarWinds lab</a></p>'
    '</div>'
)
SOURCE_HUB = (
    '<details id="source-hub-resource"><summary>Source Hub</summary>'
    '<p><a href="' + BASE + MODULES[0] + '/">'
    'Open the Source Hub →</a></p></details>'
)


def insert_after(html, pattern, addition, page):
    updated, matches = re.subn(pattern, lambda match: match[0] + addition, html)
    if matches != 1:
        raise ValueError(f"{page}: expected one research anchor, found {matches}")
    return updated


def write_page(path, html, hashes):
    destination = SITE / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    data = html.encode("utf-8")
    destination.write_bytes(data)
    hashes[path] = hashlib.sha256(data).hexdigest()


def main():
    uniform_path = SITE / "uniform-manifest.json"
    deployment_path = SITE / "deployment-manifest.json"
    uniform = json.loads(uniform_path.read_text(encoding="utf-8"))
    deployment = json.loads(deployment_path.read_text(encoding="utf-8"))
    hashes = {}
    for module in MODULES:
        path = module + "/index.html"
        html = Path(path).read_text(encoding="utf-8")
        if html.count(OLD_BACK_LINK) != 1:
            raise ValueError(f"{path}: expected one research return link")
        return_path = "research/#division-detail-03" if module.startswith("labs/") else "research/"
        html = html.replace(OLD_BACK_LINK, BASE + return_path)
        write_page(path, html, hashes)

    for page in ("index.html", "research/index.html"):
        html = (SITE / page).read_text(encoding="utf-8")
        html, matches = re.subn(
            r'(<details id="division-detail-03">\s*<summary>[^<]*</summary>)[\s\S]*?</details>',
            lambda match: match[1] + LAB_INTRO + '</details>',
            html,
        )
        if matches != 1:
            raise ValueError(f"{page}: expected one Division 03, found {matches}")
        html = insert_after(
            html, r'<details id="division-detail-04">(?:(?!</details>)[\s\S])*</details>',
            SOURCE_HUB, page,
        )
        write_page(page, html, hashes)

    uniform["files"].update(hashes)
    deployment["uniform_website"] = uniform
    deployment["files"].update(hashes)
    for path, manifest in ((uniform_path, uniform), (deployment_path, deployment)):
        path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("PASS: Source Hub and TIMEPIECE links installed and recorded in release manifests")


if __name__ == "__main__":
    main()
