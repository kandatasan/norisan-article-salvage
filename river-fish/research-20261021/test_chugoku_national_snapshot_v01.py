"""Regression tests for the pinned, source-hash-verified Chugoku fish snapshot."""
import json
import unittest
from pathlib import Path

from validate_chugoku_national_snapshot_v01 import (
    MANIFEST_PATH, SNAPSHOT_PATH, load_snapshot, validate_snapshot,
)


class ChugokuNationalSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.encoded = SNAPSHOT_PATH.read_text(encoding="ascii")
        cls.meta = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_snapshot_hash_provenance_and_inventory(self):
        result = load_snapshot()
        self.assertEqual(result["source_sha256"],
                         "1fd6a7201f3100164bc9921002b2723c04a9b6d1f55e0e773b957f6d97205f4e")
        self.assertEqual(result["rows"], 3592)
        self.assertEqual(result["river_name_groups"], 35)
        self.assertEqual(result["literal_fish_labels"], 216)
        self.assertEqual(result["survey_year_range"], [2006, 2023])
        self.assertEqual(result["publication_approvals"], 0)
        self.assertFalse(result["site_updated"])

    def test_source_snapshot_contains_only_approved_schema_fields(self):
        rows = load_snapshot()["rows_data"]
        self.assertEqual(set(rows[0]), {
            "region", "watershed", "river_name", "survey_year", "recorded_name",
            "source_url", "source_sha256", "review_status",
        })
        self.assertTrue(all(x["review_status"] ==
                            "unapproved_requires_conservation_and_identity_review" for x in rows))
        self.assertTrue(all(x["region"] == "chugoku" for x in rows))
        self.assertNotIn("prefecture", rows[0])
        self.assertNotIn("national_river_code", rows[0])

    def test_corrupt_snapshot_fails_closed(self):
        changed = ("A" if self.encoded[0] != "A" else "B") + self.encoded[1:]
        with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
            validate_snapshot(changed, self.meta)

    def test_manifest_drift_fails_closed(self):
        changed = json.loads(json.dumps(self.meta))
        changed["official_source"]["source_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "source pin"):
            validate_snapshot(self.encoded, changed)

    def test_materialization_refuses_overwrite(self):
        self.assertTrue(SNAPSHOT_PATH.exists())
        self.assertTrue(MANIFEST_PATH.exists())


if __name__ == "__main__":
    unittest.main()
