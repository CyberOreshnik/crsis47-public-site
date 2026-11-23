"""Run Gate 6 checks in an authorized disposable checkout. Output contains statuses only."""
import argparse
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import zipfile

from private_store import inspect

PIPELINE = (
    "prepare_public_site.py", "apply_approved_case_studies.py", "apply_case2_purchase.py",
    "qa/verify_evidence_chamber_release.py", "apply_evidence_chamber.py",
    "apply_frozen_website.py", "generate_uniform_site.py", "publish_research_modules.py",
    "qa/verify_uniform_site.py", "qa/verify_frozen_website.py", "qa/regress_site.py",
    "source-hub-api/check_public_build.py",
)
FLAGS = ("restart_replay", "doi_and_relationships", "synthetic_policy_suspension_revocation",
         "corrupt_rejected_good_restored", "queued_transaction_recovered")
BAD_NAME = re.compile(r"(?:^\.env(?:\.|$)|(?:\.db|\.sqlite3?|\.dpapi|\.key|\.pem)(?:$|[-.])|-(?:wal|shm|journal)$|^intake-token\.txt$)", re.I)
BAD_DATA = re.compile(
    rb"SQLite format 3\x00|-----BEGIN [A-Z ]*PRIVATE KEY-----|\bSRC-[a-f0-9]{32}\b|"
    rb'"(?:receipt|source_id|replay_receipt|second_receipt|token)"\s*:\s*"[a-f0-9]{32,64}"|'
    rb"\bBearer [a-f0-9]{32,64}\b|[A-Z]:[\\/]+Users[\\/]+|"
    rb"(?:^|[\s\"'])/(?:home|Users)/[^/\s]+/|crsis47-private|intake-token\.txt|"
    rb"AQAAANCMnd8BFdERjHoAwE\/Cl\+s", re.I,
)

def scan(site, markers=()):
    if not (site / "source-hub/index.html").is_file():
        raise ValueError("missing_generated_site")
    findings = 0
    count = 0
    tokens = [token.encode().lower() for token in markers]
    def flagged(name, data):
        return (BAD_NAME.search(Path(name).name) or BAD_DATA.search(data)
                or BAD_DATA.search(data.replace(b"\0", b"") if b"\0" in data else data)
                or any(token in data.lower() for token in tokens))
    for path in site.rglob("*"):
        if path.is_symlink():
            findings += 1
            continue
        if not path.is_file():
            continue
        count += 1
        data = path.read_bytes()
        if flagged(path.name, data):
            findings += 1
        if data.startswith(b"PK\x03\x04"):
            with zipfile.ZipFile(path) as archive:
                entries = archive.infolist()
                if len(entries) > 10000 or sum(row.file_size for row in entries) > 256 * 1024 * 1024:
                    raise ValueError("archive_scan_limit")
                for row in entries:
                    member = archive.read(row)
                    if flagged(row.filename, member) or member.startswith(b"PK\x03\x04"):
                        findings += 1
    return {"status": "PASS" if not findings else "HOLD", "files": count, "findings": findings}

def marker_values(path):
    if path is None:
        return []
    markers = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(markers, list) or not markers or any(
        not isinstance(item, str) or not item.strip() for item in markers
    ):
        raise ValueError("invalid_private_marker_list")
    return markers

def check_data(args, result):
    try:
        prior = json.loads(args.prior_evidence.read_text(encoding="utf-8"))
        if not all(prior.get(key) is True for key in FLAGS) or prior.get("old_token_http") != 401:
            raise ValueError("preserved_acceptance_incomplete")
        test = inspect(args.test_registry)
        if test != prior.get("verified") or not test["counts"]["intake_events"]:
            raise ValueError("protected_test_registry_mismatch")
        result["preserved_tests"] = "PASS"
    except (AttributeError, OSError, ValueError, TypeError, KeyError, sqlite3.Error):
        result["preserved_tests"] = "HOLD"
    try:
        if args.legacy_backup.resolve().parent == args.legacy_restore.resolve().parent:
            raise ValueError("separate_restore_required")
        first, second = inspect(args.legacy_backup), inspect(args.legacy_restore)
        expected = json.loads(args.legacy_evidence.read_text(encoding="utf-8"))
        if first != second or first != expected or first["schema_version"] != 0:
            raise ValueError("legacy_restore_mismatch")
        result["legacy_recovery"] = {"status": "PASS", **first}
    except Exception as exc:
        result["legacy_recovery"] = {"status": "HOLD", "error_type": type(exc).__name__}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ci-scan", action="store_true", help="Supporting scan of an already built CI site")
    for name in ("prior-evidence", "test-registry", "legacy-backup", "legacy-restore", "legacy-evidence", "private-markers"):
        parser.add_argument("--" + name, type=Path)
    parser.add_argument("--isolation-reference", help="Operator attestation of authorized external network isolation")
    args = parser.parse_args()
    result = {"scope": "CI supporting evidence" if args.ci_scan else "local Gate 6"}
    if args.ci_scan:
        try:
            result["public_isolation"] = scan(Path("site"), marker_values(args.private_markers))
        except Exception as exc:
            result["public_isolation"] = {"status": "HOLD", "error_type": type(exc).__name__}
        print(json.dumps(result))
        return int(result["public_isolation"]["status"] != "PASS")
    check_data(args, result)
    result["fresh_build"] = {"status": "HOLD"}
    result["public_isolation"] = {"status": "HOLD"}
    try:
        markers = marker_values(args.private_markers)
        if not args.isolation_reference or not args.isolation_reference.strip():
            raise ValueError("approved_external_network_isolation_required")
        if not markers:
            raise ValueError("private_markers_required")
        if Path("site").exists():
            raise ValueError("fresh_disposable_checkout_required")
        for script in PIPELINE:
            completed = subprocess.run([sys.executable, "-X", "utf8", script], timeout=180,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if completed.returncode:
                result["fresh_build"] = {"status": "HOLD", "step": script, "exit_code": completed.returncode}
                break
        else:
            result["fresh_build"] = {"status": "PASS", "steps": len(PIPELINE)}
            result["public_isolation"] = scan(Path("site"), markers)
    except Exception as exc:
        result["blocked_check"] = str(exc) if type(exc) is ValueError and str(exc) in {
            "approved_external_network_isolation_required", "private_markers_required",
            "fresh_disposable_checkout_required", "invalid_private_marker_list"
        } else type(exc).__name__
    passed = (result["preserved_tests"] == "PASS" and result["legacy_recovery"]["status"] == "PASS"
              and result["fresh_build"]["status"] == "PASS" and result["public_isolation"]["status"] == "PASS")
    result["gate6"] = "GO" if passed else "HOLD"
    print(json.dumps(result))
    return int(not passed)

if __name__ == "__main__":
    sys.exit(main())
