import importlib.util
import pathlib
import sys
import unittest

MODULE_PATH = pathlib.Path(__file__).parents[1] / "scripts" / "tsurikue_round2_link_cleanup.py"
spec = importlib.util.spec_from_file_location("tsurikue_round2_cleanup", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
assert spec.loader
spec.loader.exec_module(module)


class Round2CleanupTests(unittest.TestCase):
    def test_url_variants_are_normalized(self):
        self.assertTrue(module.is_dead("/matsuura/"))
        self.assertTrue(module.is_dead("https://tsurikue.com/matsuura/?x=1"))
        self.assertFalse(module.is_dead("https://example.com/matsuura/"))
        self.assertTrue(module.is_old_contact("https://tsurikue.com/contact"))

    def test_substantive_paragraph_keeps_text_and_unwraps_anchor(self):
        source = (
            '<!-- wp:paragraph -->\n'
            '<p><a href="/matsuura/">らーめん まつうら</a>は、ガツンと濃厚な魚介が特徴のお店です。</p>\n'
            '<!-- /wp:paragraph -->'
        )
        result = module.transform(source, 1892)
        self.assertIn(
            "<p>らーめん まつうらは、ガツンと濃厚な魚介が特徴のお店です。</p>",
            result.updated,
        )
        self.assertEqual([action.kind for action in result.actions], ["unwrap_anchor"])

    def test_navigation_paragraph_is_removed(self):
        source = (
            '<!-- wp:paragraph -->\n'
            '<p>泊まった話は、<a href="/totoya-iiyo/">宿泊体験記事</a>で紹介しています。</p>\n'
            '<!-- /wp:paragraph -->'
        )
        result = module.transform(source, 1939)
        self.assertEqual(result.updated.strip(), "")
        self.assertEqual([action.kind for action in result.actions], ["delete_block"])

    def test_dead_list_item_is_removed_but_live_item_remains(self):
        source = (
            '<!-- wp:list -->\n<ul>'
            '<!-- wp:list-item -->\n<li><a href="/tanoshiiumiasobi/">削除</a></li>\n<!-- /wp:list-item -->'
            '<!-- wp:list-item -->\n<li><a href="/live/">残す</a></li>\n<!-- /wp:list-item -->'
            '</ul>\n<!-- /wp:list -->'
        )
        result = module.transform(source, 1887)
        self.assertNotIn("tanoshiiumiasobi", result.updated)
        self.assertIn('/live/', result.updated)

    def test_contact_link_is_replaced_not_deleted(self):
        source = (
            '<!-- wp:paragraph -->\n'
            '<p><a href="https://tsurikue.com/contact">お問い合わせはこちら</a></p>\n'
            '<!-- /wp:paragraph -->'
        )
        result = module.transform(source, 1970)
        self.assertIn(module.CONTACT_REPLACEMENT, result.updated)
        self.assertIn("お問い合わせはこちら", result.updated)
        self.assertEqual([action.kind for action in result.actions], ["replace_link"])

    def test_next_adventure_is_post_specific(self):
        source = (
            '<!-- wp:paragraph -->\n'
            '<p><strong>次の冒険へ</strong></p>\n'
            '<!-- /wp:paragraph -->'
        )
        self.assertIn("次の冒険へ", module.transform(source, 1887).updated)
        self.assertNotIn("次の冒険へ", module.transform(source, 1939).updated)

    def test_unrelated_paragraph_is_preserved(self):
        source = (
            '<!-- wp:paragraph -->\n'
            '<p><strong>関連記事</strong></p>\n'
            '<!-- /wp:paragraph -->'
        )
        self.assertEqual(module.transform(source, 1887).updated, source)

    def test_expected_counts_validation_rejects_mismatch(self):
        summary = module.RunSummary(
            affected_documents=8,
            occurrences=22,
            delete_blocks=18,
            unwrap_anchors=3,
            replace_links=2,
            orphan_paragraphs=11,
            remaining=0,
        )
        with self.assertRaises(SystemExit):
            module.validate_expected(summary)

    def test_authenticated_fetch_uses_posts_and_pages_and_raw_content(self):
        calls = []

        def fake_request_json(url, **kwargs):
            calls.append((url, kwargs))
            post_id = 1887 if "/posts/" in url else 1970
            return {
                "id": post_id,
                "status": "publish",
                "link": "https://tsurikue.com/test/",
                "title": {"raw": "raw title", "rendered": "rendered title"},
                "content": {"raw": "RAW BODY", "rendered": "RENDERED BODY"},
            }

        original_documents = module.TARGET_DOCUMENTS
        original_request_json = module.request_json
        try:
            module.TARGET_DOCUMENTS = {1887: "posts", 1970: "pages"}
            module.request_json = fake_request_json
            docs = module.fetch_authenticated_documents(
                "https://tsurikue.com", "user", "pass"
            )
        finally:
            module.TARGET_DOCUMENTS = original_documents
            module.request_json = original_request_json

        self.assertEqual([doc.content for doc in docs], ["RAW BODY", "RAW BODY"])
        self.assertTrue(any("/posts/1887?" in url for url, _ in calls))
        self.assertTrue(any("/pages/1970?" in url for url, _ in calls))
        self.assertTrue(all("context=edit" in url for url, _ in calls))

    def test_apply_sends_only_content(self):
        payloads = []

        def fake_request_json(url, **kwargs):
            payloads.append(kwargs.get("payload"))
            return {"id": 1887}

        original_request_json = module.request_json
        try:
            module.request_json = fake_request_json
            doc = module.Document(1887, "posts", "Title", "https://example.test", "before")
            result = module.Result(
                "before",
                "after",
                [module.Action("delete_block", ["/matsuura/"], "before", "", "test")],
                [],
            )
            statuses = module.apply_updates_with_rollback(
                "https://tsurikue.com", "user", "pass", [(doc, result)]
            )
        finally:
            module.request_json = original_request_json

        self.assertEqual(statuses[1887], "updated")
        self.assertEqual(payloads, [{"content": "after"}])

    def test_apply_rolls_back_earlier_updates_on_failure(self):
        calls = []

        def fake_request_json(url, **kwargs):
            calls.append((url, kwargs.get("payload")))
            if "/posts/1892" in url:
                raise RuntimeError("simulated failure")
            return {"id": 1887}

        original_request_json = module.request_json
        try:
            module.request_json = fake_request_json
            doc1 = module.Document(1887, "posts", "One", "https://example.test/1", "before-1")
            doc2 = module.Document(1892, "posts", "Two", "https://example.test/2", "before-2")
            result1 = module.Result(
                "before-1",
                "after-1",
                [module.Action("delete_block", ["/matsuura/"], "before-1", "", "test")],
                [],
            )
            result2 = module.Result(
                "before-2",
                "after-2",
                [module.Action("delete_block", ["/ra-tei/"], "before-2", "", "test")],
                [],
            )
            with self.assertRaises(RuntimeError):
                module.apply_updates_with_rollback(
                    "https://tsurikue.com",
                    "user",
                    "pass",
                    [(doc1, result1), (doc2, result2)],
                )
        finally:
            module.request_json = original_request_json

        self.assertEqual(calls[0][1], {"content": "after-1"})
        self.assertEqual(calls[1][1], {"content": "after-2"})
        self.assertEqual(calls[2][1], {"content": "before-1"})


if __name__ == "__main__":
    unittest.main()
