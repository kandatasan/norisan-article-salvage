"""Regression tests for minimal owner-voice LBX cheap update and Nov 2026 official prices."""
import unittest
from unittest.mock import patch
from scripts import revise_lbx_cheap_light_20261114 as m

def unit(item,idx):
    before,_=item
    if idx==3:
        return "<!-- wp:table -->\n"+before+"\n<!-- /wp:table -->"
    return "<!-- wp:paragraph -->\n"+before+"\n<!-- /wp:paragraph -->"

class LBXCheapLightTests(unittest.TestCase):
    def setUp(self):
        self.source=(
          '<!-- tsurikue-original:v1 slug=lexus-lbx-cheap source=editorial-revenue-design-20260920 -->\n'
          '<!-- tsurikue-editorial:v1 slug=lexus-lbx-cheap -->\n'
          +'\n\n'.join(unit(item,i) for i,item in enumerate(m.CHANGES))
          +'\n<!-- wp:heading --><h2>方法1｜本人の体験</h2><!-- /wp:heading -->'
          +'\n<!-- wp:list --><ul><li>探す</li></ul><!-- /wp:list -->'
          +'\n<!-- wp:shortcode -->\n[blog_parts id="4521"]\n<!-- /wp:shortcode -->'
          +'\n<!-- wp:loos/button {"color":"green","isCount":true} -->'
          +'\n<div class="swell-block-button -html green_" data-id="gu3863-01"><a href="https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY" rel="nofollow">中古を探す</a>'
          +'<img src="https://www13.a8.net/0.gif?a8mat=4B65SD+8DUSHE+9QU+NVHCY" alt=""></div>\n<!-- /wp:loos/button -->'
          +'\n<!-- wp:loos/button {"color":"green","isCount":true} -->'
          +'\n<div class="swell-block-button -html green_" data-id="gu3863-02"><a href="https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY" rel="nofollow">中古を探す</a>'
          +'<img src="https://www13.a8.net/0.gif?a8mat=4B65SD+8DUSHE+9QU+NVHCY" alt=""></div>\n<!-- /wp:loos/button -->'
          +'\n<!-- wp:paragraph -->\n<p>私はシエンタを売りました。サドルタンが欲しい。30件ほど着信。カーセブンへ427万円で売却。25万6,300円。</p>\n<!-- /wp:paragraph -->'
        )
    def transform(self,source=None):
        source=self.source if source is None else source
        with patch.object(m,'SOURCE_SHA',m.digest(source)):
            return m.transform(source)
    def test_source_exactly_recoverable(self):
        result=self.transform()
        self.assertIn(m.MARKER,result)
        recovered=result.replace('\n'+m.MARKER,'',1)
        for old,new in reversed(m.CHANGES):
            self.assertEqual(recovered.count(new),1)
            recovered=recovered.replace(new,old,1)
        self.assertEqual(recovered,self.source)
    def test_no_change_to_buttons_ctn_headings_lists(self):
        result=self.transform()
        a,b=m.signature(self.source),m.signature(result)
        for field in ('headings','lists','images','buttons','shortcodes','paragraphs','tables','gulliver_counted','gulliver_click_ids','original_emotional_reactions'):
            self.assertEqual(a[field],b[field],field)
        self.assertEqual(result.count('[blog_parts id="4521"]'),1)
        self.assertEqual(result.count('data-id="gu3863-01"'),1)
        self.assertEqual(result.count('data-id="gu3863-02"'),1)
    def test_new_prices_from_official_release(self):
        result=self.transform()
        for price in ('4,450,000円','4,650,000円','4,820,000円','5,670,000円'):
            self.assertIn(price,result)
        self.assertIn('37万円',result)
        self.assertIn('改良前のRelax',result)
        self.assertIn(m.NEWS,result)
    def test_owners_older_256300_quote_not_recast_as_current(self):
        result=self.transform()
        self.assertIn('改良前の見積もり',result)
        self.assertIn('25万6,300円',result)
        self.assertIn('485万6,300円',result)
        self.assertIn('シエンタ',result)
        self.assertIn('サドルタン',result)
    def test_refuse_unapproved_live_edits(self):
        with self.assertRaisesRegex(RuntimeError,'changed since source audit'):
            m.transform(self.source)
    def test_refuse_missing_anchor(self):
        source=self.source.replace(m.CHANGES[1][0],m.P('金額未定'))
        with self.assertRaisesRegex(RuntimeError,'expected unique'):
            self.transform(source)
    def test_idempotent_after_full_edit(self):
        first=self.transform()
        self.assertEqual(m.transform(first),first)
    def test_exact_count_no_fabricated_extra_sections(self):
        self.assertLessEqual(len(m.CHANGES),17)
        self.assertEqual(len(m.CHANGES),15)

if __name__=='__main__':
    unittest.main()
