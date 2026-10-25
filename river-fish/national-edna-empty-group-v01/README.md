# National eDNA river-name candidate source (research only)

This read-only source inspection evaluates Table S1 from the peer-reviewed 2026 nationwide black-bass eDNA study (DOI `10.1002/edn3.70292`) as a possible source for fish-empty atlas display groups.

The paper reports 121 sampling sites across 31 prefectures in 2021–2023; eDNA from at least one of three bass taxa was detected at 87 sites. That makes it a promising source for the faster target: one directly named fish record can qualify an existing empty display group. A waterbody/site label is not automatically an atlas river, and eDNA is never rendered as capture, catchability, abundance, or current fish distribution.

The workflow fetches the publisher's public supplement and emits only its SHA-256, archive member names, workbook dimensions, sheet names, and recognized column-header labels. It does not store or upload source rows, sample identifiers, coordinates, locality names, or species results. A separate reviewed parser and crosswalk will be needed before any candidate can affect coverage. This workflow never writes the website, WordPress, or Xserver.

Source article: https://doi.org/10.1002/edn3.70292
