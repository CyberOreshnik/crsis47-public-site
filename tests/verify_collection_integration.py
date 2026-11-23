"""Whole-site integration contract checks; no third-party packages or hosting."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/"source-hub/index.html").read_text()
api=(ROOT/"source-hub-api/server.py").read_text()
adr=(ROOT/"docs/architecture/ADR-001-scalable-collections.md").read_text()
checks={
 "Source Hub API configuration is explicit": 'name="source-hub-api"' in source,
 "Source Hub uses one-page API requests": 'endpoint.searchParams.set("limit", "25")' in source,
 "Source Hub supports URL-backed filters": 'new URLSearchParams(location.search)' in source,
 "Source Hub supports browser history": 'history.pushState' in source and 'popstate' in source,
 "Source Hub cancels obsolete requests": 'AbortController' in source and 'request?.abort()' in source,
 "Source Hub limits API response size": 'limit>25' in api,
 "Source Hub enforces public approved records": '"visibility=\'public\'","review_status=\'approved\'"' in api,
 "Whole-site architecture includes all collections": all(s in adr for s in ["Books","case studies","TIMEPIECE","Source Hub","glossary","research"]),
 "No hosted API endpoint silently enabled": 'name="source-hub-api" content=""' in source,
}
for label,ok in checks.items():
 print(("PASS" if ok else "FAIL"),label)
assert all(checks.values()),"Integration contract checks failed"
print("PASS: static integration contracts. Browser network isolation and hosted API are NOT verified.")
