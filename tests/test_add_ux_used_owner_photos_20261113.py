import unittest
from unittest.mock import patch
from scripts import add_ux_used_owner_photos_20261113 as m


class OwnerPhotosTests(unittest.TestCase):
    def setUp(self):
        self.original=(
            '<!-- wp:paragraph -->\n<p>また、UXは後席と荷室に余裕がある車ではありません。'
            '<br>家族で使う人は<a href="https://tsurikue.com/lexus-ux-rear-seat/">後席の感想</a>を。</p>'
            '\n<!-- /wp:paragraph -->\n\n'
            '<!-- wp:heading -->\n<h2 class="wp-block-heading">中古で狙いたいグレードは？</h2>\n<!-- /wp:heading -->'
        )

    def guarded_transform(self,source):
        with patch.object(m,'EXPECTED_CONTENT_SHA256',m.sha(source)):
            return m.transform(source)

    def test_only_two_photo_blocks_added_after_relevant_paragraph(self):
        after=self.guarded_transform(self.original)
        self.assertEqual(after.count('<!-- wp:image'),2)
        self.assertEqual(after.count('<!-- wp:paragraph'),1)
        self.assertEqual(after.count('<!-- wp:heading'),1)
        self.assertEqual(m.linked_urls(after),m.linked_urls(self.original))
        self.assertTrue(after.index('wp-image-2201')<after.index('wp-image-2207'))
        self.assertTrue(after.index('wp-image-2207')<after.index('中古で狙いたいグレードは？'))
        self.assertIn('レクサスUXの荷室に大きな段ボール',after)

    def test_idempotent(self):
        after=self.guarded_transform(self.original)
        self.assertEqual(m.transform(after),after)

    def test_drift_cancels(self):
        with self.assertRaisesRegex(RuntimeError,'content changed'):
            m.transform(self.original)

    def test_no_insert_across_intermediate_blocks(self):
        source=self.original.replace(
            '<!-- wp:heading -->',
            '<!-- wp:separator -->\n<hr />\n<!-- /wp:separator -->\n<!-- wp:heading -->')
        with self.assertRaisesRegex(RuntimeError,'no longer borders'):
            self.guarded_transform(source)

    def test_already_present_owner_photo_without_marker_stops(self):
        source=self.original+ '\n<!-- wp:image {"id":2201} --><figure><img class="wp-image-2201" /></figure><!-- /wp:image -->'
        with self.assertRaisesRegex(RuntimeError,'already present'):
            self.guarded_transform(source)


if __name__=='__main__': unittest.main()
