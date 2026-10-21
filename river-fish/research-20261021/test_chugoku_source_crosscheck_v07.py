"""Safety and source provenance tests for five-prefecture fish river crosscheck."""
import copy
import unittest
from build_chugoku_source_crosscheck_v07 import (
    analyze, read_rows, INPUT, PROVINCIAL_FIELDS, SCHEMA,
)
from extract_official_named_river_fish_nationwide_v04 import (
    manifest_for, FIELDS as NATIONAL_FIELDS,
)


def provincial(scope="named_river", status="source_text_checked", conservation="not_flagged",
               fish="オイカワ"):
    return {
        "prefecture": "島根県", "watershed": "斐伊川", "river": "三刀屋川" if scope != "watershed_only" else "",
        "evidence_scope": scope, "recorded_name": fish,
        "evidence_kind": "official_survey_summary", "survey_year": "",
        "source_id": "SH22", "source_locator": "表2-4",
        "verification_status": status, "source_url": "https://example.org/official.pdf",
        "conservation_review": conservation, "integration_status": "staged_only",
        "notes": "",
    }


def national(fish="オイカワ"):
    m = manifest_for("chugoku")
    return {
        "region": "chugoku", "watershed": "斐伊川", "river_name": "三刀屋川",
        "survey_year": "2015", "recorded_name": fish,
        "source_url": m["source_url"], "source_sha256": m["source_sha256"],
        "review_status": "unapproved_requires_conservation_and_identity_review",
    }


def code():
    return {
        "river_code": "8700010001", "river_name": "三刀屋川",
        "watershed_code": "870001", "watershed_name": "斐伊川",
        "code_region_prefix": "87", "source_url": "https://example.org/code",
        "identity_status": "coded_name_only_not_geographically_verified",
        "site_status": "research_only",
    }


def water():
    return {"watershed_code": "870001", "watershed_name": "斐伊川"}


def atlas(yes=True):
    return {
        "research_display_name_groups": 511, "fish_only_mvp": True,
        "entries": [{"id": "a1", "name": "三刀屋川"}] if yes else [],
        "links": [{"prefecture": "島根県", "water": "斐伊川",
                   "river_id": "a1"}] if yes else [],
    }


def run(prov=None, fish=None, river_codes=None, live=None):
    return analyze(prov if prov is not None else [provincial()],
                   fish if fish is not None else [national()],
                   live if live is not None else atlas(),
                   river_codes if river_codes is not None else [code()],
                   [water()], manifest_for("chugoku"))


class ChugokuSourceCrosscheckTests(unittest.TestCase):
    def test_existing_candidate_is_never_approved(self):
        d = run()
        self.assertEqual(d["schema"], SCHEMA)
        self.assertEqual(d["priority_counts"], {"A_EXISTING_ATLAS_RIVER_REVIEW": 1})
        x = d["rows"][0]
        self.assertEqual(x["independent_same_literal_fish_label_count"], 1)
        self.assertFalse(x["approved_for_publication"])
        self.assertFalse(x["code_identity_verified"])
        self.assertFalse(x["atlas_identity_verified"])
        self.assertNotIn("オイカワ", str(d))
        self.assertNotIn("recorded_name", str(d))

    def test_new_river_candidate_not_automatically_added(self):
        d = run(live=atlas(False))
        self.assertEqual(d["rows"][0]["review_priority"], "B_NEW_RIVER_REVIEW")
        self.assertEqual(d["rows"][0]["live_atlas_navigation_name_candidate_ids"], [])

    def test_context_is_blocked_even_with_two_name_matches(self):
        d = run(prov=[provincial(scope="named_river_context")])
        self.assertEqual(d["rows"][0]["evidence_gate"], "CONTEXT_ONLY_REQUIRES_SCOPE_REVIEW")
        self.assertEqual(d["rows"][0]["review_priority"], "C_EVIDENCE_SCOPE_OR_CONSERVATION_REVIEW")

    def test_conservation_or_unread_never_ready(self):
        d = run(prov=[provincial(conservation="required")])
        self.assertEqual(d["rows"][0]["evidence_gate"], "CONSERVATION_REVIEW_REQUIRED")
        d = run(prov=[provincial(status="search_excerpt_only")])
        self.assertEqual(d["rows"][0]["evidence_gate"], "SOURCE_ORIGINAL_NOT_FULLY_CHECKED")

    def test_watershed_only_held_not_inferred(self):
        d = run(prov=[provincial(), provincial(scope="watershed_only")])
        self.assertEqual(d["river_groups"], 1)
        self.assertEqual(d["watershed_only_rows_held"], 1)
        self.assertEqual(d["named_river_candidate_rows"], 1)

    def test_no_fuzzy_taxonomy_or_false_independent_overlap(self):
        d = run(fish=[national("カワムツ")])
        self.assertEqual(d["rows"][0]["independent_same_literal_fish_label_count"], 0)
        self.assertEqual(d["rows"][0]["national_chugoku_survey_records_same_water_river_name"], 1)

    def test_ambiguous_code_not_ready(self):
        c2 = dict(code(), river_code="8700010002")
        d = run(river_codes=[code(), c2])
        self.assertEqual(d["rows"][0]["review_priority"], "D_AMBIGUOUS_OR_MISSING_CODE_REVIEW")

    def test_source_status_and_pinned_sha_fail_closed(self):
        p = provincial()
        p["integration_status"] = "published"
        with self.assertRaises(ValueError):
            run(prov=[p])
        n = national()
        n["source_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            run(fish=[n])

    def test_real_124_staged_rows_are_grouped_safely(self):
        provincial_rows = read_rows(INPUT, PROVINCIAL_FIELDS)
        self.assertEqual(len(provincial_rows), 124)
        d = run(prov=provincial_rows)
        self.assertEqual(d["river_groups"], 13)
        self.assertEqual(d["named_river_candidate_rows"], 115)
        self.assertEqual(d["watershed_only_rows_held"], 9)
        self.assertTrue(all(x["approved_for_publication"] is False for x in d["rows"]))

    def test_live_atlas_schema_drift_stops(self):
        a = atlas()
        a["research_display_name_groups"] = 512
        with self.assertRaises(ValueError):
            run(live=a)


if __name__ == "__main__":
    unittest.main()
