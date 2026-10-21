import csv
import unittest
from pathlib import Path
from urllib.parse import urlparse

DATA = Path(__file__).resolve().parent / "chugoku_seven_river_plan_reaches_v01.csv"
EXPECTED = {
    ("島根県", "斐伊川", "斐伊川", "8707040001"): "16.85",
    ("島根県", "斐伊川", "三刀屋川", "8707040191"): "35.18",
    ("島根県", "斐伊川", "久野川", "8707040204"): "16.73",
    ("島根県", "斐伊川", "深野川", "8707040211"): "16.90",
    ("島根県", "斐伊川", "阿井川", "8707040213"): "20.70",
    ("鳥取県", "日野川", "日野川", "8707030001"): "59.80",
    ("鳥取県", "日野川", "大川", "8707030012"): "3.00",
}


class SevenRiverPlanReachTests(unittest.TestCase):
    def test_exact_seven_officially_defined_plan_reaches(self):
        with DATA.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 7)
        keys = {(r["prefecture"], r["watershed"], r["river"], r["river_code"]): r
                for r in rows}
        self.assertEqual(set(keys), set(EXPECTED))
        self.assertEqual({k: v["plan_length_km"] for k, v in keys.items()}, EXPECTED)

    def test_tributary_relation_and_source_are_explicit(self):
        with DATA.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            self.assertTrue(r["official_relation"])
            self.assertTrue(r["source_locator"])
            self.assertIn("pref.shimane.lg.jp" if r["prefecture"] == "島根県"
                          else "pref.tottori.lg.jp", urlparse(r["source_url"]).hostname)
            if r["river"] in {"三刀屋川", "久野川", "深野川", "阿井川", "大川"}:
                self.assertIn("合流支川", r["official_relation"])

    def test_plan_length_never_becomes_fish_sampling_extent(self):
        with DATA.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            self.assertIn("採集地点", r["fish_scope_note"]) if r["prefecture"] == "島根県" else self.assertIn("転用しない", r["fish_scope_note"])
            self.assertEqual(r["fish_publication_approval"], "not_approved")
            self.assertEqual(r["integration_status"], "research_only")


if __name__ == "__main__":
    unittest.main()
