"""Explicit local synthetic projection. No intake event can invoke publication."""
import argparse
from contextlib import closing
import json
from pathlib import Path

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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-db", required=True)
    parser.add_argument("source_id")
    parser.add_argument("--approve-synthetic", required=True, action="store_true")
    args = parser.parse_args()
    ingest.initialize(args.private_db)
    server.initialize()
    print(ingest.encode(project_demo(args.private_db, args.source_id)))

if __name__ == "__main__":
    main()
