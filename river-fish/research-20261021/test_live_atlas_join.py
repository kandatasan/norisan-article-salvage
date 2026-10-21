"""Offline fail-closed tests for live-atlas name candidate review."""
import unittest
from audit_live_atlas_river_fish import classify, basin


class JoinTests(unittest.TestCase):
    def setUp(self):
        self.atlas = {
            "research_display_name_groups": 511, "fish_only_mvp": True,
            "entries": [
                {"id": "a", "name": "三刀屋川"},
                {"id": "b", "name": "三刀屋川"},
                {"id": "c", "name": "八幡川"},
                {"id": "d", "name": "赤川"},
            ],
            "links": [
                {"prefecture": "島根県", "water": "斐伊川", "river_id": "a"},
                {"prefecture": "島根県", "water": "斐伊川水系", "river_id": "b"},
                {"prefecture": "広島県", "water": "八幡川", "river_id": "c"},
                {"prefecture": "島根県", "water": "斐伊川", "river_id": "d"},
            ],
        }

    def row(self, **kw):
        x = {"prefecture": "島根県", "watershed": "斐伊川",
             "river": "赤川", "recorded_name": "アユ",
             "evidence_scope": "named_river", "integration_status": "staged_only",
             "source_id": "SH22", "verification_status": "source_text_checked",
             "conservation_review": "not_flagged"}
        x.update(kw)
        return x

    def test_single_exact_name_only_candidate(self):
        r = classify([self.row()], self.atlas)[0]
        self.assertEqual(r["join_review_status"], "EXACT_SINGLE_NAME_CANDIDATE")
        self.assertEqual(r["atlas_name_candidate_ids"], "d")
        self.assertEqual(r["approved_for_publish"], "NO")

    def test_duplicate_name_blocks_automatic_join(self):
        r = classify([self.row(river="三刀屋川")], self.atlas)[0]
        self.assertEqual(r["join_review_status"], "AMBIGUOUS_SAME_NAME")
        self.assertEqual(r["atlas_name_candidate_ids"], "a|b")

    def test_wrong_prefecture_not_joined(self):
        r = classify([self.row(prefecture="鳥取県")], self.atlas)[0]
        self.assertEqual(r["join_review_status"], "NOT_FOUND_IN_LIVE_ATLAS")

    def test_watershed_only_cannot_join(self):
        r = classify([self.row(river="", evidence_scope="watershed_only")], self.atlas)[0]
        self.assertEqual(r["join_review_status"], "WATERSHED_ONLY_NOT_LINKABLE")
        self.assertEqual(r["atlas_name_candidate_ids"], "")

    def test_conservation_blocks_even_with_exact_name(self):
        r = classify([self.row(conservation_review="required")], self.atlas)[0]
        self.assertEqual(r["join_review_status"], "CONSERVATION_REVIEW_REQUIRED")
        self.assertEqual(r["approved_for_publish"], "NO")

    def test_unverified_source_blocks_even_with_exact_name(self):
        r = classify([self.row(verification_status="search_excerpt_only")], self.atlas)[0]
        self.assertEqual(r["join_review_status"], "SOURCE_NOT_FULLY_CHECKED")

    def test_bad_schema_or_publication_status_fails_closed(self):
        with self.assertRaises(ValueError):
            classify([self.row()], {**self.atlas, "research_display_name_groups": 999})
        with self.assertRaises(ValueError):
            classify([self.row(integration_status="approved")], self.atlas)

    def test_only_terminal_watershed_label_normalized(self):
        self.assertEqual(basin("斐伊川水系"), "斐伊川")
        self.assertEqual(basin("斐伊川"), "斐伊川")
        self.assertEqual(basin("斐伊川上流"), "斐伊川上流")


if __name__ == "__main__":
    unittest.main()
