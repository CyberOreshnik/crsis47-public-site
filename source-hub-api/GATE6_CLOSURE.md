# Gate 6 closure

Run in the root of a disposable checkout with no existing `site` directory, only after the security reviewer authorizes external network isolation. The command records the operator's attestation that isolation is active. It does not configure or verify network isolation itself.

```powershell
python source-hub-api/gate6_close.py --prior-evidence $priorJson --test-registry $testDb --legacy-backup $backupDb --legacy-restore $restoreDb --legacy-evidence $legacySnapshotJson --private-markers $markersJson --isolation-reference $approval
```

Keep inputs outside the checkout. The prior JSON must include the accepted test booleans named in `FLAGS`, `old_token_http: 401`, and the protected test registry inspection under `verified`. The legacy evidence JSON must come from a verified consistent snapshot of the original registry and match the summary format emitted by `private_store.py verify`. Use protected, separate backup and restore directories. The command checks recovery evidence and never opens the original installation.

Supply a private JSON array of known confidential strings to scan, including receipts, source identifiers and sensitive paths for the local verification. The scan emits counts and statuses, and the build emits only step information on failure. The frozen build and approved content guards also run. Marker matching is limited to known values and supported signatures and archive formats. Keep local output private.

`--ci-scan` scans an already generated CI site and returns supporting evidence only. A nonzero exit indicates a failed or incomplete mandatory check.
