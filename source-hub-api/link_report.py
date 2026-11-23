"""Record an authorized link checker observation without fetching URLs here."""
import argparse
from contextlib import closing
import json

import ingest
import server

def report(source_id, observed_status):
    if type(observed_status) is not int or not 100 <= observed_status <= 599:
        raise ValueError("invalid_http_status")
    with closing(server.connect()) as db, db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("""SELECT p.source_row,p.citation_json,s.url FROM public_provenance p
                            JOIN sources s ON s.id=p.source_row
                            WHERE p.source_id=? AND s.visibility='public' AND s.review_status='approved'""",
                         (source_id,)).fetchone()
        if not row:
            raise ValueError("approved_source_not_found")
        observation = {"url": row["url"], "status": observed_status, "reported_at": ingest.now(),
                       "state": "BROKEN" if observed_status in (404,410) else "OBSERVED"}
        citation = json.loads(row["citation_json"])
        citation["link_report"] = observation
        db.execute("UPDATE public_provenance SET citation_json=? WHERE source_row=?",
                   (ingest.encode(citation), row["source_row"]))
        db.execute("UPDATE revision SET version=version+1 WHERE id=1")
        return observation

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source_id")
    parser.add_argument("reported_http_status", type=int)
    args = parser.parse_args()
    print(ingest.encode(report(args.source_id, args.reported_http_status)))
