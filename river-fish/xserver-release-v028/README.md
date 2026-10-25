# Xserver v0.28 upload bundle

The original v0.26 data archive is preserved byte for byte. The standalone
page loads the latest reviewed `source-connections-v01` layer (41 groups / 271
records) from a separate JSON file with a revision query for cache refresh.
The standalone page is `noindex`.

Build from the original v0.26 archive (not a previously generated v0.27 ZIP):

```sh
python river-fish/xserver-release-v028/build_release.py --baseline-zip /path/to/original-v026.zip --out /path/to/tsurikue_river_atlas_xserver_v028.zip
python river-fish/xserver-release-v028/verify_release.py /path/to/tsurikue_river_atlas_xserver_v028.zip
```

Upload the ZIP's `river-fish-atlas/` folder to `public_html/` as described in
`UPLOAD.txt`. The bundle contains the same data references as the published
WordPress atlas after the Tokyo municipal survey update: 359 / 1,143 display
name groups have fish evidence (31.4%). This number includes the existing
article's 16 source-only groups; no new group is introduced by this release.
The original data files are retained and pinned by SHA-256 in the manifest.

The WordPress post already embeds these 41 source groups. Uploading this ZIP
only refreshes the standalone Xserver page; it does not change the article or
switch it to the external JSON consumer. Keep any such switch as a separate,
guarded operation after live file verification.
