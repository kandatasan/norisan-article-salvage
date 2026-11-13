"""Regression of Gutenberg/A8 direct-copy migration for per-article SWELL counts."""
import unittest
from scripts import migrate_all_gulliver_native_counted_20261113 as m

A8=m.URL
IMG='<img border="0" width="1" height="1" src="https://www13.a8.net/0.gif?a8mat='+m.A8+'" alt="">'
A='<a href="'+A8+'" rel="nofollow">ガリバーで希望のUXを探してみる</a>'
TEMPLATE='''<!-- wp:loos/button {"color":"green","className":"is-style-btn_solid u-mb-ctrl u-mb-5"} -->
<div class="swell-block-button -html green_ is-style-btn_solid u-mb-ctrl u-mb-5">'''+A+'\n'+IMG+'''</div>
<!-- /wp:loos/button -->'''
FUNNEL='''<!-- wp:paragraph -->
<p>中古相場を見る</p>
<!-- /wp:paragraph -->

'''+TEMPLATE

def shortcode(pid):
    return '<!-- wp:shortcode -->\n[blog_parts id="'+str(pid)+'"]\n<!-- /wp:shortcode -->'

def para(txt):
    return '<!-- wp:paragraph -->\n<p>'+txt+'</p>\n<!-- /wp:paragraph -->'

def micro(place,txt):
    return '<!-- wp:html -->\n<div class="tsq-gulliver-micro-20261014 '+place+'"><span>'+txt+'</span></div>\n<!-- /wp:html -->'

def outcome(pid,slug,body):
    return m.transformed(pid,slug,body,TEMPLATE,FUNNEL)


class GulliverCountedTests(unittest.TestCase):
    def test_source_button_preserves_affiliate_href_and_pixel(self):
        item=m.copy_button(TEMPLATE,'gu111-01','ガリバーで中古SUVを探してみる')
        self.assertIn('"isCount":true',item)
        self.assertIn('data-id="gu111-01"',item)
        self.assertIn(A8,item)
        self.assertIn(IMG,item)
        self.assertIn('ガリバーで中古SUVを探してみる',item)
        self.assertEqual(item.count(m.A8),2)

    def test_legacy_shortcode_substitution_is_only_change(self):
        source=para('シエンタの25万円差。')+'\n\n'+shortcode(2843)+'\n\n'+para('写真も話も残す。')
        output,edits=outcome(991,'lexus-ux-price',source)
        self.assertEqual(len(edits),1)
        self.assertIn('ガリバーで希望のUXを探してみる',output)
        self.assertNotIn('[blog_parts id="2843"]',output)
        self.assertIn(para('シエンタの25万円差。'),output)
        self.assertIn(para('写真も話も残す。'),output)

    def test_two_swells_have_unique_count_ids(self):
        source=shortcode(4172)+'\n\n'+para('これは元の本文です')+'\n\n'+shortcode(2843)
        output,edits=outcome(999,'tanto-used-best-year',source)
        self.assertEqual(len(edits),2)
        self.assertEqual(len(set(__import__('re').findall(r'data-id="([^"]+)"',output))),2)
        self.assertEqual(output.count('"isCount":true'),2)
        self.assertEqual(output.count(m.URL),2)

    def test_old_microcopy_converted_into_native_gutenberg_paragraphs(self):
        source=para('オーナー一次体験')+'\n\n'+micro('top','中古を見てみる')+'\n\n'+shortcode(4172)+'\n\n'+micro('bottom','保証もチェック')
        result,edits=outcome(101,'lexus-lbx-used',source)
        self.assertEqual(len(edits),1)
        self.assertIn('中古を見てみる',result)
        self.assertIn('保証もチェック',result)
        self.assertNotIn('tsq-gulliver-micro-20261014',result)
        self.assertIn(para('オーナー一次体験'),result)
        self.assertIn('data-id="gu101-01"',result)

    def test_convert_original_a8_paragraph_without_touching_tracking(self):
        exact_a8_para='<!-- wp:paragraph -->\n<p>'+A+IMG+'</p>\n<!-- /wp:paragraph -->'
        result,edits=outcome(102,'lexus-ux-review',exact_a8_para)
        self.assertEqual(len(edits),1)
        self.assertIn(A,result)
        self.assertIn(IMG,result)
        self.assertEqual(result.count('"isCount":true'),1)

    def test_copy_master_4507_as_regular_blocks_not_blog_parts(self):
        result,edits=outcome(3835,'goodbuy',shortcode(4507))
        self.assertEqual(len(edits),1)
        self.assertIn('中古相場を見る',result)
        self.assertIn('data-id="gu3835-01"',result)
        self.assertNotIn('[blog_parts id="4507"]',result)

    def test_original_natively_direct_button_enable_tracking(self):
        source=para('本人の感想')+'\n\n'+TEMPLATE
        result,edits=outcome(104,'lexus-ux-used',source)
        self.assertEqual(len(edits),1)
        self.assertEqual(result.count(A8),1)
        self.assertEqual(result.count(IMG),1)
        self.assertIn('data-id="gu104-01"',result)
        self.assertIn(para('本人の感想'),result)

    def test_ctn_photo_and_table_are_preserved(self):
        before='<!-- wp:image --><figure>x</figure><!-- /wp:image -->\n\n'+shortcode(4172)
        before+='\n\n<!-- wp:shortcode -->[blog_parts id="4521"]<!-- /wp:shortcode -->'
        before+='\n\n<!-- wp:table --><table></table><!-- /wp:table -->'
        result,_=outcome(103,'lexus-ux-vs-nx',before)
        self.assertIn('<!-- wp:image --><figure>x</figure><!-- /wp:image -->',result)
        self.assertIn('[blog_parts id="4521"]',result)
        self.assertIn('<!-- wp:table --><table></table><!-- /wp:table -->',result)

    def test_no_change_for_already_counted_button(self):
        before=m.copy_button(TEMPLATE,'gu105-01')
        output,edits=outcome(105,'lexus-ux-used',before)
        self.assertEqual(output,before)
        self.assertEqual(edits,[])

if __name__=='__main__':
    unittest.main()
