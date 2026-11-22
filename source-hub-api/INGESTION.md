# Source Hub ingestion on the development branch

This is a no-cost development implementation. Intake defaults to synthetic fixtures; Gate 2 and Gate 3 permit explicitly enabled public sources for their controlled research commands. Use Python with SQLite FTS5 trigram support. GitHub Pages remains the static public frontend. The existing page retains its small journal fallback by default. The intake server and its database never serve the public query endpoint. No hosted service is configured.

## Local demonstration

1. Set SOURCE_HUB_DB to an absolute path for a disposable public SQLite database outside the checkout. Set SOURCE_HUB_INTAKE_TOKEN to a locally generated random value of at least 32 characters. Keep the token out of source files, fixture payloads and shell history.
2. Open a terminal and run python source-hub-api/ingest.py --private-db PATH serve with a different absolute private database path outside the checkout. It binds to loopback port 8766 and starts a queue worker.
3. Send POST http://127.0.0.1:8766/api/source-events with the contents of synthetic-event.json, Content-Type application/json, Authorization Bearer TOKEN and Idempotency-Key demo-01. Poll GET /api/source-events/RECEIPT with the same authorization until filed. Use the returned source_id for the next step.
4. For a local preview, explicitly approve the synthetic snapshot with python source-hub-api/project.py --private-db PATH SOURCE_ID --approve-synthetic. This exports citation JSON and populates a separate public database. No worker path publishes automatically.
5. Serve the public database with python source-hub-api/server.py. Verify GET http://127.0.0.1:8765/api/sources?project=CASE-001. For browser verification, copy the Source Hub page to a temporary static directory, set its API meta value to http://127.0.0.1:8765/, and serve that copy on port 8000 using python -m http.server 8000 --bind 127.0.0.1. Set SOURCE_HUB_ALLOWED_ORIGIN=http://127.0.0.1:8000 for the API. The tracked page retains its empty API config.

## Contract and operation

SOURCE_USED v1 accepts one event per JSON request. An integration submits only after it selects a source for authorized use. Treat Idempotency-Key as a stable event ID across retries. A replay of the same normalized event returns the same receipt; different content with the same key receives 409. Retry transient transport errors and HTTP 503 with bounded backoff. Do not retry validation or authentication failures without fixing the request. Poll until filed or failed. The terminal review CLI is python source-hub-api/ingest.py --private-db PATH failures. Logs contain receipt IDs, attempts and error codes, not payloads. Resubmit corrected input with a new event key and record the old receipt in the workflow's review record.

A transaction claims, files and marks an event complete. A savepoint reverts partial writes. Failed processing retries after 2 and 4 seconds, then moves to failed. Conflicting DOI/URL mappings fail closed. Other metadata disagreements retain the first populated value and record a conflict with the original incoming event retained. URL and DOI aliases deduplicate metadata. Content hashes apply only when an authorized byte-preservation worker exists. Preservation requests record blocked status in the audit, without network retrieval. Capture starts at CAPTURED. Metadata verification and evidence review require separate decisions; no ingestion code advances those states. Null means unavailable. Public approval is separate and limited to a manually selected synthetic projection. Later private intake has no effect on an already approved snapshot until reprojected or withdrawn.

Search retains the existing 25-result keyset and stale-cursor behavior. The public-only SQLite projection adds citation export fields and project, collection and verification filters. Its searchable description indexes author names, DOI and persistent ID. Search by project with the dedicated filter. Use the original stable ID for joins. The local JSON projection round-trips through the trusted offline importer. That importer is an internal interface for explicitly approved synthetic snapshots, not an HTTP endpoint or an untrusted file importer. The public API returns no claim IDs, originating workflows, private audit events or receipt data. A snapshot is bounded to 64 project relationships; the private relationship set can grow beyond it. The local operator can report observed public-link HTTP status via python source-hub-api/link_report.py SOURCE_ID STATUS. A 404 or 410 is marked BROKEN and is returned in citation metadata. There is no automatic network probing.

## Record-family adapter contract

| Family | Adapter mapping | Status |
|---|---|---|
| Citation register and scholarly sources | claim_ids carries C-identifiers; DOI and publication metadata stay nullable | Scholarly synthetic flow tested; protected citation-register events denied |
| PGDT | external_ids carries scenario identifiers; pgdt_lens carries People, Governance, Data or Technology | Synthetic contract; real register not connected |
| Engineering | external_ids carries stable version/manifest references; checksum belongs in separately approved byte-preservation records | Restricted route disabled |
| Validator | external_ids preserves S001–S100 values without transformation | Restricted route disabled |
| Governance | external_ids preserves G-01–G-18; approvals remain outside intake-controlled decisions | Restricted route disabled |
| Case studies, books, laboratories, historical evidence | project_ids and evidence_type map to stable collections without a fixed count | Synthetic contract only |

This mapping follows v0.1's evidence and claim separation. No controlled archive or research records were imported. The v0.2 mapping preserves the existing claim row ID and distinguishes support status from proposal status. The v0.3 crosswalk treats namespaces as adapter keys and leaves original source identifiers untouched. In v0.4, preprinted validator IDs remain template rows, engineering reports are distinct from executed archive manifests, and governance decisions require authoritative sign-off. The adapter keeps these fields out of automatic verification and never interprets external IDs as completed decisions. The internal packages were consulted as design references only.

| Integration | Actual connection |
|---|---|
| Loopback HTTP client and SQLite | Implemented for synthetic inputs |
| Controlled Codex task | Automatic filing within the named Gate 2 command only; no global capture hook |
| Zotero and GitHub research workflows | No automatic transmission connected |
| Public Pages and hosted read service | Static fallback only; hosted service unset |
| Original-byte storage and content hashes | No byte worker or licensed storage. Link reporting accepts external observations; automated checking remains disconnected |

## Migration, rollback and boundary

The development projection adds tables to existing public search storage. Existing search rows retain their original keys and ordering. Before migrating, stop writers and create consistent SQLite backups using the online backup API or a quiesced checkpointed copy. Keep the private database, WAL and backups outside the checkout and web root. Keep the old server/frontend together when rolling back. Restore both databases from a paired backup if reversing a data migration, then rotate cursor configuration. To withdraw a projected source, delete its public sources row in a transaction with foreign_keys=ON. This removes its projection and search entries. Keep the private registry and audit. Files in the public build are assembled through the existing allowlisted site build, with CI checking for ingestion files, databases and fixture markers.

Before real data intake, require a private host and verified storage boundary, scoped identities and credential rotation, retention/withdrawal controls, rights review, and authorized adapters. A local bearer credential and separate SQLite files demonstrate API behavior; they are not production access isolation. Do not expose these stdlib loopback servers over a network. No public release, protected-data ingestion or doctoral experimental execution is authorized.

## Validation

Run python source-hub-api/test_ingest.py and node source-hub-api/navigation_test.js. The synthetic scale test measures local SQLite search and pagination, plus seeding time. It is not a hosted latency or concurrency result. CI runs the real loopback HTTP test, existing public search test and website build guards. A local sandbox that explicitly blocks sockets can set SOURCE_HUB_SKIP_SOCKET_TEST=1 for local-only checks. Keep it unset in CI.

## Gate 2 controlled Codex research task

After the normal website build, run `python3 source-hub-api/codex_research.py`. This one command answers a narrow documentation question from IANA's live Example Domains page, files the selected source automatically, polls the authenticated loopback intake, and verifies the actual private SQLite record and public isolation. It retries the exact event once and submits another use to demonstrate both event replay and source deduplication. A failed run exits nonzero. The run emits receipt evidence and destroys its disposable test databases after verification. The response digest fingerprints content read for the task; original bytes are not preserved.

Gate 2 admission is disabled by default. The controlled runner enables an exact IANA URL, workflow and project combination in its own process. Real sources cannot be projected through the synthetic public approval path. No global Codex, ordinary ChatGPT, Zotero or unrelated workflow hook exists.

## Gate 3 — controlled real-source policy

Gate 2 accepted baseline: `b969dd30020c9100389cf8f299936bfdb169dd4b`. [Accepted CI](https://github.com/CyberOreshnik/crsis47-public-site/actions/runs/45061795701) and [sanitized receipt](https://github.com/CyberOreshnik/crsis47-public-site/actions/runs/45061795701/artifacts/14769637576). Source `SRC-2f79cfefbf304f4680efa59fb96285bc`, initial/replay receipt `5b1d448cff464ff58a9fc57b29552586`. Gate 2's command and checks remain in CI.

`approved_sources.json` is a reviewed development policy register. It starts with IANA's Example Domains and RFC Editor's RFC 2606 and 6761. Each entry approves one canonical HTTPS URL, source identity, source-use statement, citation and project/claim mapping. A host or DOI prefix does not grant permission. Additions require an explicitly authorized register edit and evidence locators. This policy can represent public reports, scholarly DOI or canonical URL records, technical guidance, primary incident material, and case study, book and PGDT source relationships, subject to per-document review and accessible HTML identity evidence. It does not enable unrestricted URL entry, automated discovery, restricted records, PDF retrieval or original-byte preservation.

Run `python3 source-hub-api/codex_research_gate3.py` from the checkout after its normal website build. One command retrieves and uses the three documents to answer the documented question and automatically files each source. It verifies the database rows, two project relationships per source, and exact replay through authenticated intake. It tests HTTP rejection of an unlisted document on an approved host, restricted classification, and mismatched DOI. A separate disposable public database and a generated-site check establish the test boundary. Any validation or filing failure exits nonzero. Temporary databases live outside the checkout and are removed at the end. Only the sanitized receipt and evidence metadata persist in CI. The hash fingerprints the HTTP response read in the demonstration and is not a custody assertion.

One private registry holds all evidence. Logical collections group the existing evidence types; a second project uses the same source ID and adds a project/claim edge, regardless of its collection. Unknown publication dates stay null; a known year-month uses YYYY-MM without fabricating a day. Gate 3 uses its own explicit process-local opt-in and validates metadata and provenance fields both at the client and intake. Registry publication stays UNAPPROVED; real entries are ineligible for the synthetic public projector. Ordinary ChatGPT, Zotero, browsers and other Codex workflows remain disconnected.
