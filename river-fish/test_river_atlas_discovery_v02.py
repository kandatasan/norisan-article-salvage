"""Evidence-bound navigation: never invent tributaries or river-level species."""
import unittest
from build_river_atlas_discovery_v02 import discovery


class TestDiscovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = discovery()

    def test_parent_relationships_remain_unknown(self):
        self.assertEqual(self.data["riverTreeStatus"],
                         "unavailable_until_independent_parent_evidence")
        self.assertTrue(all(r["parentRiverCode"] is None and not r["children"]
                            for r in self.data["rivers"]))
        self.assertEqual(len({r["riverCode"] for r in self.data["rivers"]}),
                         self.data["riverCount"])

    def test_species_reverse_index_is_survey_scoped(self):
        names = [s["recordedName"] for s in self.data["species"]]
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(all(s["watershedCodeMatch"] == "unverified" and
                            s["individualRiverPresence"] == "not_verified" and
                            s["sourceUrls"] for s in self.data["species"]))
        self.assertEqual(self.data["directRiverSpeciesStatus"], "not_available")

    def test_scope_rejects_mismatched_source(self):
        from build_river_atlas_poc_v01 import collect
        raw = collect()
        raw["fishSurvey"][0]["region"] = "other"
        with self.assertRaises(ValueError):
            discovery(raw)


if __name__ == "__main__":
    unittest.main()
