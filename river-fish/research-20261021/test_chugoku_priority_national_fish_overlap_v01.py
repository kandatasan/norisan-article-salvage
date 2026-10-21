import csv
import unittest
from pathlib import Path

from audit_chugoku_priority_national_fish_overlap_v01 import summarize, validate_rows

TARGETS = Path(__file__).resolve().parent / "chugoku_seven_river_plan_reaches_v01.csv"


def load_targets():
    with TARGETS.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


class PriorityNationalFishOverlapTests(unittest.TestCase):
    def test_exact_water_and_river_name_pair_only(self):
        records = [
            ("斐伊川", "斐伊川", "2019", "オイカワ"),
            ("斐伊川", "斐伊川", "2019", "カワムツ"),
            ("斐伊川", "斐伊川", "2014", "オイカワ"),
            ("日野川", "日野川", "2009", "コイ"),
            ("別水系", "三刀屋川", "2020", "アユ"),
            ("斐伊川", "同名の別支流", "2020", "アユ"),
        ]
        rows = summarize(records, load_targets())
        by_key = {(r["watershed"], r["river"]): r for r in rows}
        self.assertEqual(by_key[("斐伊川", "斐伊川")]["survey_years"], "2014;2019")
        self.assertEqual(by_key[("斐伊川", "斐伊川")]["unique_year_fish_record_count"], "3")
        self.assertEqual(by_key[("日野川", "日野川")]["unique_year_fish_record_count"], "1")
        self.assertEqual(by_key[("斐伊川", "三刀屋川")]["unique_year_fish_record_count"], "0")

    def test_summary_has_no_fish_or_station_fields_and_never_approves(self):
        rows = summarize([], load_targets())
        validate_rows(rows)
        self.assertEqual(len(rows), 7)
        for row in rows:
            self.assertEqual(row["fish_publication_approval"], "not_approved")
            self.assertEqual(row["integration_status"], "research_only")
            self.assertNotIn("魚名", row)
            self.assertNotIn("地点", row)


if __name__ == "__main__":
    unittest.main()
