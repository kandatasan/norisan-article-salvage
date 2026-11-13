import unittest
from unittest.mock import patch

from scripts import add_ux_resale_actual_negotiation_20261113 as m


class ConfirmedOwnerNegotiationTests(unittest.TestCase):
    def setUp(self):
        self.sample=(
            m.para('CTNは条件に合う買取店を選び、やり取りは最大3社。カーセブンとネクステージから連絡が来た。')+
            '\n\n'+
            m.para('カーセブンとネクステージには、どちらにも実際のUXを見てもらいました。')+
            '\n\n'+
            m.para('2025年2月、実際の売却金額は427万円でした。半年前には435万円の提示額。')+
            '\n\n'+
            '<!-- wp:shortcode -->\n[blog_parts id="4521"]\n<!-- /wp:shortcode -->'+
            '\n\n'+
            '<!-- wp:image {"id":2231} --><figure><img class="wp-image-2231" /></figure><!-- /wp:image -->'
        )

    def updated(self):
        with patch.object(m,'EXPECTED_SHA',m.digest(self.sample)):
            return m.transform(self.sample)

    def test_inserts_real_dialogue_in_correct_place(self):
        changed=self.updated()
        self.assertEqual(changed.count('ぶっちゃけ、いくらぐらいになりそうですか？'),1)
        self.assertIn('他社に負けない金額が出せそうなら、他社の現地査定を断ろうと思う',changed)
        self.assertLess(changed.find('CTNは条件に合う'),changed.find('私が実際にやった交渉'))
        self.assertLess(changed.find('私が実際にやった交渉'),changed.find('どちらにも実際のUX'))
        self.assertEqual(changed.count('<!-- wp:paragraph'),self.sample.count('<!-- wp:paragraph')+3)
        self.assertEqual(changed.count('<!-- wp:heading'),1)

    def test_idempotence(self):
        changed=self.updated()
        self.assertEqual(m.transform(changed),changed)

    def test_unexpected_changes_fail_closed(self):
        with self.assertRaisesRegex(RuntimeError,'drifted'):
            m.transform(self.sample)

    def test_original_photo_ctn_and_amounts_are_intact(self):
        changed=self.updated()
        self.assertIn('[blog_parts id="4521"]',changed)
        self.assertEqual(changed.count('wp-image-2231'),1)
        self.assertEqual(changed.count('427万円'),self.sample.count('427万円'))
        self.assertEqual(changed.count('435万円'),self.sample.count('435万円'))
        self.assertEqual(changed.count('2025年2月'),self.sample.count('2025年2月'))

    def test_do_not_cross_over_intermediate_block(self):
        edited=self.sample.replace(
           '<!-- wp:paragraph -->\n<p>カーセブンとネクステージには',
           '<!-- wp:separator --><hr /><!-- /wp:separator -->\n<!-- wp:paragraph -->\n<p>カーセブンとネクステージには'
        )
        with patch.object(m,'EXPECTED_SHA',m.digest(edited)):
            with self.assertRaisesRegex(RuntimeError,'Unexpected block'):
                m.transform(edited)

if __name__=='__main__':unittest.main()
