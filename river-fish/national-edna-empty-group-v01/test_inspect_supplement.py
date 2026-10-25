import io
import json
import unittest
import zipfile

from openpyxl import Workbook

from inspect_supplement import inspect


def fixture_xlsx():
    wb = Workbook()
    ws = wb.active
    ws.title = "sensitive river location"
    ws.append(["水系名", "河川名", "確認種", "地点名"])
    ws.append(["Hidden watershed", "Hidden River", "Sensitive fish", "hidden sampling site"])
    raw = io.BytesIO()
    wb.save(raw)
    return raw.getvalue()


class KanagawaWorkbookInspectionTests(unittest.TestCase):
    def test_only_header_schema_is_emitted(self):
        result = inspect(fixture_xlsx(), "fixture")
        serialized = json.dumps(result, ensure_ascii=False)
        for value in ("Hidden watershed", "Hidden River", "Sensitive fish", "hidden sampling site",
                      "sensitive river location"):
            self.assertNotIn(value, serialized)
        self.assertEqual(result["worksheets"][0]["sheet_index"], 1)
        self.assertTrue(result["worksheets"][0]["header_candidates"])

    def test_invalid_xlsx_rejected(self):
        with self.assertRaises(zipfile.BadZipFile):
            inspect(b"x" * 2048, "fixture")

    def test_oversized_workbook_rejected(self):
        with self.assertRaises(ValueError):
            inspect(b"x" * 4_000_001, "fixture")


if __name__ == "__main__":
    unittest.main()
