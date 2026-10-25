
# Kanagawa prefectural eDNA river candidates (research only)

This workflow reads the public Excel source files linked from Kanagawa Prefecture's environmental DNA page. The page lists fish eDNA results for FY2021–FY2025, including surveys of the prefecture's water-source rivers and a prefecture-wide citizen-science project.

The extractor matches source fish labels in memory against the repository's official taxon reference and aggregates positive results only when the source provides explicit water-system and river fields. The Actions log prints national coverage and aggregate match counts. Its downloadable research artifact lists candidate river groups, source IDs, survey years, and counts; it omits fish names, sampling-site names, coordinates, and river codes. No source row is saved.

Every group remains `research_only_unapproved`. Exact water-system and river matches are checked against the public atlas, but the atlas does not carry reliable prefecture fields for every group; even exact pair matches need a prefecture cross-check. Unmatched pairs may be aliases or duplicate groups, so they are not added to the 50% count until reviewed. eDNA detections remain separate from capture records and do not establish current presence, catchability, abundance, or habitat occupancy. The public source page's reuse rules require attribution and a notice of edits. No website, WordPress, Xserver, production API, or public search data is changed by this workflow.

The latest local scan found 110 source water-system/river pairs with positive fish eDNA results. Exact-pair comparison found 43 pairs already represented by fish-positive atlas groups and 67 pairs without an exact atlas pair; none was an exact match to a currently empty group. Those 67 remain crosswalk candidates, not coverage additions. If all 67 later prove to be distinct new groups and are approved, a rough projection would be 416/1,210 (34.4%), leaving 189 groups to reach 50%. This is hypothetical and does not change the current coverage metric.

- Source page: https://www.pref.kanagawa.jp/docs/b4f/suigen/edna.html
- Data-use rules: https://www.pref.kanagawa.jp/documents/97797/riyo-kiyaku.pdf
