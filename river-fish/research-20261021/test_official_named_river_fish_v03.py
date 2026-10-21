"""Offline tests for official direct river↔fish extraction and sensitive-data boundary."""
import csv
import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
from extract_official_named_river_fish_v03 import (
    aggregate, workbook_records, write_outputs, HEADERS, FIELDS, M
)


def fixture_book(headers=HEADERS):
    strings = list(headers.values()) + ["魚類", "太田川", "諸木川", "アユ", "魚介類", "エビ"]
    idx = {s: i for i, s in enumerate(strings)}
    shared = ('<sst xmlns="' + M[1:-1] + '">' +
              "".join("<si><t>" + s + "</t></si>" for s in strings) + "</sst>")
    rows = [headers, {"C": "魚類", "F": "太田川", "G": "2021",
                      "J": "アユ", "M": "諸木川"},
            {"C": "魚介類", "F": "太田川", "G": "2021",
             "J": "エビ", "M": "諸木川"}]
    xmlrows = []
    for i, row in enumerate(rows, 1):
        cells = []
        for col, value in row.items():
            if value in idx:
                cells.append(f'<c r="{col}{i}" t="s"><v>{idx[value]}</v></c>')
            else:
                cells.append(f'<c r="{col}{i}"><v>{value}</v></c>')
        xmlrows.append(f'<row r="{i}">' + "".join(cells) + "</row>")
    sheet = '<worksheet xmlns="' + M[1:-1] + '"><sheetData>' + "".join(xmlrows) + '</sheetData></worksheet>'
    inner = BytesIO()
    with ZipFile(inner, "w") as z:
        z.writestr("xl/sharedStrings.xml", shared)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
    outer = BytesIO()
    with ZipFile(outer, "w") as z:
        z.writestr("official/魚類_中国.xlsx", inner.getvalue())
    return outer.getvalue()


class OfficialNamedRiverTests(unittest.TestCase):
    def test_parser_reads_only_five_columns(self):
        rows = list(workbook_records(fixture_book(), "official/魚類_中国.xlsx"))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["M"], "諸木川")
        self.assertEqual(rows[0]["J"], "アユ")
        self.assertEqual(set(rows[0]), set(HEADERS))
        self.assertNotIn("station", str(rows))

    def test_schema_drift_fails(self):
        bad = dict(HEADERS)
        bad["M"] = "支川名"
        with self.assertRaises(ValueError):
            list(workbook_records(fixture_book(bad), "official/魚類_中国.xlsx"))

    def test_missing_member_fails(self):
        with self.assertRaises(ValueError):
            list(workbook_records(fixture_book(), "missing.xlsx"))

    def test_category_and_duplicates_and_no_prefecture(self):
        rows = [{"C": "魚類", "F": "太田川", "G": "2021", "J": "アユ", "M": "諸木川"},
                {"C": "魚類", "F": "太田川", "G": "2021", "J": "アユ", "M": "諸木川"},
                {"C": "魚介類", "F": "太田川", "G": "2021", "J": "エビ", "M": "諸木川"}]
        records, meta = aggregate(rows, min_source_rows=1)
        self.assertEqual(len(records), 1)
        self.assertEqual(meta["counts"]["valid_source_rows"], 2)
        self.assertEqual(meta["counts"]["excluded_not_explicit_fish_category"], 1)
        self.assertIsNone(meta["prefecture"])
        self.assertFalse(meta["national_river_code_identity_verified"])
        self.assertEqual(meta["sensitive_species_review"], "required_before_publication")

    def test_no_watershed_inference(self):
        rows = [{"C": "魚類", "F": "太田川", "G": "2021", "J": "アユ", "M": ""},
                {"C": "魚類", "F": "太田川", "G": "2021", "J": "アユ", "M": "諸木川"}]
        data, _ = aggregate(rows, min_source_rows=1)
        self.assertEqual(data, [("太田川", "諸木川", "2021", "アユ")])

    def test_no_location_fields_in_csv_and_no_overwrite(self):
        data, meta = aggregate([{"C": "魚類", "F": "太田川", "G": "2021", "J": "アユ", "M": "諸木川"}], min_source_rows=1)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "results"
            p = write_outputs(out, data, meta)
            with p.open(encoding="utf-8") as f:
                r = csv.DictReader(f)
                self.assertEqual(r.fieldnames, list(FIELDS))
                self.assertEqual(len(list(r)), 1)
            with self.assertRaises(FileExistsError):
                write_outputs(out, data, meta)
            meta2 = json.loads((out / "direct_named_river_fish_summary_v03.json").read_text())
            self.assertEqual(meta2["status"], "STAGED_REVIEW_ONLY_NOT_FOR_PUBLICATION")


if __name__ == "__main__":
    unittest.main()
