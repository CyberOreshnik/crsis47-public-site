"""Install the reviewed public research modules into generated Pages output."""
from html import escape
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

SITE = Path("site")
BASE = "/crsis47-public-site/"
REGISTRY = Path("collections/registry.json")

def registered_collection(collection_id):
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    matches = [entry for entry in registry["collections"] if entry["id"] == collection_id]
    if len(matches) != 1:
        raise ValueError(f"Missing or duplicate registered collection: {collection_id}")
    return matches[0]

OLD_BACK_LINK = "../approved-website/index.html#research"
def lab_intro(labs):
    cards = []
    for lab in labs:
        title = escape(lab["title"])
        description = escape(lab["description"])
        url = escape(lab["launch_url"], quote=True)
        cards.append(
            f'<li><h4>{title}</h4><p>{description}</p>'
            f'<p><a class="button" href="{url}" aria-label="Launch {title} in TIMEPIECE">'
            'Launch TIMEPIECE</a></p></li>'
        )
    return (
        '<div class="research-lab-intro">'
        '<img src="' + BASE + 'shield.png" alt="CRSIS-47 Evidence Chamber shield" width="72" '
        'style="display:block;height:auto;margin:1rem 0">'
        '<h3>CRSIS-47 TIMEPIECE</h3>'
        '<p>Choose an exercise. Read the evidence, decide what to do, and explain why.</p>'
        + ('<ul>' + ''.join(cards) + '</ul>' if cards else '<p>No public exercises are available yet.</p>')
        + '</div>'
    )


def public_labs():
    catalog_path = Path(registered_collection("timepiece")["manifest"])
    entries = json.loads(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(entries, list):
        raise ValueError("Lab catalog must be a list")
    seen = set()
    labs = []
    for entry in entries:
        slug = entry.get("slug", "")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) or slug in seen:
            raise ValueError(f"Invalid or duplicate lab slug: {slug!r}")
        seen.add(slug)
        if entry.get("status") not in ("draft", "published"):
            raise ValueError(f"{slug}: expected draft or published status")
        if entry["status"] == "draft":
            continue
        for field in ("title", "description"):
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                raise ValueError(f"{slug}: missing {field}")
        local_path = f"labs/{slug}" if "hosted_url" not in entry else None
        if local_path:
            url = BASE + local_path + "/"
        else:
            url = entry["hosted_url"]
            target = urlsplit(url)
            if target.scheme != "https" or not target.hostname or target.username is not None:
                raise ValueError(f"{slug}: hosted lab must have an HTTPS launch URL")
        labs.append(dict(entry, launch_url=url, local_path=local_path))
    return labs


SOURCE_HUB = (
    '<details id="source-hub-resource"><summary>Source Hub</summary>'
    '<p><a href="' + BASE + "source-hub" + '/">'
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
    # Publish registry metadata for on-demand readers; preserve existing site layout.
    registry_path = "collections/registry.json"
    write_page(registry_path, REGISTRY.read_text(encoding="utf-8"), hashes)
    # Export approved, validated collection metadata to the deployed site.\n    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))\n    by_id = {item["id"]: item for item in registry["collections"]}\n    for cid, expected in (("glossary", "/glossary.html"), ("research", "/research/"), ("source-hub", "/source-hub/")):\n        if cid not in by_id or by_id[cid]["route"] != expected:\n            raise ValueError(f"{cid}: approved route does not match registry")\n    labs = public_labs()
    intro = lab_intro(labs)
    local_modules = ["source-hub", *(lab["local_path"] for lab in labs if lab["local_path"])]
    for module in local_modules:
        path = module + "/index.html"
        html = Path(path).read_text(encoding="utf-8")
        if html.count(OLD_BACK_LINK) > 1:
            raise ValueError(f"{path}: duplicate research return link")
        return_path = "research/#division-detail-03" if module.startswith("labs/") else "research/"
        html = html.replace(OLD_BACK_LINK, BASE + return_path)
        write_page(path, html, hashes)

    for page in ("index.html", "research/index.html"):
        html = (SITE / page).read_text(encoding="utf-8")
        html, matches = re.subn(
            r'(<details id="division-detail-03">\s*<summary>[^<]*</summary>)[\s\S]*?</details>',
            lambda match: match[1] + intro + '</details>',
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
