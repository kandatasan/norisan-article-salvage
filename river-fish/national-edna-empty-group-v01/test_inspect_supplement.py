import io
import json
import unittest
import zipfile

from openpyxl import Workbook
from inspect_supplement import inspect


def fixture_zip():
    wb = Workbook()
    ws = wb.active
    ws.title = "Table S1"
    ws.append(["Site", "Prefecture", "Water body", "Species", "Sample secret location"])
    ws.append(["unpublished sample", "Hidden prefecture", "Hidden River", "Sensitive fish", "hidden coordinate"])
    xlsx = io.BytesIO()
    wb.save(xlsx)
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("TableS1.xlsx", xlsx.getvalue())
    return raw.getvalue()


class SupplementInspectionTests(unittest.TestCase):
    def test_only_schema_metadata_is_emitted(self):
        result = inspect(fixture_zip())
        serialized = json.dumps(result)
        for value in ("unpublished sample", "Hidden River", "Sensitive fish", "hidden coordinate"):
            self.assertNotIn(value, serialized)
        self.assertEqual(result["workbooks"][0]["sheets"][0]["name"], "Table S1")
        self.assertTrue(result["workbooks"][0]["sheets"][0]["header_candidates"])

    def test_bad_zip_rejected(self):
        with self.assertRaises(zipfile.BadZipFile):
            inspect(b"x" * 2048)

    def test_oversized_source_rejected(self):
        with self.assertRaises(ValueError):
            inspect(b"x" * 8_000_001)


if __name__ == "__main__":
    unittest.main()
