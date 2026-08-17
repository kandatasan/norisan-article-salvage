import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "old_tsurikue_photo_reconciliation.py"
spec = importlib.util.spec_from_file_location("photo", MODULE_PATH)
photo = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = photo
assert spec.loader
spec.loader.exec_module(photo)
ARCHIVES = Path(__file__).parents[1] / "scripts" / "old_tsurikue_archives.json"


class DummyResponse:
    def __init__(self, payload=b"{}", headers=None):
        self.payload = payload
        self.headers = headers or {}
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self):
        return self.payload


class PhotoReconciliationTests(unittest.TestCase):
    def test_archive_map_has_exactly_46_non_lexus_targets(self):
        rows = json.loads(ARCHIVES.read_text(encoding="utf-8"))
        self.assertEqual(46, len(rows))
        self.assertEqual(46, len({row["slug"] for row in rows}))
        self.assertFalse(any("lexus-diary.com" in json.dumps(row).lower() for row in rows))

    def test_http_request_is_explicit_get(self):
        seen = []
        def fake_urlopen(req, timeout=0):
            seen.append(req)
            return DummyResponse(b"{}")
        with mock.patch.object(photo.urllib.request, "urlopen", fake_urlopen):
            photo.get_bytes("https://example.com/test")
        self.assertEqual("GET", seen[0].method)

    def test_filename_normalization(self):
        self.assertEqual("my photo.jpg", photo.normalized_filename("https://x.test/My%20Photo-300x200-scaled.jpg?x=1#z"))
        self.assertEqual("abc.png", photo.normalized_filename("https://web.archive.org/web/20230101000000im_/https://x.test/a/ABC-1024x768.png"))

    def test_duplicate_filename_is_not_auto_matched(self):
        media = [
            {"id": 1, "source_url": "https://tsurikue.com/wp-content/uploads/2023/01/a.jpg"},
            {"id": 2, "source_url": "https://tsurikue.com/wp-content/uploads/2023/02/a-300x200.jpg"},
        ]
        self.assertIsNone(photo.filename_match("https://old/a.jpg", media))

    def test_hash_classification_boundaries(self):
        self.assertEqual("MATCH_HASH_STRONG", photo.classify_hash_distances([2, 8]))
        self.assertEqual("CANDIDATE_HASH", photo.classify_hash_distances([4, 6]))
        self.assertEqual("CANDIDATE_HASH", photo.classify_hash_distances([10, 20]))
        self.assertEqual("PLACEHOLDER", photo.classify_hash_distances([20, 24]))

    def test_parser_excludes_noise_and_captures_context(self):
        html = b'''<html><body><article><div class="post_content"><h2>Heading</h2><p>before text</p>
        <img src="https://tsurikue.com/wp-content/uploads/2023/01/good.jpg" width="800" height="600">
        <p>after text</p><img src="https://x.test/facebook-icon.png"><img src="https://x.test/pixel.gif" width="1" height="1">
        </div></article></body></html>'''
        images = photo.extract_images(html, "https://web.archive.org/web/20230101000000/https://tsurikue.com/x/")
        self.assertEqual(1, len(images))
        self.assertEqual("Heading", images[0].nearest_heading)
        self.assertEqual("before text", images[0].context_before)
        self.assertEqual("after text", images[0].context_after)

    def test_archive_failure_never_guesses(self):
        with mock.patch.object(photo, "get_bytes", side_effect=OSError("offline")):
            ok, rows = photo.reconcile_one("x", ["https://web.archive.org/web/1/https://tsurikue.com/x/"], [])
        self.assertFalse(ok)
        self.assertEqual("ARCHIVE_UNAVAILABLE", rows[0]["result"])
        self.assertIsNone(rows[0]["matched_media_id"])

    def test_artifacts_record_zero_wordpress_writes(self):
        report = {
            "mode": "authenticated-photo-reconciliation-dry-run", "targets": 46, "lexus_targets": 0,
            "live_media_count": 2113, "archive_articles_ok": 46, "archive_articles_failed": 0,
            "archive_image_refs": 1, "MATCH_FILENAME": 1, "MATCH_HASH_STRONG": 0,
            "CANDIDATE_HASH": 0, "PLACEHOLDER": 0, "ARCHIVE_UNAVAILABLE": 0,
            "wordpress_write_count": 0,
            "results": [photo.blank_row("x", "https://web.archive.org/x", "MATCH_FILENAME", "test")],
        }
        report["results"][0]["image_order"] = 1
        report["results"][0]["legacy_filename"] = "a.jpg"
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            photo.write_artifacts(out, report)
            saved = json.loads((out / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(0, saved["wordpress_write_count"])
            self.assertTrue((out / "result.csv").exists())
            self.assertTrue((out / "result.md").exists())


if __name__ == "__main__":
    unittest.main()
