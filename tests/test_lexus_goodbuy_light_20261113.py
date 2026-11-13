import unittest
from unittest.mock import patch
from scripts import lexus_goodbuy_light_20261113 as m


class GoodbuySmallEditTests(unittest.TestCase):
    def setUp(self):
        self.original = "\n\n".join([
            '<!-- wp:paragraph -->\n'+m.CHANGES[0][0]+'\n<!-- /wp:paragraph -->',
            '<!-- wp:paragraph -->\n'+m.CHANGES[1][0]+'\n<!-- /wp:paragraph -->',
            '<!-- wp:paragraph -->\n<p>私はシエンタからUXへ。三眼フルLEDと装備合計27万5,000円。友人も値引きなし。</p>\n<!-- /wp:paragraph -->',
            '<!-- wp:paragraph -->\n<p>月5,000円なら年間6万円。5年なら30万円です。</p>\n<!-- /wp:paragraph -->',
            '<!-- wp:paragraph -->\n'+m.CHANGES[2][0]+'\n<!-- /wp:paragraph -->',
            '<!-- wp:shortcode -->\n[blog_parts id="4521"]\n<!-- /wp:shortcode -->',
            '<!-- wp:table --><figure><table><tbody><tr><td>内容</td></tr></tbody></table></figure><!-- /wp:table -->',
            '<!-- wp:image {"id":22} --><figure><img class="wp-image-22"/></figure><!-- /wp:image -->',
            '<!-- wp:heading --><h2>実録</h2><!-- /wp:heading -->',
            '<!-- wp:html --><p><a href="https://example.com/">original link</a></p><!-- /wp:html -->',
        ])

    def transform(self, original=None):
        original=self.original if original is None else original
        with patch.object(m,'SOURCE_SHA',m.sha(original)):
            return m.transform(original)

    def test_only_three_paragraphs_changed(self):
        updated=self.transform()
        self.assertEqual(updated.count('<!-- wp:paragraph'),self.original.count('<!-- wp:paragraph'))
        self.assertEqual(m.signature(updated),m.signature(self.original))
        self.assertIn('2％なら利息約15.5万円、4％なら約31.5万円',updated)
        self.assertIn('保険は車両価格の値引きではありません',updated)
        self.assertNotIn('私の例と同じ月5,000円差なら',updated)
        self.assertIn('月5,000円なら年間6万円。5年なら30万円',updated)

    def test_reversible_original_exact(self):
        updated=self.transform()
        unmarked=updated.replace(m.MARKER+'\n','',1)
        for old,new in m.CHANGES:
            self.assertEqual(unmarked.count(new),1)
            unmarked=unmarked.replace(new,old,1)
        self.assertEqual(unmarked,self.original)

    def test_reject_concurrent_edit(self):
        with self.assertRaisesRegex(RuntimeError,'no longer matches'):
            m.transform(self.original)

    def test_must_find_each_exact_paragraph(self):
        changed=self.original.replace(m.CHANGES[0][0],'<p>Other loan text</p>',1)
        with self.assertRaisesRegex(RuntimeError,'Expected exactly one target'):
            self.transform(changed)

    def test_idempotent(self):
        revised=self.transform()
        self.assertEqual(m.transform(revised),revised)

    def test_loan_example_math(self):
        def total(amount,annual,months):
            m_rate=annual/12
            return amount * (m_rate/(1-(1+m_rate)**(-months))) * months
        self.assertAlmostEqual(total(3_000_000,.02,60),3_154_997,delta=3)
        self.assertAlmostEqual(total(3_000_000,.04,60),3_314_974,delta=3)
        self.assertAlmostEqual(total(3_000_000,.04,60)-total(3_000_000,.02,60),159_977,delta=3)

if __name__=='__main__':
    unittest.main()
