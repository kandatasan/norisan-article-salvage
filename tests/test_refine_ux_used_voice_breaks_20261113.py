import hashlib
import unittest
from unittest.mock import patch
from scripts import refine_ux_used_voice_breaks_20261113 as m


class UxUsedVoiceBreakTests(unittest.TestCase):
    def test_source_drift_halts_before_any_change(self):
        with self.assertRaisesRegex(RuntimeError,"SHA drift"):
            m.transform("<p>edited by someone</p>")

    def test_merge_adjacent_paragraphs_preserves_emphasis(self):
        source=m.p("前半の話。")+"\n\n"+m.p("後半も同じ話。<strong>大事。</strong>")
        updated=m.merge(source,["前半の話。","後半も同じ話。"])
        self.assertEqual(updated.count("<!-- wp:paragraph"),1)
        self.assertIn("前半の話。<br>後半も同じ話。",updated)
        self.assertIn("<strong>大事。</strong>",updated)

    def test_merge_refuses_to_cross_images_or_headings(self):
        source=m.p("説明の続き。")+"\n\n<!-- wp:image -->\n<figure>写真</figure>\n<!-- /wp:image -->\n\n"+m.p("あとから続く説明。")
        with self.assertRaisesRegex(RuntimeError,"Refusing to merge"):
            m.merge(source,["説明の続き。","あとから続く説明。"])

    def test_soft_break_keeps_html_tags_and_existing_breaks(self):
        original="はじめの文。次の文。<br>最後。"
        output=m.sentence_breaks(original)
        self.assertEqual(output,"はじめの文。<br>次の文。<br>最後。")
        self.assertEqual(m.sentence_breaks(output),output)

    def test_paragraph_classes_preserved(self):
        original='<!-- wp:paragraph {"className":"special"} -->\n<p class="special">ひとつめ。ふたつめ。</p>\n<!-- /wp:paragraph -->'
        output=m.normalize_plain_paragraphs(original)
        self.assertIn('{"className":"special"}',output)
        self.assertIn('<p class="special">',output)
        self.assertIn("ひとつめ。<br>ふたつめ。",output)


if __name__=="__main__":
    unittest.main()
