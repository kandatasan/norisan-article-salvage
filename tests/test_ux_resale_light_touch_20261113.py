"""Regression tests: UX resale original prose must be byte-identical after removing additions."""
import re
import unittest
from unittest.mock import patch
from scripts import add_ux_resale_light_touch_20261113 as m


def block(text):
    return "<!-- wp:paragraph -->\n<p>" + text + "</p>\n<!-- /wp:paragraph -->"


class UXResaleLightTouchTests(unittest.TestCase):
    def setUp(self):
        self.original = "\n\n".join([
            block("350万円、500万円前後、430万円、435万円は査定時の提示額。実際に売却した金額は427万円です。"),
            block("なお、購入額616万円の見積もり内訳にはオプションや諸費用も含まれます。616万円と427万円の差を、そのまま車両本体の値下がりとして見ることはできません。"),
            '<!-- wp:image {"id":2234} --><figure><img class="wp-image-2234" /></figure><!-- /wp:image -->',
            '<!-- wp:heading -->\n<h2>生活のために売却</h2>\n<!-- /wp:heading -->',
            block("CTNは条件に合う買取店を選び、やり取りは<strong>最大3社</strong>。<br>私が利用したときに連絡が来たのは、カーセブンとネクステージの2社でした。"),
            block("2社とも電話だけで金額を決めたわけではありません。<br>実際にUXを見てもらいました。"),
            '<!-- wp:shortcode -->\n[blog_parts id="4521"]\n<!-- /wp:shortcode -->',
            '<!-- wp:list -->\n<ul class="wp-block-list"><!-- wp:list-item --><li>現場の話</li><!-- /wp:list-item --></ul>\n<!-- /wp:list -->',
        ])

    def changed(self, body=None):
        body = self.original if body is None else body
        with patch.object(m, 'EXPECTED_SHA256', m.digest(body)):
            return m.transform(body)

    def test_only_one_compact_list_and_two_phone_paragraphs(self):
        updated=self.changed()
        self.assertEqual(updated.count('<!-- wp:paragraph'),self.original.count('<!-- wp:paragraph')+2)
        self.assertEqual(updated.count('<!-- wp:heading'),self.original.count('<!-- wp:heading'))
        self.assertEqual(len(re.findall(r'<!-- wp:list(?:\s|>)',updated)),
                         len(re.findall(r'<!-- wp:list(?:\s|>)',self.original))+1)
        self.assertEqual(updated.count('<!-- wp:list-item'),self.original.count('<!-- wp:list-item')+4)
        self.assertEqual(updated.count('<!-- wp:image'),self.original.count('<!-- wp:image'))
        self.assertEqual(updated.count('[blog_parts id="4521"]'),1)
        self.assertTrue(updated.find(m.MARKER_STATS)<updated.find('なお、購入額'))
        self.assertTrue(updated.find(m.MARKER_CALLS)<updated.find('2社とも電話だけで'))

    def test_original_prose_is_exactly_unchanged(self):
        updated=self.changed()
        restored=updated.replace('\n\n'+m.MARKER_STATS+'\n'+m.STATS,'',1).replace(
            '\n\n'+m.MARKER_CALLS+'\n'+m.CALLS,'',1)
        self.assertEqual(restored,self.original)

    def test_refuse_unexpected_live_text(self):
        with self.assertRaisesRegex(RuntimeError,'differs from reverted original'):
            m.transform(self.original)

    def test_duplicate_anchor_blocks(self):
        body=self.original+"\n\n"+block("350万円、500万円前後、430万円、435万円は査定時の提示額。")
        with self.assertRaisesRegex(RuntimeError,'Expected one paragraph'):
            self.changed(body)

    def test_unexpected_intervening_content_blocks(self):
        body=self.original.replace(
            block("2社とも電話だけで金額を決めたわけではありません。<br>実際にUXを見てもらいました。"),
            '<!-- wp:separator --><hr /><!-- /wp:separator -->'+
            block("2社とも電話だけで金額を決めたわけではありません。<br>実際にUXを見てもらいました.")
        )
        with self.assertRaisesRegex(RuntimeError,'Expected one paragraph|Unexpected content'):
            self.changed(body)

    def test_idempotence_with_both_markers(self):
        updated=self.changed()
        self.assertEqual(m.transform(updated),updated)

    def test_69_3_percent_is_purchase_total_ratio(self):
        self.assertAlmostEqual(427 / 616 * 100, 69.31818,places=4)
        self.assertIn('オプション・諸費用込み',m.STATS)
        self.assertIn('購入総額に対する残価率',m.STATS)


if __name__=="__main__":
    unittest.main()
