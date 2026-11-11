"""Fail-closed acceptance checks for CRSIS-47 Evidence Chamber artwork.

This is a technical gate, not a substitute for visual approval.
Run before any production merge. The owner-approved assets and recorded hashes
must be committed to the development branch before the check can pass.
"""
from pathlib import Path
import hashlib, json, sys

ROOT = Path(__file__).resolve().parents[1]
record = ROOT / "brand/evidence-chamber/approved-artwork-manifest.json"
if not record.is_file():
    sys.exit("BLOCKED: final approved-artwork manifest is missing")

manifest = json.loads(record.read_text(encoding="utf-8"))
required = {
    "header_shield": "brand/evidence-chamber/crsis47-header-shield-approved.png",
    "closing_composition": "brand/evidence-chamber/crsis47-closing-composition-approved.png",
}
for role, relative in required.items():
    item = manifest.get(role)
    if not isinstance(item, dict) or item.get("path") != relative:
        sys.exit(f"BLOCKED: {role} has no approved path")
    expected = item.get("sha256", "")
    if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
        sys.exit(f"BLOCKED: {role} has no recorded SHA-256")
    asset = ROOT / relative
    if not asset.is_file():
        sys.exit(f"BLOCKED: missing {asset}")
    if hashlib.sha256(asset.read_bytes()).hexdigest() != expected:
        sys.exit(f"BLOCKED: checksum mismatch for {role}")

if manifest.get("visual_review") != "owner-approved":
    sys.exit("BLOCKED: final visual review not approved")
if manifest.get("pearl_count") != 5 or manifest.get("extra_dots") is not False:
    sys.exit("BLOCKED: five pearls / zero extra dots not verified")
if manifest.get("gold_oil_lamp") is not True or manifest.get("stemless_acorn") is not True:
    sys.exit("BLOCKED: gold oil lamp and stemless acorn not verified")
print("PASS: approved artwork present and checksum matched; owner visual sign-off recorded")
