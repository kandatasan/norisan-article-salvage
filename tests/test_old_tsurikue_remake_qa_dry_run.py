import difflib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import old_tsurikue_remake_dry_run as phase3
import old_tsurikue_remake_qa_dry_run as qa


class RemakeQADryRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.phase3_dir = root / "phase3"
        cls.qa_dir = root / "phase31"
        cls.phase3_report = phase3.build(cls.phase3_dir)
        cls.baseline = qa.validate_phase3_baseline(cls.phase3_dir, cls.phase3_report)
        cls.report = qa.build(cls.qa_dir)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def article(self, slug):
        return json.loads(
            (self.qa_dir / "articles" / f"{slug}.json").read_text(encoding="utf-8")
        )

    def test_formal_phase3_baseline_gate(self):
        self.assertEqual(len(self.baseline), 46)
        self.assertEqual(
            sum(qa.visible_chars(a["content"]) < 800 for a in self.baseline), 11
        )
        self.assertEqual(self.phase3_report["summary"]["matched_images_used"], 110)
        self.assertEqual(self.phase3_report["summary"]["placeholders_used"], 29)
        self.assertEqual(self.phase3_report["summary"]["unmatched_photos_omitted"], 224)

    def test_phase31_scope_images_and_writes(self):
        s = self.report["summary"]
        self.assertEqual(s["targets"], 46)
        self.assertEqual(s["lexus_targets"], 0)
        self.assertEqual(s["articles_generated"], 46)
        self.assertEqual(s["matched_images_used"], 110)
        self.assertEqual(s["placeholders_used"], 29)
        self.assertEqual(s["unmatched_photos_omitted"], 224)
        self.assertEqual(s["wordpress_write_count"], 0)
        self.assertEqual(s["draft_creation_count"], 0)
        self.assertEqual(s["media_upload_count"], 0)

    def test_short_article_baseline_does_not_regress(self):
        s = self.report["summary"]
        self.assertEqual(s["short_articles_under_800_before"], 11)
        self.assertEqual(s["short_articles_under_800_after"], 11)
        self.assertEqual(s["newly_under_800"], 0)
        self.assertEqual(s["articles_reduced_50pct_or_more"], 0)
        for row in self.report["qa"]:
            self.assertLess(row["reduction_ratio"], 0.50)

    def test_known_join_and_text_fixes(self):
        gulp = self.article("gulp-powder")["content"]
        self.assertEqual(gulp.count("強烈な匂いと釣果で、最強集魚剤"), 1)
        self.assertNotIn("楽天だとここが安かった", gulp)

        totaya = self.article("totoya-iiyo")["content"]
        self.assertEqual(totaya.count("私が利用したのは、二名一室の和室タイプでした"), 1)

        matthew = self.article("matthewoishii")["content"]
        self.assertNotIn(">メニューは日替わり系も豊</h", matthew)
        self.assertIn("メニューは日替わり系も豊富！", matthew)

        ramen = self.article("ramenkou")["content"]
        self.assertNotIn("デカデカ」と", ramen)
        self.assertIn("デカデカと", ramen)

        yari = self.article("yariika-fishing")["content"]
        self.assertIn("0.6〜0.8号", yari)
        self.assertNotIn("0.6〜08号", yari)
        self.assertIn("この2点を意識して探してみましょう", yari)
        self.assertIn("猪突猛進な性格", yari)

        ymg = self.article("yamaguchi-drive")["content"]
        self.assertNotIn("作成中です", ymg)

    def test_affiliate_cleanup_preserves_firsthand_text(self):
        sabiki = self.article("sabiki-beginner")["content"]
        self.assertNotIn("このブログにはPRが含まれています", sabiki)
        self.assertIn("テキトーな事は書きたくない", sabiki)
        gopro = self.article("gopro-jidoribou")["content"]
        self.assertNotRegex(gopro, r"価格[:：]\s*[\d,]+円.*時点.*感想\(")

    def test_operational_info_is_reframed_locally(self):
        matthew = self.article("matthewoishii")["content"]
        self.assertIn("訪問当時の定休日：月曜日", matthew)
        self.assertIn("訪問当時の営業時間", matthew)
        self.assertIn("訪問当時の電話番号", matthew)
        self.assertIn(qa.GENERIC_STALE_NOTICE, matthew)

    def test_no_high_similarity_paragraph_duplicates_remain(self):
        for path in (self.qa_dir / "articles").glob("*.json"):
            article = json.loads(path.read_text(encoding="utf-8"))
            seen = []
            for block in qa.split_blocks(article["content"]):
                if qa.block_type(block) != "paragraph":
                    continue
                current = qa.normalize_compare(qa.block_text(block))
                if len(current) < 50:
                    continue
                for previous in seen:
                    ratio = difflib.SequenceMatcher(None, current, previous).ratio()
                    self.assertLess(
                        ratio,
                        0.94,
                        f"{article['slug']} still has a {ratio:.3f} near-duplicate paragraph",
                    )
                seen.append(current)

    def test_artifacts_and_article_level_metrics_exist(self):
        for name in (
            "index.json",
            "index.csv",
            "summary.md",
            "qa-report.json",
            "qa-report.md",
        ):
            self.assertTrue((self.qa_dir / name).exists(), name)
        self.assertEqual(len(list((self.qa_dir / "articles").glob("*.html"))), 46)
        self.assertEqual(len(list((self.qa_dir / "articles").glob("*.json"))), 46)
        for row in self.report["qa"]:
            self.assertIn("visible_chars_before", row)
            self.assertIn("visible_chars_after", row)
            self.assertIn("reduction_ratio", row)
            self.assertIn("deleted_blocks_by_reason", row)
            self.assertIn("deleted_chars_by_reason", row)


if __name__ == "__main__":
    unittest.main()
