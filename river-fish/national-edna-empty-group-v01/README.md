# Kanagawa prefectural eDNA source inspection (research only)

This workflow checks the public Excel source files linked from Kanagawa Prefecture's environmental DNA page. The page lists fish eDNA results for FY2021–FY2025, including surveys of the prefecture's water-source rivers and a prefecture-wide citizen-science project.

The current step checks only workbook structure. It prints each source's checksum and size, worksheet count, dimensions, and recognized column-header labels. It does not print worksheet titles or any source row, sampling-site name, locality, coordinate, or species result. A separate reviewed extraction and river-name crosswalk are required before this source can affect coverage.

eDNA detections remain a distinct evidence method. They are not rendered as capture records, catchability, abundance, or confirmation of present-day habitat. The public source page and the linked data-use rules permit reuse with source attribution and a notice that the data was edited. No website, WordPress, Xserver, or public search data is changed by this workflow.

- Source page: https://www.pref.kanagawa.jp/docs/b4f/suigen/edna.html
- Data-use rules: https://www.pref.kanagawa.jp/documents/97797/riyo-kiyaku.pdf
