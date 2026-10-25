
# Kanagawa prefectural eDNA river candidates (research only)

This workflow reads the public Excel source files linked from Kanagawa Prefecture's environmental DNA page. The page lists fish eDNA results for FY2021–FY2025, including surveys of the prefecture's water-source rivers and a prefecture-wide citizen-science project.

The extractor matches source fish labels in memory against the repository's official taxon reference and aggregates positive results only when the source provides explicit water-system and river fields. The Actions log prints national coverage and aggregate match counts. Its downloadable research artifact lists candidate river groups, source IDs, survey years, and counts; it omits fish names, sampling-site names, coordinates, and river codes. No source row is saved.

Every group remains `research_only_unapproved`. Exact water-system and river matches are checked against the public atlas, but the atlas does not carry reliable prefecture fields for every group; even exact pair matches need a prefecture cross-check. Unmatched pairs may be aliases or duplicate groups, so they are not added to the 50% count until reviewed. eDNA detections remain separate from capture records and do not establish current presence, catchability, abundance, or habitat occupancy. The public source page's reuse rules require attribution and a notice of edits. No website, WordPress, Xserver, production API, or public search data is changed by this workflow.

The latest scan found 110 source water-system/river pairs with positive fish eDNA results. Exact-pair comparison found 43 pairs already represented by fish-positive atlas groups and 67 pairs without an exact atlas pair; none was an exact match to a currently empty group. Those 67 remain crosswalk candidates, not coverage additions.

The research artifact schema is `kanagawa-edna-river-group-candidates-v02`; the new fields carry aggregate coverage snapshots and a privacy-minimized registry name-pair status only.

Two live baselines are reported because the site has both a base atlas JSON and an article-embedded source layer. The strict base-JSON audit is 321/1,127 river-name groups (28.5%), with 243 additional qualifying groups needed for 50%; it excludes identity-held groups from the numerator. The published combined article/source-layer audit is 349/1,143 (30.5%), with 223 additional groups needed. Use the first when measuring the base JSON alone and the second when describing the already published combined layer; their numerators and denominators must not be mixed.

The official national river-code name list contains exact water-system/river-name pair rows for 4 of the 67 unmatched pairs: 2 have one exact row and 2 have multiple exact rows. The other 63 have no exact pair row in that list. Across all 110 candidates, 34 have one exact registry row, 3 have multiple rows, and 73 have no exact pair. These are only name-pair candidates: the registry does not include a prefecture field, and neither a single code row nor an exact name pair approves identity or publication. No river-code value is copied into the artifact. If all 67 unmatched pairs were later confirmed as distinct new display groups, the published-layer scenario would be 416/1,210 (34.4%), leaving 189 groups to reach 50%; the base-JSON-only scenario would be 388/1,194 (32.5%), leaving 209. Both scenarios are hypothetical and are not counted as progress.

- Source page: https://www.pref.kanagawa.jp/docs/b4f/suigen/edna.html
- Data-use rules: https://www.pref.kanagawa.jp/documents/97797/riyo-kiyaku.pdf
- [Official national river-code name list and its identity caveats](../NATIONAL_RIVER_CODES_V07.md)
