import unittest
from audit_river_collection_v01 import audit


class TestCollectionAudit(unittest.TestCase):
    def test_counts_and_quarantine(self):
        d = audit()
        self.assertEqual(d["riverCodeCount"], 35449)
        self.assertEqual(d["watershedCodeCount"], 5475)
        self.assertEqual(d["unmatchedRiverRows"], 19)
        self.assertEqual(len(d["unmatchedRiverCodes"]), 19)
        self.assertTrue(d["unmatchedWatershedPrefixes"])

    def test_unverified_links_stay_unverified(self):
        d = audit()
        self.assertEqual(d["collectionMatrix"]["individualRiverBiota"], "not_complete")
        self.assertEqual(d["collectionMatrix"]["riverToRiverConfluences"], "not_complete")
        self.assertEqual(d["safety"]["prefectureFromCodePrefix"], "prohibited")
        self.assertFalse(d["safety"]["liveSystemsTouched"])


if __name__ == "__main__":
    unittest.main()
