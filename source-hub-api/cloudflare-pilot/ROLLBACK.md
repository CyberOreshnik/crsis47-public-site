# G06 recovery and rollback
Development only. No production deployment authorized.

Baseline: GitHub Pages main remains independent; Source Hub API meta remains empty. Worker endpoint and preview URLs disabled by default. No private database bindings or storage provisioned.

Triggers: outage, quota exhaustion, invalid configuration, unauthorized revision, suspected compromise. Isolate only pilot routes and endpoint; revoke pilot credentials if compromised; restore approved empty API meta from verified baseline (do not revert unrelated website changes). Verify static pages, navigation, shield and source venue preview. Record incident and exact commit. Preserve private registry untouched. Restart only after owner approval, free-plan verification, fresh credentials if needed, approved manifest revision and passing regression tests. No automatic restart.

Tests: simulated network failure, HTTP 429/403/503/500, stale cursor 409, advanced filters fail closed, successful recovery. Simulation does not establish live provider behavior or full-browser acceptance. Production drill remains pending.
