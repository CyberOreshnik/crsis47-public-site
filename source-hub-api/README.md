# CRSIS-47 collection scalability decision

Keep the frozen static site, existing public routes and shared design. Each collection owns its records and detail pages. Add optional read adapters behind the same URL-based navigation as collections outgrow static data. No hosted services are provisioned.

| Collection | Current slice and next migration | Acceptance at migration |
| --- | --- | --- |
| Source Hub and investigative evidence | SQLite adapter behind the existing page. Adopt stable IDs, source URLs, type, date, PGDT and publication gate. Extend metadata with versioned provenance before importing research. | 25 records per response, no omitted or repeated IDs within a revision, no unpublished rows. |
| Books and Case Studies | Retain the existing generated catalogs, covers and URLs. Move growing lists into separate paged collection endpoints. | Cap records and cover requests per page. Detail links and purchases remain valid. |
| TIMEPIECE | Keep the lab registry and load a selected lab at launch. Keep private sessions outside public catalog storage. | Directory requests contain metadata only. Validate the approved app and hosting separately. |
| Glossary and Theoretical Foundations | Preserve term anchors and multilingual pages. Split growth into language-scoped search and records. | Test stable anchors, accessible navigation and locale-specific payloads. |
| Research & Laboratories and institutional collections | Keep the divisions as entry points. Collections and datasets receive independent versioned indexes and evidence classifications. | Entry pages load no other collections' datasets. Verify provenance and publication approval before indexing. |

Use stable IDs and public URLs throughout. Prefer independent build inputs, URL-addressable filters, accessible result navigation and portable metadata. Scale test each collection separately before increasing its publication volume. The first gate is 500,000 synthetic Source Hub records.

## Local setup

Use Python 3 with SQLite FTS5 trigram support. Run `python3 source-hub-api/load_test.py` for the deterministic temporary database test and `node source-hub-api/navigation_test.js` for a mocked browser-navigation check. Run `SOURCE_HUB_DB=/path/to/public.sqlite python3 source-hub-api/server.py` for the loopback API. Import only cleared records into a separate serving database using transactional INSERT, UPDATE and DELETE. Avoid SQLite REPLACE because delete-trigger behavior depends on connection settings. Existing databases are indexed on initialization. Use the browser configuration meta tag in Source Hub with an API base URL ending in a slash. Leave it empty to keep the existing journal discovery view.

## Publication and pagination

The API returns only records marked both public and approved. Production ingestion must separately validate provenance, citations, identifiers and safe links. The shared response shape is `{items,nextCursor}`, capped at 25 with bounded display fields. Filters are bound parameters and text search takes a literal substring of at least three characters. Ascending unique IDs give deterministic ordering. Each request reads one SQLite snapshot. Signed cursors bind the last ID, filters, database epoch and revision. Any committed insert, update or delete invalidates outstanding cursors, including edits to private rows. Clients receive HTTP 409 and restart. The server retains no older snapshot across requests. Rotate cursor secrets when restoring a backup. Use a shared configured secret across workers if later hosted.

## Hosting gate

This release uses local tools and the existing GitHub workflow. No new service or spending is authorized. The stdlib HTTP server binds to loopback for testing. Before selecting an external host, verify its recurring free allowance, persistent disk and backup terms, cold starts, request and transfer quotas, overage policy, and available usage alerts. Test TLS, timeouts, rate limits, monitoring and availability on the chosen deployment. Set `SOURCE_HUB_ALLOWED_ORIGIN` to an exact website origin if required. CORS controls browser access and the database publication gate limits the records served. Hosting choice and production capacity remain unverified.
