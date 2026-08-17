import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import old_tsurikue_photo_filename_fallback as fb


class RecoveredFilenameFallbackTests(unittest.TestCase):
    def test_real_ref_file_has_deduplicated_positions(self):
        refs = fb.load_refs()
        self.assertEqual(len(refs), 363)
        self.assertNotIn("lexus", " ".join(row["slug"] for row in refs).lower())

    def test_copy_suffix_alias_is_conservative(self):
        self.assertEqual(fb._copy_suffix_alias("IMG_2471-1.jpg"), "img_2471.jpg")
        self.assertEqual(fb._copy_suffix_alias("abc123-2.jpeg"), "abc123.jpeg")
        self.assertIsNone(fb._copy_suffix_alias("image-1.jpg"))

    def test_exact_unique_match(self):
        media = [{"id": 10, "source_url": "https://tsurikue.com/wp-content/uploads/2026/05/IMG_1111.jpg"}]
        exact, aliases = fb.build_indexes(media)
        row = fb.match_ref({"slug": "x", "order": 1, "filename": "IMG_1111-scaled.jpg", "heading": "H"}, exact, aliases)
        self.assertEqual(row["result"], "MATCH_FILENAME")
        self.assertEqual(row["matched_media_id"], 10)

    def test_copy_suffix_unique_match(self):
        media = [{"id": 11, "source_url": "https://tsurikue.com/wp-content/uploads/2026/05/IMG_2471.jpg"}]
        exact, aliases = fb.build_indexes(media)
        row = fb.match_ref({"slug": "x", "order": 1, "filename": "IMG_2471-1.jpg", "heading": "H"}, exact, aliases)
        self.assertEqual(row["result"], "MATCH_FILENAME")
        self.assertEqual(row["matched_media_id"], 11)

    def test_ambiguous_match_stays_placeholder(self):
        media = [
            {"id": 1, "source_url": "https://tsurikue.com/wp-content/uploads/2026/05/IMG_2471.jpg"},
            {"id": 2, "source_url": "https://tsurikue.com/wp-content/uploads/2026/05/IMG_2471-2.jpg"},
        ]
        exact, aliases = fb.build_indexes(media)
        row = fb.match_ref({"slug": "x", "order": 1, "filename": "IMG_2471-1.jpg", "heading": "H"}, exact, aliases)
        self.assertEqual(row["result"], "PLACEHOLDER")
        self.assertIsNone(row["matched_media_id"])


if __name__ == "__main__":
    unittest.main()
