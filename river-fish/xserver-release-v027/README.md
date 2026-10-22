# Xserver v0.27 upload bundle

Packages the unchanged v0.26 data archive with the reviewed 31 source groups / 261 records from `source-connections-v01`.
The standalone page loads the supplementary data from JSON, rather than embedding the records in its executable script.
The JSON request has a content revision query to avoid an old cached source layer.

Build with the existing `tsurikue_river_atlas_xserver.zip` baseline:

```sh
python river-fish/xserver-release-v027/build_release.py --baseline-zip /path/to/previous.zip --out /path/to/tsurikue_river_atlas_xserver.zip
```

Upload the enclosed `river-fish-atlas/` folder into the domain's `public_html/` directory. See `UPLOAD.txt`.
The baseline archive remains unchanged; every retained file has a SHA-256 entry in `release-v027.json`.
No production data is written by the builder. The generated standalone page is noindex.

The WordPress post still uses the verified embedded layer. After the new public JSON is verified against its reviewed hash, `external_script()` supplies the equivalent external consumer for a guarded script-only migration. Do not switch the post before that verification. The added workflow only checks and exports the consumer; it cannot deploy or change WordPress.

## Release verification on 2026-10-22

- Live post: 4240 / `japan-river-atlas` / published / featured media 4238. Executable SHA-256: `573d61b513881306b9f931e5a99cdc94320f2f141b5c72cb34939edd2d17eafc`.
- Four live core JSON files match the baseline ZIP byte for byte; the builder pins their hashes and rejects another release.
- ZIP CRC, every retained baseline file hash, supplemental JSON equality and all indexed runtime JSON paths pass `verify_release.py` (541 data files).
- External consumer passes the existing browser interaction suite through `test_external_runtime.cjs`: river search, fish-only filter, fish reverse search and navigation, held fish exclusion, existing historical records retained.
- All five source-connection regression tests pass; generated JavaScript passes `node --check`.
- Bundle composition adds 31 source groups / 261 records. When loaded it produces 349/1,143 display-name groups (30.5%); the count is not a physical-river count.
- Xserver upload and the WordPress migration remain pending. This release does not claim they are complete.
