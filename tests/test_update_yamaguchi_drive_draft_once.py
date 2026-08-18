import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).parents[1] / "scripts" / "update_yamaguchi_drive_draft_once.py"
spec = importlib.util.spec_from_file_location("target", SCRIPT)
target = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(target)


class YamaguchiDriveDraftUpdateTests(unittest.TestCase):
    def test_scope_is_exact_single_draft(self):
        self.assertEqual(target.POST_ID, 2664)
        self.assertEqual(target.SLUG, "yamaguchi-drive")
        self.assertEqual(target.build_payload()["status"], "draft")
        self.assertEqual(set(target.build_payload()), {"title", "slug", "content", "status"})

    def test_markers_and_title_are_present(self):
        self.assertIn(target.SALVAGE_MARKER, target.full_content())
        self.assertIn(target.EDITORIAL_MARKER, target.full_content())
        self.assertIn(target.TITLE, target.article_content())

    def test_only_confirmed_media_are_used(self):
        content = target.article_content()
        self.assertEqual(len(target.EXPECTED_MEDIA), 10)
        for media_id, path in target.EXPECTED_MEDIA.items():
            self.assertIn(f'"id":{media_id}', content)
            self.assertIn(path, content)

    def test_links_and_voice(self):
        content = target.article_content()
        for url in (
            "https://tsurikue.com/muvalley/", "https://tsurikue.com/motonosumi/",
            "https://tsurikue.com/kulabotaisyoukan/", "https://tsurikue.com/tsunoshima/",
            "https://nanavi.jp/news/32692/", "https://www.karatoichiba.com/calendars/",
            "https://www.kaikyokan.com/cms/20250801open/",
        ):
            self.assertIn(url, content)
        for phrase in ("欲張りですね", "説得力なし！", "遊びすぎですね", "旅行なんだから、それでいい！"):
            self.assertIn(phrase, content)

    def test_no_placeholder_or_lexus_content(self):
        content = target.article_content()
        self.assertNotIn("【写真差し込み】", content)
        self.assertNotIn("lexus-diary.com", content.lower())


if __name__ == "__main__":
    unittest.main()
