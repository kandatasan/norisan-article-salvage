import hashlib
import unittest
from unittest.mock import patch
from pathlib import Path

from scripts import rewrite_ux_used_20261113 as m


def paragraph(s):
    return '<!-- wp:paragraph -->\n<p>' + s + '</p>\n<!-- /wp:paragraph -->'


def heading(s):
    return '<!-- wp:heading -->\n<h2 class="wp-block-heading">' + s + '</h2>\n<!-- /wp:heading -->'


class RewriteUxUsed(unittest.TestCase):
    def test_drift_is_blocked(self):
        with self.assertRaisesRegex(RuntimeError, "Source content changed"):
            m.transform("some future editor content", "new CTA")

    def test_exact_scoped_rewrite_and_idempotence(self):
        first = paragraph('<strong>UX250h F SPORTが車両本体199.6万円。</strong>')
        intros = first + '\n\n' + '\n\n'.join(paragraph('original intro ' + str(i)) for i in range(5))
        source = '\n\n'.join([
            '<p><!-- lexus-salvage:v1 slug=lexus-ux-used --></p>',
            intros,
            '<!-- wp:image {"id":2587,"sizeSlug":"large","linkDestination":"none"} -->\n<figure><img class="wp-image-2587" src="https://tsurikue.com/original.jpg"/></figure>\n<!-- /wp:image -->',
            heading('結論｜中古UXは今「最強個体を探す」のが面白い'),
            paragraph('私は616万円でUXを買いました。<br>それを知っているからこそ、支払総額200万円台のF SPORTを見ると「いや、これ満足度高いだろ」と思います。'),
            '<!-- tsurikue-ux-purchase-funnel:lexus-ux-used:20261111 -->\n[blog_parts id="4505"]\nガリバーで希望のUXを探してみる',
            heading('中古UXの「最強」は3つある'),
            paragraph('私なら中古UXを「一番安い1台」では選びません。<br>何を優先するかで、最強は変わります。'),
            '<table><tr><td><strong>コスパ最強</strong></td><td><strong>完成度最強</strong></td><td><strong>安心最強</strong></td></tr></table>',
            heading('安い中古車を見るときの注意点'),
            paragraph('そして乗り換えなら、買う車だけでなく<strong>今の車がいくらで売れるか</strong>も先に確認しておきたいところです。'),
            '<!-- tsurikue-ctn-used-funnel:20260917-treasure -->',
            paragraph('私がUXへ乗り換えたときは25万円差。'),
            '<!-- wp:shortcode -->\n[blog_parts id="4521"]\n<!-- /wp:shortcode -->',
            heading('まとめ｜200万円台のUXは「安いレクサス」じゃなく宝探し'),
            paragraph('私は新車でUXを買って良かったです。'),
            '<!-- wp:html -->\n<div class="tsq-gulliver-micro-20261014 top">買ったあとも好きでいられる</div>\n<!-- /wp:html -->',
            paragraph('ガリバーで中古のレクサスUXを探してみる'),
            '<!-- wp:html -->\n<div class="tsq-gulliver-micro-20261014 bottom">自分に合う一台</div>\n<!-- /wp:html -->',
            '<!-- tq-lexus-related-cards:v1:lexus-ux-used -->',
            '<!-- tq-lexus-related-cards:v1:end -->',
            '<!-- tsurikue-goodbuy-hub-link:20260920 -->',
        ])
        funnel = Path('editorial/ux-purchase-funnel-wave1-20261111/funnel-4507.html').read_text(encoding='utf-8').strip()
        with patch.object(m, 'EXPECTED_SHA', hashlib.sha256(source.encode()).hexdigest()):
            updated = m.transform(source, funnel)
            self.assertEqual(updated, m.transform(updated, funnel))
        self.assertIn('300万円台までで', updated)
        self.assertIn('三眼LEDとムーンルーフが実質無料', updated)
        self.assertIn('電話ラッシュ', updated)
        self.assertIn('改良後の装備重視', updated)
        self.assertEqual(updated.count('[blog_parts id="4521"]'), 1)
        self.assertEqual(updated.count('[blog_parts id="4505"]'), 1)
        self.assertEqual(updated.count('ガリバーで希望のUXを探してみる'), 2)
        self.assertNotIn('ガリバーで中古のレクサスUXを探してみる', updated)
        self.assertIn('wp-image-2587', updated)
        self.assertIn('<!-- tq-lexus-related-cards:v1:lexus-ux-used -->', updated)
        self.assertIn('<!-- tsurikue-goodbuy-hub-link:20260920 -->', updated)
        self.assertEqual(updated.count('<!-- wp:heading'), source.count('<!-- wp:heading') + 2)


if __name__ == '__main__':
    unittest.main()
