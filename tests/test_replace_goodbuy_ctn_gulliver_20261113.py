"""Only replace the two legacy Gulliver ad locations; preserve actual UX evidence."""
import unittest
from unittest.mock import patch
from scripts import replace_goodbuy_ctn_gulliver_outlets_20261113 as m

def para(body):
    return '<!-- wp:paragraph -->\n<p>'+body+'</p>\n<!-- /wp:paragraph -->'

def heading(body):
    return '<!-- wp:heading -->\n<h2>'+body+'</h2>\n<!-- /wp:heading -->'

def shortcode(part):
    return '<!-- wp:shortcode -->\n[blog_parts id="'+str(part)+'"]\n<!-- /wp:shortcode -->'

class GoodbuyNewExitTests(unittest.TestCase):
    def setUp(self):
        self.old_top='<!-- wp:html -->\n<div class="tsq-gulliver-micro-20261014 top" style="text-align:center;">昔の上コピー</div>\n<!-- /wp:html -->'
        self.old_bottom='<!-- wp:html -->\n<div class="tsq-gulliver-micro-20261014 bottom" style="text-align:center;">昔の下コピー</div>\n<!-- /wp:html -->'
        self.source='\n\n'.join([
            para('616万円のレクサスUX、シエンタ売却では25万円の差！'),
            shortcode(4521),
            heading('方法4｜不要なオプションは外す。でも欲しい装備まで削らない'),
            para('三眼LED、ムーンルーフはそのまま'),
            shortcode(2843),
            heading('方法5｜新車が予算を超えるなら、中古・CPOまで広げる'),
            para('レクサスの中古探しは面白い。'),
            self.old_top,shortcode(4172),self.old_bottom,
            heading('レクサスを安く買う方法は「一番安い仕様を選ぶ」ことじゃない'),
            para('UX買い替えの真実は見積もりで。'),
            '<!-- wp:table --><figure><table></table></figure><!-- /wp:table -->',
            '<!-- wp:image {"id":2231} --><img class="wp-image-2231"/><!-- /wp:image -->',
            '<!-- wp:list --><ul><li>絶対ほしい</li></ul><!-- /wp:list -->',
        ])
    def run_transform(self,body=None):
        body=self.source if body is None else body
        with patch.object(m,'CONTENT_SHA',m.sha(body)):
            return m.transform(body)

    def test_replaces_legacy_gulliver_but_preserves_current_ctn(self):
        result=self.run_transform()
        self.assertEqual(result.count('[blog_parts id="4521"]'),1)
        self.assertEqual(result.count('[blog_parts id="4507"]'),1)
        self.assertNotIn('[blog_parts id="2843"]',result)
        self.assertNotIn('[blog_parts id="4172"]',result)
        self.assertLess(result.index(m.BANNER_MARKER),result.index(m.FUNNEL_MARKER))
        self.assertEqual(m.protected(self.source)['original_paragraph_blocks'],
                         m.protected(result)['original_paragraph_blocks'])
        self.assertEqual(m.protected(self.source)['headings'],m.protected(result)['headings'])

    def test_changes_reversible_exact_to_original(self):
        result=self.run_transform()
        old_funnel=self.old_top+'\n\n'+shortcode(4172)+'\n\n'+self.old_bottom
        original=result.replace(m.BANNER_MARKER,shortcode(2843),1).replace(m.NEW_FUNNEL,old_funnel,1)
        self.assertEqual(original,self.source)

    def test_guard_refuses_changed_live_content(self):
        with self.assertRaisesRegex(RuntimeError,'drifted'):
            m.transform(self.source)

    def test_guard_refuses_duplicated_old_banner(self):
        data=self.source.replace(shortcode(2843),shortcode(2843)+'\n\n'+shortcode(2843))
        with self.assertRaisesRegex(RuntimeError,'not uniquely'):
            self.run_transform(data)

    def test_idempotence_after_both_changes(self):
        new=self.run_transform()
        self.assertEqual(m.transform(new),new)

    def test_guard_does_not_remove_personal_story_paragraphs(self):
        res=self.run_transform()
        self.assertIn('シエンタ売却では25万円の差',res)
        self.assertIn('三眼LED、ムーンルーフはそのまま',res)

if __name__=="__main__":
    unittest.main()
