# CRSIS-47 scalable collection architecture — ADR 001

Status: proposed for implementation and validation. Owner policy: FREE-FIRST, zero unapproved charges. Website identity frozen.

## Scope
Books, case studies, TIMEPIECE labs, Source Hub, glossary, research programs, investigations, languages, and future collections must scale independently. Source Hub is the first implementation slice, **not** a one-off design.

## Separation
- **Presentation:** existing GitHub Pages website, unchanged approved visual assets and URLs.
- **Catalog metadata:** small public collections may be prebuilt static JSON shards with a fixed page size; do not embed entire growing collections into HTML.
- **Large search collections:** hosted read-only API backed by indexed database; API credentials and private records never shipped to GitHub Pages.
- **Restricted evidence:** private storage and authentication boundary separate from public search index. Public API enforces publication state in SQL.
- **Interactive labs:** manifest-only catalog; fetch lab-specific evidence and exercises only after launch. Private participant sessions require separately approved authenticated storage.

## Common content contract
Every record has immutable ID, collection, title, slug, language, publication status, version, updated timestamp, and provenance where relevant. Collection-specific schemas extend this common envelope. Avoid assuming 500,000 lab exercises or books need identical search infrastructure.

## Common browsing contract
Default page size 25, hard maximum 25. Filters and query state in URL, stable deterministic ordering with unique-ID tie-break, accessible loading/error/empty states, Back/Forward support. Each tab loads only its own current page. Cursors must bind to filter set and document consistency guarantees.

## Performance and safety gates
- Synthetic 500,000-record database test: deterministic seeding, indexes, no restricted leakage, full traversal duplicate/skip assertions, representative query timings and payload sizes.
- Add browser tests proving navigation to Books never fetches Source Hub or TIMEPIECE datasets.
- Production performance claims require testing actual free-tier hosting under realistic load, not only SQLite localhost.
- Record index query plans, memory, p50/p95/p99, concurrent writes, and browser network transfer.
- Keep live Source Hub functioning until deployed API passes validation; no silent broken switch.

## Migration sequence
1. Validate and harden Source Hub API and local load tests.
2. Build configurable Source Hub client behind a safe fallback and test URL state.
3. Evaluate eligible free hosting and quotas; require owner approval before any provisioning.
4. Generalize collection manifest, paging and navigation without redesigning frozen website.
5. Restore original approved TIMEPIECE lab from verified source asset; do not use simplified demo as approved final.
6. Migrate other catalogs incrementally with regression checks.

## Cost gate
No billing setup, paid dependency, subscription, or recurring charges without explicit owner authorization. Measure free-tier limits and document exit/migration strategy.

## Current limitations
The initial Python API and load test are unverified prototypes. No hosted endpoint has been approved. Do not describe this ADR as proof of 500k performance or complete website scalability.
