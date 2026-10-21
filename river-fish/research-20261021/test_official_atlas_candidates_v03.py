import unittest
from build_official_atlas_candidates_v03 import compare
from extract_official_named_river_fish_v03 import EXPECTED_SHA256


def record(water="太田川", river="諸木川", fish="アユ"):
    return {"region":"chugoku", "watershed":water, "river_name":river,
            "survey_year":"2021", "recorded_name":fish,
            "source_url":"https://www.nilim.go.jp/lab/fbg/ksnkankyo/download/slist/RT87_B01.zip",
            "source_sha256":EXPECTED_SHA256,
            "review_status":"unapproved_requires_conservation_and_identity_review"}


def atlas():
    return {"research_display_name_groups":511, "fish_only_mvp":True,
            "entries":[{"id":"1","name":"諸木川"},{"id":"2","name":"諸木川"},
                       {"id":"3","name":"赤川"}],
            "links":[{"prefecture":"広島県","water":"太田川水系","river_id":"1"},
                     {"prefecture":"山口県","water":"太田川水系","river_id":"2"},
                     {"prefecture":"島根県","water":"斐伊川水系","river_id":"3"}]}


class OfficialAtlasCandidateTests(unittest.TestCase):
    def test_ambiguous_name_never_auto_assigns_prefecture(self):
        result=compare([record()],atlas())
        group=result["groups"][0]
        self.assertEqual(group["match_class"],"MULTIPLE_NAVIGATION_NAME_CANDIDATES")
        self.assertEqual(len(group["candidate_navigation"]),2)
        self.assertFalse(group["official_prefecture_verified"])
        self.assertFalse(group["approved_for_publication"])

    def test_exact_single_navigation_still_unverified(self):
        group=compare([record("斐伊川","赤川")],atlas())["groups"][0]
        self.assertEqual(group["match_class"],"ONE_NAVIGATION_NAME_CANDIDATE_NOT_VERIFIED")
        self.assertFalse(group["national_river_code_verified"])
        self.assertEqual(group["species_publication_review"],"required")

    def test_unmatched_name_does_not_make_fake_id(self):
        group=compare([record("太田川","未収録川")],atlas())["groups"][0]
        self.assertEqual(group["candidate_navigation"],[])
        self.assertEqual(group["match_class"],"SOURCE_NAMED_RIVER_NOT_IN_LIVE_ATLAS")

    def test_hash_and_status_fail_closed(self):
        bad=record()
        bad["source_sha256"]="wrong"
        with self.assertRaises(ValueError):
            compare([bad],atlas())
        bad=record()
        bad["review_status"]="approved"
        with self.assertRaises(ValueError):
            compare([bad],atlas())

    def test_duplicate_atlas_ids_fail_closed(self):
        bad=atlas()
        bad["entries"].append({"id":"1","name":"別の川"})
        with self.assertRaises(ValueError):
            compare([record()],bad)

    def test_same_river_multiple_fish_years_grouped(self):
        result=compare([record(),record(fish="オイカワ")],atlas())
        self.assertEqual(result["river_name_groups"],1)
        self.assertEqual(result["source_fish_year_records"],2)
        self.assertEqual(result["groups"][0]["distinct_source_fish_labels"],2)


if __name__=="__main__":
    unittest.main()
