"""Publish reviewed journal manifests and explicitly approved synthetic snapshots."""
import argparse
from contextlib import closing
from datetime import date as datetime_date
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

import ingest
import server

def approve_snapshot(path, source_id):
    with closing(ingest.connect(path)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM registry WHERE id=?", (source_id,)).fetchone()
        if not row or row["classification"] != "REVIEW_REQUIRED":
            raise ValueError("source_not_eligible")
        item = json.loads(row["metadata"])
        if item["evidence_type"] in ingest.PRIVATE_TYPES or not item["source_url"].startswith("https://example.org/synthetic/"):
            raise ValueError("source_not_eligible")
        projects = [r[0] for r in db.execute(
            "SELECT DISTINCT project FROM relationships WHERE source_id=? ORDER BY project", (source_id,))]
        if len(projects) > 64:
            raise ValueError("projection_project_limit")
        snapshot = dict(item, source_id=source_id, project_ids=projects, collection=row["collection"],
                        verification=row["verification"], schema_version=1)
        db.execute("INSERT INTO audit(source_id,receipt,action,detail,at) VALUES(?,?,?,?,?)",
                   (source_id, "", "APPROVED_SYNTHETIC_SNAPSHOT", ingest.encode(snapshot), ingest.now()))
        return snapshot

def import_snapshot(db, snapshot):
    """Local operator only, with output from approve_snapshot as the trusted input."""
    if (snapshot["schema_version"] != 1 or snapshot["evidence_type"] in ingest.PRIVATE_TYPES
        or not snapshot["source_url"].startswith("https://example.org/synthetic/")):
        raise ValueError("unsupported_projection")
    if len(snapshot["project_ids"]) > 64:
        raise ValueError("projection_project_limit")
    item = db.execute("SELECT source_row FROM public_provenance WHERE source_id=?", (snapshot["source_id"],)).fetchone()
    description = " · ".join(filter(None, [
        ", ".join(snapshot["authors"]), snapshot["publisher"], snapshot["doi"], snapshot["source_id"]
    ]))
    args = (snapshot["title"] or "Untitled synthetic source", description, snapshot["evidence_type"],
            snapshot["pgdt_lens"] or "", snapshot["publication_date"], snapshot["source_url"])
    if item:
        row_id = item[0]
        db.execute("""UPDATE sources SET title=?,description=?,source_type=?,pgdt_lens=?,
                      publication_date=?,url=? WHERE id=?""", (*args, row_id))
    else:
        row_id = db.execute("""INSERT INTO sources(title,description,source_type,pgdt_lens,
                         publication_date,url,review_status,visibility) VALUES(?,?,?,?,?,?,'approved','public')""", args).lastrowid
    db.execute("""INSERT INTO public_provenance VALUES(?,?,?,?,?) ON CONFLICT(source_row) DO UPDATE
                  SET collection=excluded.collection,verification=excluded.verification,citation_json=excluded.citation_json""",
               (row_id, snapshot["source_id"], snapshot["collection"], snapshot["verification"], ingest.encode(snapshot)))
    db.execute("DELETE FROM public_projects WHERE source_row=?", (row_id,))
    db.executemany("INSERT INTO public_projects VALUES(?,?)",
                   ((row_id, project) for project in snapshot["project_ids"]))

def project_demo(private_path, source_id):
    if Path(private_path).resolve() == Path(server.DB).resolve():
        raise ValueError("private_and_public_databases_must_differ")
    snapshot = approve_snapshot(private_path, source_id)
    with closing(server.connect()) as db, db:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("BEGIN IMMEDIATE")
        import_snapshot(db, snapshot)
    return snapshot


def import_public_journals(db, records):
    """Import reviewed GitHub citation records into the public search index."""
    if not isinstance(records, list):
        raise ValueError("journal_manifest_must_be_a_list")
    fields = {"title", "url", "doi", "authors", "publisher", "publication_date", "access"}
    seen = set()
    for record in records:
        if not isinstance(record, dict) or set(record) != fields:
            raise ValueError("invalid_journal_fields")
        title, url, doi, authors, publisher, date, access = (
            record[key] for key in ("title", "url", "doi", "authors", "publisher", "publication_date", "access")
        )
        if not isinstance(title, str) or not title.strip() or not isinstance(url, str):
            raise ValueError("invalid_journal_title_or_url")
        link = urlsplit(url)
        if (link.scheme != "https" or not link.hostname or link.username or link.password
            or link.query or link.fragment or any(char.isspace() for char in url)):
            raise ValueError("invalid_public_reading_url")
        if doi is not None and (not isinstance(doi, str) or not re.fullmatch(r"10\.\d{4,9}/\S+", doi)):
            raise ValueError("invalid_journal_doi")
        if (not isinstance(authors, list) or any(not isinstance(author, str) for author in authors)
            or not isinstance(publisher, str) or access not in ("open_access", "subscription", "unknown")):
            raise ValueError("invalid_journal_citation")
        if date is not None:
            if not isinstance(date, str) or not re.fullmatch(r"\d{4}(?:-\d{2}(?:-\d{2})?)?", date):
                raise ValueError("invalid_journal_publication_date")
            datetime_date.fromisoformat(date + {4: "-01-01", 7: "-01", 10: ""}[len(date)])
        identity = doi.lower() if doi else url
        if identity in seen:
            raise ValueError("duplicate_journal_identity")
        seen.add(identity)
        source_id = "JOURNAL-" + hashlib.sha256(identity.encode()).hexdigest()[:32]
        citation = dict(record, doi=doi.lower() if doi else None, source_url=url, source_id=source_id)
        desc = " · ".join(filter(None, [", ".join(authors), publisher, doi, access.replace("_", " ")]))
        values = (title, desc, date, url)
        row = db.execute("SELECT source_row FROM public_provenance WHERE source_id=?", (source_id,)).fetchone()
        if row:
            row_id = row[0]
            db.execute("UPDATE sources SET title=?,description=?,publication_date=?,url=? WHERE id=?",
                       (*values, row_id))
        else:
            row_id = db.execute("""INSERT INTO sources(title,description,publication_date,url,
                source_type,pgdt_lens,review_status,visibility)
                VALUES(?,?,?,?,'Journal article','','approved','public')""", values).lastrowid
        db.execute("""INSERT INTO public_provenance VALUES(?,?,'journal-articles','REVIEWED',?)
            ON CONFLICT(source_row) DO UPDATE SET citation_json=excluded.citation_json""",
                   (row_id, source_id, ingest.encode(citation)))

def import_reviewed_manifest(path):
    records = json.loads(Path(path).read_text(encoding="utf-8"))
    server.initialize()
    with closing(server.connect()) as db, db:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("BEGIN IMMEDIATE")
        import_public_journals(db, records)
    return len(records)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-db")
    parser.add_argument("--reviewed-journal-manifest", metavar="PATH")
    parser.add_argument("source_id", nargs="?")
    parser.add_argument("--approve-synthetic", action="store_true")
    args = parser.parse_args()
    if args.reviewed_journal_manifest:
        if args.private_db or args.source_id or args.approve_synthetic:
            parser.error("supply only the reviewed journal manifest")
        print(ingest.encode({"journal_articles_imported": import_reviewed_manifest(args.reviewed_journal_manifest)}))
        return
    if not (args.private_db and args.source_id and args.approve_synthetic):
        parser.error("synthetic projection requires --private-db, source ID and --approve-synthetic")
    ingest.initialize(args.private_db)
    server.initialize()
    print(ingest.encode(project_demo(args.private_db, args.source_id)))

if __name__ == "__main__":
    main()
