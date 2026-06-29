import importlib.util
import pathlib
import sys
import unittest

MODULE_PATH = pathlib.Path(__file__).parents[1] / "scripts" / "tsurikue_internal_link_dry_run.py"
spec = importlib.util.spec_from_file_location("tsurikue_dry_run", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
assert spec.loader
spec.loader.exec_module(module)


class DryRunTests(unittest.TestCase):
    def test_url_variants_are_normalized(self):
        variants = [
            "/fishingpage/",
            "https://tsurikue.com/fishingpage",
            "http://www.tsurikue.com/fishingpage/?x=1#top",
        ]
        self.assertTrue(all(module.is_target(value) for value in variants))
        self.assertFalse(module.is_target("https://example.com/fishingpage/"))

    def test_substantive_paragraph_keeps_text(self):
        source = '<!-- wp:paragraph -->\n<p><a href="/hanabiramenn/">華火のラーメン</a>は、魚介系ダシで濃厚です。</p>\n<!-- /wp:paragraph -->'
        result = module.transform(source)
        self.assertIn("<p>華火のラーメンは、魚介系ダシで濃厚です。</p>", result.updated)
        self.assertEqual([action.kind for action in result.actions], ["unwrap_anchor"])

    def test_navigation_paragraph_is_removed_with_comments(self):
        source = '前\n<!-- wp:paragraph -->\n<p>感想は、<a href="/hanabiramenn/">個別記事</a>で紹介しています。</p>\n<!-- /wp:paragraph -->\n後'
        result = module.transform(source)
        self.assertNotIn("hanabiramenn", result.updated)
        self.assertNotIn("wp:paragraph", result.updated)
        self.assertEqual([action.kind for action in result.actions], ["delete_block"])

    def test_single_link_list_is_removed(self):
        source = '<!-- wp:list -->\n<ul class="wp-block-list"><!-- wp:list-item -->\n<li><a href="/fishingpage/">釣りの部屋へ</a></li>\n<!-- /wp:list-item --></ul>\n<!-- /wp:list -->'
        result = module.transform(source)
        self.assertEqual(result.updated.strip(), "")

    def test_unrelated_list_item_is_preserved(self):
        source = '<!-- wp:list -->\n<ul><!-- wp:list-item -->\n<li><a href="/fishingpage/">削除</a></li>\n<!-- /wp:list-item -->\n<!-- wp:list-item -->\n<li><a href="/live/">残す</a></li>\n<!-- /wp:list-item --></ul>\n<!-- /wp:list -->'
        result = module.transform(source)
        self.assertNotIn("fishingpage", result.updated)
        self.assertIn('/live/', result.updated)

    def test_image_link_is_unwrapped_without_removing_image(self):
        source = '<!-- wp:paragraph -->\n<p><a href="/fishingpage/"><img src="fish.jpg" alt="魚" /></a></p>\n<!-- /wp:paragraph -->'
        result = module.transform(source)
        self.assertIn('<img src="fish.jpg" alt="魚" />', result.updated)
        self.assertNotIn('<a href="/fishingpage/">', result.updated)
        self.assertEqual([action.kind for action in result.actions], ["unwrap_anchor"])

    def test_expected_counts_validation_rejects_mismatch(self):
        summary = module.RunSummary(affected_documents=10, target_links=22, delete_blocks=22, unwrap_anchors=1, remaining=0)
        with self.assertRaises(SystemExit):
            module.validate_expected(summary)

    def test_authenticated_fetch_uses_context_edit_and_content_raw(self):
        calls = []

        def fake_request_json(url, **kwargs):
            calls.append((url, kwargs))
            return {
                "id": 2358,
                "status": "publish",
                "link": "https://tsurikue.com/everyman-iiyo/",
                "title": {"raw": "raw title", "rendered": "rendered title"},
                "content": {"raw": "RAW BODY", "rendered": "RENDERED BODY"},
            }

        original_ids = module.TARGET_POST_IDS
        original_request_json = module.request_json
        try:
            module.TARGET_POST_IDS = (2358,)
            module.request_json = fake_request_json
            docs = module.fetch_authenticated_posts("https://tsurikue.com", "user", "pass")
        finally:
            module.TARGET_POST_IDS = original_ids
            module.request_json = original_request_json

        self.assertEqual(docs[0].content, "RAW BODY")
        self.assertNotIn("RENDERED BODY", docs[0].content)
        self.assertIn("context=edit", calls[0][0])
        self.assertEqual(calls[0][1].get("auth_header", "").startswith("Basic "), True)

    def test_apply_update_sends_only_content(self):
        sent_payloads = []

        def fake_request_json(url, **kwargs):
            sent_payloads.append(kwargs.get("payload"))
            return {"id": 2358}

        original_request_json = module.request_json
        try:
            module.request_json = fake_request_json
            doc = module.Document(2358, "post", "Title", "https://example.test", "before")
            result = module.Result("before", "after", [module.Action("unwrap_anchor", ["/fishingpage/"], "before", "after", "test")], [])
            statuses = module.apply_updates("https://tsurikue.com", "user", "pass", [(doc, result)])
        finally:
            module.request_json = original_request_json

        self.assertEqual(statuses[2358], "updated")
        self.assertEqual(sent_payloads, [{"content": "after"}])


if __name__ == "__main__":
    unittest.main()
