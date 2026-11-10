# CRSIS-47 Evidence Chamber — Phase 1 website integration

**Owner approval:** 2026-11-10. Scope: homepage hero, navigation header, footer. Preserve existing content, Case Study 001–006 progression, and all purchase links.

## Status
**Integration snippets staged for review; NOT deployed.** Repository page layout could not be inspected through available file search. The approved PNG has not been uploaded to this public repository, so these snippets are NOT ready to activate.

## Approved image prerequisite
Source file: `CRSIS47_Evidence_Chamber_Royal_Blue_Gold_Approved_Visual_2026-11-10.png`
Source SHA-256: `178737391e814ee911de2082573c8d6986f3dada748ef2f2c2050017988b8ee0`
Source dimensions: 1312 × 1199. Approved image is preserved in ChatGPT Library. Do not substitute a generated lookalike.

Place an approved web-optimized copy at `/assets/brand/crsis47-evidence-chamber-approved.png`. Ensure the exact image and its accessible alternatives are reviewed.

## Implementation
1. Identify actual site homepage/header/footer templates and build process.
2. Add CSS from `evidence-chamber.css` to existing stylesheet without resets.
3. Integrate the three semantic fragments in `placements.html` into the existing templates. Do not paste the entire fragments file as a page.
4. Confirm header and footer do not duplicate a pre-existing brand lockup.
5. Test mobile/desktop, screen-reader semantics, image load, page weight and layout shifts.
6. Regression-test all existing Case Study 001–006 links and Payhip checkout destinations.
7. Review preview before merge or deployment.

## Design boundary
No redesign. Royal blue and brilliant gold, the shield, chamber, CRSIS-47 wordmark and supporting title remain frozen. This change is branding placement only.
