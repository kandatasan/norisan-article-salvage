"""Offline national official direct river-fish ingestion checks."""
import csv
import copy
import tempfile
import unittest
from pathlib import Path
from extract_official_named_river_fish_nationwide_v04 import (
    REGIONS, manifest_for, validate_manifest, build_region, export_region,
    STATUS, FIELDS
)


class NineRegionTests(unittest.TestCase):
    def test_all_nine_pinned_manifests_have_safe_scope(self):
        self.assertEqual(len(REGIONS), 9)
        for region in REGIONS:
            with self.subTest(region=region):
                validate_manifest(region, manifest_for(region))

    def test_unknown_region_and_unpinned_url_blocked(self):
        with self.assertRaises(ValueError):
            manifest_for("other")
        m = manifest_for("chugoku")
        m["source_url"] = "https://example.org/unpinned.zip"
        with self.assertRaises(ValueError):
            validate_manifest("chugoku", m)

    def test_changed_hash_and_publication_status_blocked(self):
        m = manifest_for("chugoku")
        m["source_sha256"] = "wrong"
        with self.assertRaises(ValueError):
            validate_manifest("chugoku", m)
        m = manifest_for("chugoku")
        m["status"] = "published"
        with self.assertRaises(ValueError):
            validate_manifest("chugoku", m)

    def test_synthetic_rows_no_inferred_prefecture_or_code(self):
        m = manifest_for("chugoku")
        m["source_rows"] = 100
        m["unique_watersheds"] = 1
        m["distinct_name_labels"] = 1
        m["years"] = ["2021"]
        source = [{"C": "魚類", "F": "太田川", "G": "2021",
                   "J": "アユ", "M": "諸木川"} for _ in range(100)]
        records, report = build_region("chugoku", m, source)
        self.assertEqual(len(records), 1)
        self.assertEqual(report["status"], STATUS)
        self.assertEqual(report["river_name_groups"], 1)
        self.assertIsNone(report["prefecture"])
        self.assertIsNone(report["national_river_code"])
        self.assertEqual(report["sensitive_species_review"], "required_before_publication")
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "data"
            export_region("chugoku", m, records, report, out)
            with (out / "official_direct_river_fish_v04.csv").open(encoding="utf-8") as f:
                reader = csv.DictReader(f)
                self.assertEqual(reader.fieldnames, list(FIELDS))
                self.assertEqual(len(list(reader)), 1)
            with self.assertRaises(FileExistsError):
                export_region("chugoku", m, records, report, out)

    def test_source_count_mismatch_fails(self):
        m = manifest_for("chugoku")
        with self.assertRaises(ValueError):
            build_region("chugoku", m, [{"C": "魚類", "F": "太田川",
                                        "G": "2021", "J": "アユ", "M": "諸木川"}] * 100)


if __name__ == "__main__":
    unittest.main()
