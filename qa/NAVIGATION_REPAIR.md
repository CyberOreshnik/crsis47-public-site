# Navigation repair — QA only

Controlled source: CyberOreshnik/crsis47-author-website at d2788ea5a9783766edfb6862a3046ebb3ff11b97, review/binance-multilingual/pages/case-studies/index.html.

Use its two target additions: <span id="case-studies"></span> immediately before section#index-view, and <span id="binance"></span> immediately before section#article-view. The existing hash router remains unchanged. Apply the same targets to both English reading/download files. No multilingual article replacement or publication is included.

Baseline: 188 HTML files; 8,911 local asset references; 9,390 links; exactly eight missing-fragment issues. After repair: same counts, zero issues. Regression also checks cross-document HTML fragments and duplicate IDs. External URLs, translation accuracy, screen-reader behavior and editorial approval are not certified by this test.

The 46 release chunks and prepare_public_site.py remain unchanged. Original archive SHA-256: de3c2d2a293c5298c3593b8c958e0ccd3c72825493f1fcfab9950abd804a6c30.

Reproduce:
1. python3 prepare_public_site.py
2. python3 qa/repair_navigation.py
3. python3 qa/regress_site.py

On Windows, pass -X utf8 to Python. Input checksums prevent silently patching another release. Original deployment-manifest.json describes the unpatched reconstruction; qa-site-manifest.json describes the repaired QA tree.

Only the draft PR QA workflow runs the overlay. The deployment workflow and main are unchanged. Publication remains NO-GO pending remaining review gates.
