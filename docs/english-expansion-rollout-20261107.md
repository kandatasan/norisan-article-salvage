# つりくえ！ English rollout – 2026-11-07 verified handoff

## Purpose
Create English-language counterparts to Japanese sightseeing posts, with first-person photos, natural English, and user-choice language navigation. Maintain Japanese post URLs and content. Pilot: Orizuru Tower.

## Verified current state (read-only audits)
- Original Japanese WP post: ID **2647**, slug **orizuru-tower**, status `publish`, URL `https://tsurikue.com/orizuru-tower/`.
- English WP post: ID **4375**, slug **orizuru-tower-english**, status `draft`; actual post body confirmed through authenticated GET.
- English post contains 18 confirmed WP images and an English-only Hiroshima local welcome/peace perspective, plus one contextual DiscoverCars affiliate link with explicit disclosure and a link to Japan driving-licence guidance.
- WP permalink format: `/%postname%/`.
- No page or category with slug `en` existed at the time of audit.
- WP settings and plugin-list REST endpoints return **403** for the configured WordPress account.
- Xserver pinned-host-key SSH audit succeeded, WordPress and wp-cli are present. No known multilingual plugin directories (Polylang, WPML, TranslatePress, Weglot) were found; site does have sitemap-related plugin directories. This does not prove all plugins or settings.
- Current WordPress sitewide settings, plugin installation, /en routing and hreflang are **NOT** implemented by this file. Don't claim otherwise.

Audits:
- https://github.com/kandatasan/norisan-article-salvage/pull/825
- https://github.com/kandatasan/norisan-article-salvage/pull/827
- English transport PR: https://github.com/kandatasan/norisan-article-salvage/pull/826

## Safe target structure
Preferred after isolated test:
- Japanese: `https://tsurikue.com/orizuru-tower/` (unchanged)
- English: `https://tsurikue.com/en/orizuru-tower/`
- English landing page: `https://tsurikue.com/en/`

Use either a properly tested language-routing plugin or a tested hierarchical WP page solution. Do **not** assume that changing the post slug creates nested `/en/` routing. Do not change sitewide permalink structure or install/activate an untested translation plugin on live production.

### Required before public English release
1. Confirm site backup and rollback for PHP, database, permalink and WP content changes; isolate preview and test first.
2. Implement English /en path without changes to existing Japanese URLs. If retyping post 4375 as a hierarchical WP page, first verify edit/update compatibility and rollback. Keep no two public duplicates.
3. Add manual language switch: English → Japanese and Japanese → English. This is navigation, **not** duplication of the author's English-only reflection in the Japanese article.
4. Add bidirectional self-inclusive `hreflang` with `en` and `ja` through HTML head or sitemap; each language canonical must point to its own indexable final URL.
5. English posts and English landing UI should have appropriate page-language and navigation labels, and no forced locale/IP redirects.
6. Verify indexing controls, XML sitemap inclusion, robots, HTTP 200, canonical, mobile display, images, and no accidental Japanese site changes.
7. Confirm final prices/access against official sources when publishing; link to official park/tower information.
8. Only publish English after verifying the above; keep existing article 4375 in `draft` until then. GSC coverage and international search performance follow publication.

Google's guidance:
- https://developers.google.com/search/docs/specialty/international/managing-multi-regional-sites
- https://developers.google.com/search/docs/specialty/international/localized-versions

## Editorial and monetization (verified)
- City-centre visitors: recommend walking/trams to Orizuru Tower and Atomic Bomb Dome; tower has no dedicated parking: https://www.orizurutower.jp/en/access/
- Renting a car is optional for longer Hiroshima Prefecture / Chugoku countryside touring. Never claim rental needed for the tower.
- One DiscoverCars partner link: `https://www.discovercars.com/?a_aid=tsurikue`. Keep transparent affiliate disclosure and `rel="sponsored nofollow"` for paid outbound links.
- Drive legally: official NPA visitor guidance https://www.npa.go.jp/english/bureau/traffic/r8_english.pdf.pdf
- English-only local note is the owner's personal perspective; do not insert it in Japanese article. Preserve his appreciation for people who rebuilt the city and his invitation for overseas guests to enjoy today's Hiroshima.

## Production workflow
Use `main` inspection → feature branch → PR → diff/test → merge → Actions → real WordPress validation → publish verification; no claim of completed multilingual setup before live URL/head checks. Prefer a reversible implementation over broad WordPress/sitewide plugin changes.
