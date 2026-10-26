import unittest
from scripts.apply_editorial_draft_once import build_existing_table_cell_update

class TestNXHUDTablePatch(unittest.TestCase):
    def setUp(self):
        self.cfg = {
            "target_row_label": "フロントガラスに<br>速度などを表示",
            "target_column_index": 0, "expected_columns": 2,
            "expected_old_value": "—", "new_value": "○",
            "expected_old_style": "color:#6b7280!important;",
            "new_style": "color:#19634b!important;",
        }
        self.row = '<tr><th scope="row">フロントガラスに<br>速度などを表示</th><td style="color:#6b7280!important;">—</td><td style="color:#19634b!important;">○</td></tr>'
    def test_changes_only_one_cell(self):
        before = '<div>untouched</div>' + self.row + '<p>all other content</p>'
        result, action = build_existing_table_cell_update(before, self.cfg)
        self.assertEqual(action, "UPDATE")
        self.assertEqual(result, before.replace('<td style="color:#6b7280!important;">—</td>', '<td style="color:#19634b!important;">○</td>'))
    def test_idempotent(self):
        result, _ = build_existing_table_cell_update(self.row, self.cfg)
        result2, action = build_existing_table_cell_update(result, self.cfg)
        self.assertEqual(action, "ALREADY_PRESENT")
        self.assertEqual(result2, result)
    def test_rejects_human_edit(self):
        with self.assertRaises(RuntimeError):
            build_existing_table_cell_update(self.row.replace('>—</td>', '>△</td>'), self.cfg)
    def test_rejects_duplicate_row(self):
        with self.assertRaises(RuntimeError):
            build_existing_table_cell_update(self.row+self.row, self.cfg)
    def test_rejects_missing_column(self):
        with self.assertRaises(RuntimeError):
            build_existing_table_cell_update(self.row.replace('<td style="color:#19634b!important;">○</td>', ''), self.cfg)

if __name__ == "__main__":
    unittest.main()
