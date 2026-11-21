# CRSIS-47 TIMEPIECE lab catalog

Division 03 on the English homepage and Research & Laboratories page is generated from `labs/catalog.json`. The order of entries sets the display order.

- Add a unique lowercase hyphenated `slug`, a learner-facing `title`, a short `description`, and `status: "draft"` while preparing an exercise. Drafts are omitted from Pages output.
- For a static lab, place its standalone page at `labs/<slug>/index.html` and provide a return link to `/crsis47-public-site/research/#division-detail-03`. The installer publishes the entry page. Keep styles and scripts inline or use assets already served by the site.
- For a separately hosted lab, set `hosted_url` to its approved HTTPS launch address. Pages generates the link. The application runs on its own host.
- Set the entry status to `published` when it is approved for public release. The existing Pages workflow checks generated local links and release manifests before deployment.

Keep private lab source, credentials, and unreleased evidence outside this public repository. Draft status controls Pages output, while checked-in files are visible in GitHub.
