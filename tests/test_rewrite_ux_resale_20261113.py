"""Regression tests for verifiable UX resale story editing."""
import unittest
from scripts import rewrite_ux_resale_20261113 as m


class VerifiedUxResaleTests(unittest.TestCase):
    def test_ratio_from_total_is_69_3_percent(self):
        self.assertEqual(round(427/616*100,1),69.3)

    def test_guard_refuses_unknown_live_content(self):
        with self.assertRaisesRegex(RuntimeError,'SHA drift'):
            m.transform('<!-- wp:paragraph --><p>somebody edited this</p><!-- /wp:paragraph -->')

    def test_replace_only_unique_paragraph_and_preserve_unrelated_links(self):
        source=(m.p('今はUXのリセールについて。')+'\n\n'
                +m.p('<a href="https://tsurikue.com/ux-mitsumori/">見積もりはこちら</a>'))
        result=m.replace_paragraph(source,'今はUXのリセール','同じ話の途中。<br>このあと。')
        self.assertIn('同じ話の途中。<br>このあと。',result)
        self.assertIn('https://tsurikue.com/ux-mitsumori/',result)
        self.assertEqual(result.count('<!-- wp:paragraph'),2)

    def test_stop_on_duplicate_anchor(self):
        source=m.p('確認する。')+'\n\n'+m.p('確認する。')
        with self.assertRaisesRegex(RuntimeError,'must be unique'):
            m.replace_paragraph(source,'確認する','別の話。')

    def test_add_new_heading_without_overwriting_other_heading(self):
        source=m.h2('その前の見出し')+'\n\n'+m.h2('リセールで学んだこと')
        result=m.insert_before_heading(source,'リセールで学んだこと',m.h2('2026年11月現在の相場'))
        self.assertEqual(result.count('<!-- wp:heading'),3)
        self.assertLess(result.index('2026年11月現在の相場'),result.index('リセールで学んだこと'))

    def test_affiliate_and_media_signature(self):
        source=m.p('確認')+'<!-- wp:image {"id":55} --><img class="wp-image-55"/><!-- /wp:image -->'+m.p('[blog_parts id="4521"]')
        info=m.protected_signature(source)
        self.assertEqual(info['images'],['wp-image-55'])
        self.assertEqual(info['image_blocks'],1)
        self.assertEqual(info['shortcode'],['[blog_parts id="4521"]'])

    def test_no_synthetic_dramatic_conversation(self):
        src=open('scripts/rewrite_ux_resale_20261113.py',encoding='utf-8').read()
        self.assertIn('2025年2月にカーセブンと競り合って出た最終提示額ではありません',src)
        self.assertNotIn('他社の現地査定を断ろうと思う',src)


if __name__=='__main__':
    unittest.main()
