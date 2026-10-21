"""Review packet is not a fish-publication payload."""
import copy
import unittest
from build_chugoku_review_packet_v08 import render, SCHEMA as PACKET_SCHEMA
from build_chugoku_source_crosscheck_v07 import SCHEMA as INPUT_SCHEMA


def fixture():
    rows = []
    for i in range(13):
        ready = i < 7
        rows.append({
            "prefecture_source_publisher": "島根県" if i < 9 else "鳥取県",
            "watershed": "斐伊川" if i < 9 else "日野川",
            "river": "架空の試験川" + str(i),
            "source_ids": ["SH22" if i < 9 else "TO16"],
            "source_urls": ["https://www1.pref.shimane.lg.jp/official.pdf"] if i < 9
                           else ["https://www.pref.tottori.lg.jp/official.pdf"],
            "provincial_evidence_rows": 1,
            "national_chugoku_survey_records_same_water_river_name": 2,
            "independent_same_literal_fish_label_count": 1,
            "national_river_code_name_candidates": ["8707090023"] if ready else [],
            "live_atlas_navigation_name_candidate_ids": [],
            "evidence_gate": ("NAMED_RIVER_SOURCE_TEXT_CHECKED_NOT_IDENTITY_VERIFIED" if ready
                              else "CONTEXT_ONLY_REQUIRES_SCOPE_REVIEW"),
            "review_priority": ("B_NEW_RIVER_REVIEW" if ready
                                else "C_EVIDENCE_SCOPE_OR_CONSERVATION_REVIEW"),
            "source_conservation_flag_rows": 0,
            "source_original_not_checked_rows": 0,
            "source_name_identity_verified": False,
            "code_identity_verified": False,
            "atlas_identity_verified": False,
            "species_publication_review": "required",
            "approved_for_publication": False,
        })
    return {
        "schema": INPUT_SCHEMA, "status": "REVIEW_ONLY_DO_NOT_UPLOAD",
        "provincial_candidate_rows": 124,
        "named_river_candidate_rows": 115,
        "watershed_only_rows_held": 9,
        "river_groups": 13,
        "national_chugoku_fish_year_records": 3592,
        "priority_counts": {"B_NEW_RIVER_REVIEW": 7,
                            "C_EVIDENCE_SCOPE_OR_CONSERVATION_REVIEW": 6},
        "river_groups_with_national_river_code_single_name_candidate": 7,
        "river_groups_with_independent_literal_fish_overlap": 2,
        "rows": rows,
        "live_atlas_json_sha256": "a" * 64,
    }


class PacketTests(unittest.TestCase):
    def test_seven_ready_six_held_and_not_publishable(self):
        md = render(fixture())
        self.assertIn("先に同一河川を確認する7グループ", md)
        self.assertIn("まだ個別河川へつなげない6グループ", md)
        self.assertIn("公開承認は0", md)
        self.assertIn("8707090023", md)
        self.assertNotIn("recorded_name", md)
        self.assertNotIn("魚名：", md)
        self.assertNotIn("approved_for_publication", md)

    def test_approved_row_fails_closed(self):
        d = fixture()
        d["rows"][0]["approved_for_publication"] = True
        with self.assertRaises(ValueError):
            render(d)

    def test_unknown_external_source_domain_rejected(self):
        d = fixture()
        d["rows"][0]["source_urls"] = ["https://evil.example.net/fish"]
        with self.assertRaises(ValueError):
            render(d)

    def test_count_drift_fails_closed(self):
        d = fixture()
        d["named_river_candidate_rows"] = 116
        with self.assertRaises(ValueError):
            render(d)

    def test_fish_name_field_injected_rejected(self):
        d = fixture()
        d["rows"][0]["recorded_name"] = "希少種"
        with self.assertRaises(ValueError):
            render(d)

    def test_duplicate_river_key_fails(self):
        d = fixture()
        d["rows"][1]["river"] = d["rows"][0]["river"]
        with self.assertRaises(ValueError):
            render(d)

    def test_html_and_pipe_in_river_name_escaped(self):
        d = fixture()
        d["rows"][0]["river"] = "<script>|bad"
        md = render(d)
        self.assertNotIn("<script>", md)
        self.assertIn("&lt;script&gt;｜bad", md)


if __name__ == "__main__":
    unittest.main()
