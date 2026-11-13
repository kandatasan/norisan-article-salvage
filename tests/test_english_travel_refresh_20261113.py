import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from update_english_travel_refresh_20261113 import build_updated, digest, heading_block, render_image, clean_base, MARKER

class TravelRefreshTests(unittest.TestCase):
    def setUp(self):
        self.sample = '<!-- wp:heading -->\n<h2 class="wp-block-heading">The stop</h2>\n<!-- /wp:heading -->\n\n<!-- wp:paragraph -->\n<p>Original story.</p>\n<!-- /wp:paragraph -->\n\n<!-- wp:heading -->\n<h2 class="wp-block-heading">Verdict</h2>\n<!-- /wp:heading -->\n'

    def test_additive_photo_preserves_original(self):
        cfg = {'photos':[{'id':1960,'heading':'Verdict','position':'before','alt':'Flower detail','path':'/wp-content/uploads/2026/05/IMG_9871-768x1024.jpeg'}]}
        final=build_updated(self.sample,cfg)
        self.assertIn('Original story.', final)
        self.assertIn('wp-image-1960', final)
        self.assertEqual(final.count(MARKER),1)
        self.assertLess(final.find('wp-image-1960'),final.find('>Verdict</h2>'))
        with self.assertRaises(RuntimeError):
            build_updated(final,cfg)

    def test_affiliate_section_requires_disclosure(self):
        base={'photos':[], 'section': {'before_heading':'Verdict','html':'<a href="https://www.discovercars.com/?a_aid=tsurikue">Go</a>'}}
        with self.assertRaisesRegex(RuntimeError,'Affiliate terms'):
            build_updated(self.sample,base)

    def test_licence_cta_affiliate_once(self):
        link='<a href="https://www.discovercars.com/?a_aid=tsurikue" rel="sponsored nofollow noopener">Compare</a>'
        cfg={'section': {'before_heading':'Verdict','html':'<!-- wp:paragraph -->\n<p>This is an affiliate link. '+link+'</p>\n<!-- /wp:paragraph -->'}}
        final=build_updated(self.sample,cfg)
        self.assertEqual(final.count('https://www.discovercars.com/?a_aid=tsurikue'),1)
        self.assertIn(MARKER+':section',final)

    def test_missing_heading_refuses(self):
        with self.assertRaises(RuntimeError):
            heading_block(self.sample,'Does not exist')

    def test_media_filename_normalization(self):
        a='https://tsurikue.com/wp-content/uploads/2026/05/IMG_9871.jpeg'
        b='/wp-content/uploads/2026/05/IMG_9871-768x1024.jpeg'
        self.assertEqual(clean_base(a),clean_base(b))

    def test_reject_unsafe_image_path(self):
        with self.assertRaises(RuntimeError):
            render_image({'id':9,'path':'https://example.com/evil.jpg','alt':'Unsafe'})

if __name__=='__main__':
    unittest.main()
