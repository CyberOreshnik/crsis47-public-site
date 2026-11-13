# Adding books and case studies

Every public catalog/detail page uses generate_uniform_site.py, uniform/site.css and uniform/site.js. Do not edit generated site/ files. Approved artwork stays checksum-gated.

1. Add an item to the appropriate array in uniform/catalog.json.
2. Supply a unique ID and slug, approved title and description, approved cover path, and honest release status.
3. For books, provide the approved English synopsis in copy.en.paragraphs, plus title, hook and facts. Localized copy is stored with that book under copy.<locale>.
4. For paid case studies, set purchase_url and price_usd only when the product is approved and available. Detail pages show public summaries and Payhip links, never private download files.
5. Free reading editions can supply approved HTML under article.en and matching locale keys.
6. Add approved cover artwork to the preserved asset source and update its source manifest when applicable.
7. Run python generate_uniform_site.py --collect. New interface strings require entries in uniform/translations/<locale>.json; missing interface translations block the build.
8. Run the full build, qa/verify_uniform_site.py and qa/regress_site.py. Review desktop, mobile and right-to-left layouts.

Homepage shelves, catalog counts, detail routes and language links are generated from the catalog. Adding the sixth book or seventh case does not require changing templates. English-only synopsis copy is a source-language fallback, not a claim that it is translated.

## Translation provenance

New interface, homepage and glossary strings were machine-assisted on 13 November 2026 using Google's public translation interface, then stored as static files. Builds call no translation service. Project names, classification labels and locked measurement/framework names were protected. Existing translated book synopses and Case Study 001 text were preserved from the approved release.

These are not certified or independently reviewed translations. English governs technical terminology. Product-file language and availability are separate; website translation does not translate paid downloads.

## Remaining operational follow-up

Payhip storefront shield and navy/gold purchase-button branding require authenticated editor access. Future content still requires normal editorial, source, translation, accessibility and product-release review.
