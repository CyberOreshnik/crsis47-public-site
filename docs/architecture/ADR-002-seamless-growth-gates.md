# ADR-002 — Seamless Growth and Operational Readiness Contract

**Status:** Required engineering acceptance gates; not a claim of completed implementation.  
**Scope:** Every current and future CRSIS-47 collection, lab, language, page, and publication.  
**Policy:** FREE-FIRST; preserve frozen design, assets, URLs, public/private research boundaries.

## Growth contract
1. **Additive content registration.** New books, case studies, labs, research programs, evidence sources and translations enter through validated manifests or collection schemas. No edits to shared navigation HTML for every new item. Stable immutable IDs, slugs and redirects for renamed items.
2. **Independent loading.** A page requests only the active collection's current page; no full-dataset HTML, eager cross-collection downloads or uncontrolled client-side filtering. Lab catalog metadata is separate from full lab bundles.
3. **Capacity thresholds.** Test 500k records now, then 1M, 5M and realistic mixed-query workloads before committing to corresponding scale claims. Monitor storage, index growth, CPU/memory, p95/p99, and concurrent-user behavior.
4. **Performance budgets.** Record baseline HTML/JS/CSS/image transfer, total requests, largest response and render timings for each route at desktop and mobile viewport. Set thresholds based on measured approved site; fail CI on regressions beyond documented allowance.
5. **Schema and API compatibility.** Version public APIs and content schema; additive changes first. Use migration scripts with reversible rollback and sample import/export tests. Retain existing links, bookmarkable filters and browser history.
6. **Publication safety.** Deny by default: only explicitly approved public records enter public indexes and static artifacts. Run negative tests against draft, restricted, embargoed and withdrawn content. No secret tokens in GitHub Pages.
7. **Accessibility and localization.** Keyboard navigation, semantic labels, contrast, screen reader announcements, RTL layout where relevant, language fallbacks, localized metadata, and automated/manual acceptance for newly added modules.
8. **Resilience.** API timeouts, controlled retries/backoff, meaningful offline/unavailable states, safe cached public catalog fallback when permitted, health checks, backups with restore drills, and documented recovery point/time objectives before hosting approval.
9. **Security.** Strict origin policy, rate limiting at host/proxy where feasible, input bounds, output encoding, dependency audits, secure secret rotation, least privilege, privacy-conscious logs, and explicit incident response owner.
10. **Observability.** Monitor API errors, latency, search zero-result rates, broken links, build/deploy failures, content freshness, storage, quotas and cost. Alert only on actionable thresholds; do not assume paid monitoring.
11. **Change control.** Pull request, automated checks, owner approval, reversible deployment, smoke test, and post-release verification. Keep frozen visual assets under checksum enforcement.
12. **Cost.** Verify free-tier quotas and account limits, disable automatic paid upgrades, document migration/exit plan. No provisioning or billing changes without owner approval.

## Definition of done for a new collection
- Manifest/schema validated and documented; sample item added without editing shared page templates.
- Stable URL and redirect policy verified.
- Browser network capture shows only requested data loaded, including after search, pagination, Back/Forward and lab launch.
- Private/draft record never appears in public HTML, JSON, API, sitemap, or search.
- Accessibility and localization smoke tests pass.
- Performance budgets measured, not merely asserted.
- Backup and rollback documented for affected storage.
- Existing approved branding, cover assets, footer, and all routes unchanged.
- CI checks and owner acceptance complete.

## Known gaps as of 2026-11-21
The 500k local SQLite benchmark and six-route Chromium request-isolation test passed. They do **not** demonstrate production hosting scalability, every collection's modular schema, API resilience, recovery drills, multilingual correctness, or zero-downtime deployments. Those remain gates before production merge.
