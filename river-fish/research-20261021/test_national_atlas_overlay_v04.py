import unittest
from build_national_atlas_overlay_v04 import compare
from extract_official_named_river_fish_nationwide_v04 import manifest_for


def row(water="太田川", river="諸木川", fish="アユ"):
    m=manifest_for("chugoku")
    return {"region":"chugoku","watershed":water,"river_name":river,
            "survey_year":"2021","recorded_name":fish,
            "source_url":m["source_url"],"source_sha256":m["source_sha256"],
            "review_status":"unapproved_requires_conservation_and_identity_review"}


def atlas():
    return {"research_display_name_groups":511,"fish_only_mvp":True,
            "entries":[{"id":"a","name":"諸木川"},{"id":"b","name":"諸木川"},
                       {"id":"c","name":"赤川"}],
            "links":[{"prefecture":"広島県","water":"太田川水系","river_id":"a"},
                     {"prefecture":"山口県","water":"太田川水系","river_id":"b"},
                     {"prefecture":"島根県","water":"斐伊川","river_id":"c"}]}


class NationalOverlayTests(unittest.TestCase):
    def test_duplicate_river_name_is_ambiguous(self):
        result=compare([row()],atlas(),"chugoku",manifest_for("chugoku"))
        group=result["groups"][0]
        self.assertEqual(group["status"],"MULTIPLE_NAVIGATION_NAME_CANDIDATES")
        self.assertEqual(len(group["atlas_name_candidates"]),2)
        self.assertFalse(group["official_prefecture_verified"])
        self.assertFalse(group["approved_for_publication"])

    def test_exact_single_is_not_verified(self):
        result=compare([row("斐伊川","赤川")],atlas(),"chugoku",manifest_for("chugoku"))
        group=result["groups"][0]
        self.assertEqual(group["status"],"ONE_NAVIGATION_NAME_CANDIDATE_NOT_VERIFIED")
        self.assertFalse(group["national_river_code_verified"])

    def test_missing_atlas_river_is_not_fake_id(self):
        result=compare([row(river="未収録川")],atlas(),"chugoku",manifest_for("chugoku"))
        self.assertEqual(result["groups"][0]["atlas_name_candidates"],[])

    def test_reject_mixed_regions_and_source_hash(self):
        bad=row()
        bad["region"]="kanto"
        with self.assertRaises(ValueError):
            compare([bad],atlas(),"chugoku",manifest_for("chugoku"))
        bad=row()
        bad["source_sha256"]="wrong"
        with self.assertRaises(ValueError):
            compare([bad],atlas(),"chugoku",manifest_for("chugoku"))

    def test_multiple_fish_records_counted_once_per_river(self):
        result=compare([row(),row(fish="オイカワ")],atlas(),"chugoku",manifest_for("chugoku"))
        self.assertEqual(result["source_named_river_groups"],1)
        self.assertEqual(result["source_fish_year_records"],2)
        self.assertEqual(result["groups"][0]["fish_name_label_count"],2)

    def test_dangling_atlas_link_fails_closed(self):
        bad=atlas()
        bad["links"][0]["river_id"]="missing"
        with self.assertRaises(ValueError):
            compare([row()],bad,"chugoku",manifest_for("chugoku"))


if __name__=="__main__":
    unittest.main()
