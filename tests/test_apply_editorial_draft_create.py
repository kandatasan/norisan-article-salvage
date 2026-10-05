import importlib.util, pathlib, unittest

P = pathlib.Path(__file__).parents[1] / 'scripts' / 'apply_editorial_draft_once.py'
spec = importlib.util.spec_from_file_location('m_create', P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class CreatePackageTests(unittest.TestCase):
    def cfg(self):
        return {
            'operation': 'create',
            'slug': 'new-draft',
            'title': 'New Draft',
            'status': 'draft',
            'categories': [47],
            'featured_media': 0,
            'expected_media': {'7': '/wp-content/uploads/2026/10/x.jpg'},
        }

    def full(self):
        return '<!-- wp:image {"id":7} --><figure><img src="https://tsurikue.com/wp-content/uploads/2026/10/x.jpg" class="wp-image-7"/></figure><!-- /wp:image -->'

    def test_accept_confirmed_inline_media(self):
        self.assertEqual(m.validate_create_package(self.cfg(), self.full()), 1)

    def test_reject_non_draft_create(self):
        cfg = self.cfg(); cfg['status'] = 'publish'
        with self.assertRaises(RuntimeError):
            m.validate_create_package(cfg, self.full())

    def test_reject_post_id_on_create(self):
        cfg = self.cfg(); cfg['post_id'] = 123
        with self.assertRaises(RuntimeError):
            m.validate_create_package(cfg, self.full())

    def test_reject_unconfirmed_inline_media(self):
        cfg = self.cfg(); cfg['expected_media'] = {}
        with self.assertRaises(RuntimeError):
            m.validate_create_package(cfg, self.full())

    def test_reject_external_image(self):
        full = '<figure><img src="https://example.com/x.jpg"/></figure>'
        with self.assertRaises(RuntimeError):
            m.validate_create_package(self.cfg(), full)

    def test_reject_wp_image_zero(self):
        full = '<figure><img src="https://tsurikue.com/x.jpg" class="wp-image-0"/></figure>'
        with self.assertRaises(RuntimeError):
            m.validate_create_package(self.cfg(), full)

if __name__ == '__main__':
    unittest.main()
