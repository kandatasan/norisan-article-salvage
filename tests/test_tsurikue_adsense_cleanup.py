import importlib.util
import pathlib
import sys
import unittest

MODULE_PATH = pathlib.Path(__file__).parents[1] / "scripts" / "tsurikue_adsense_cleanup.py"
spec = importlib.util.spec_from_file_location("tsurikue_adsense_cleanup", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
assert spec.loader
spec.loader.exec_module(module)


def doc(content, post_id=1939, title="Test title｜subtitle", endpoint="posts", link=None):
    expected_link = link or module.TARGET_DOCUMENTS.get(post_id, (endpoint, "https://tsurikue.com/test/"))[1]
    return module.Document(post_id, endpoint, title, expected_link, content)


class AdsenseCleanupTests(unittest.TestCase):
    def test_edit_memo_paragraph_is_deleted(self):
        source = (
            '<!-- wp:paragraph -->\n'
            '<p><strong>【ここに、山陰1泊2日ドライブ旅のアイキャッチ写真】</strong></p>\n'
            '<!-- /wp:paragraph -->'
        )
        result = module.transform(doc(source))
        self.assertEqual(result.updated.strip(), "")
        self.assertEqual([a.kind for a in result.actions], ["delete_edit_memo"])

    def test_legacy_wording_is_replaced(self):
        before = "この記事は、過去に実際に行った体験をもとに再編集しています。"
        source = f"<!-- wp:paragraph -->\n<p>{before}</p>\n<!-- /wp:paragraph -->"
        result = module.transform(doc(source))
        self.assertNotIn("再編集", result.updated)
        self.assertIn("2026年7月に内容を整理", result.updated)
        self.assertEqual([a.kind for a in result.actions], ["replace_legacy_text"])

    def test_dead_internal_link_is_replaced(self):
        source = (
            '<!-- wp:paragraph -->\n'
            '<p><a href="https://www.tsurikue.com/fishingpage/?x=1#top">釣りの部屋</a></p>\n'
            '<!-- /wp:paragraph -->'
        )
        result = module.transform(doc(source, post_id=2391))
        self.assertIn(module.DEAD_REPLACEMENT, result.updated)
        self.assertNotIn("fishingpage", result.updated)
        self.assertEqual([a.kind for a in result.actions], ["replace_dead_link"])

    def test_blank_alt_uses_section_heading_and_existing_alt_is_preserved(self):
        source = (
            '<!-- wp:heading -->\n<h2>鳥取砂丘 砂の美術館はかなり圧巻だった</h2>\n<!-- /wp:heading -->\n'
            '<!-- wp:image -->\n<figure><img src="a.jpg" alt="" class="wp-image-999"/></figure>\n<!-- /wp:image -->\n'
            '<!-- wp:image -->\n<figure><img src="b.jpg" alt="already set" class="wp-image-1000"/></figure>\n<!-- /wp:image -->'
        )
        result = module.transform(doc(source))
        self.assertIn('alt="鳥取砂丘 砂の美術館はかなり圧巻"', result.updated)
        self.assertIn('alt="already set"', result.updated)
        self.assertEqual(sum(a.kind == "add_alt" for a in result.actions), 1)

    def test_top_page_special_alts_are_stable(self):
        source = '<img src="x.jpg" alt="" class="wp-image-2298"/>'
        result = module.transform(
            doc(source, post_id=2255, title="トップページ", endpoint="pages", link="https://tsurikue.com/")
        )
        self.assertIn('alt="釣りカテゴリー"', result.updated)

    def test_transform_is_idempotent(self):
        source = (
            '<!-- wp:heading -->\n<h2>ギンザケの石狩鍋</h2>\n<!-- /wp:heading -->\n'
            '<img src="a.jpg" alt="" class="wp-image-999"/>'
        )
        first = module.transform(doc(source, post_id=2391))
        second = module.transform(doc(first.updated, post_id=2391))
        self.assertEqual(second.updated, first.updated)
        self.assertEqual(second.actions, [])

    def test_expected_count_validation_rejects_mismatch(self):
        summary = module.RunSummary(
            affected_documents=31,
            edit_memos=4,
            legacy_replacements=34,
            link_replacements=1,
            alt_additions=182,
            remaining_edit_memos=0,
            remaining_legacy_terms=0,
            remaining_dead_links=0,
            remaining_blank_alts=0,
        )
        with self.assertRaises(SystemExit):
            module.validate_expected(summary)

    def test_authenticated_fetch_uses_raw_content_and_explicit_endpoint(self):
        calls = []
        original_targets = module.TARGET_DOCUMENTS
        original_request = module.request_json

        def fake_request(url, **kwargs):
            calls.append((url, kwargs))
            return {
                "id": 1939,
                "status": "publish",
                "link": "https://tsurikue.com/hiroshima-sanin-1night-2days/",
                "title": {"raw": "Raw title", "rendered": "Rendered title"},
                "content": {"raw": "RAW CONTENT", "rendered": "RENDERED CONTENT"},
            }

        try:
            module.TARGET_DOCUMENTS = {
                1939: ("posts", "https://tsurikue.com/hiroshima-sanin-1night-2days/")
            }
            module.request_json = fake_request
            docs = module.fetch_authenticated_documents("https://tsurikue.com", "user", "pass")
        finally:
            module.TARGET_DOCUMENTS = original_targets
            module.request_json = original_request

        self.assertEqual(docs[0].content, "RAW CONTENT")
        self.assertIn("/posts/1939?", calls[0][0])
        self.assertIn("context=edit", calls[0][0])

    def test_apply_sends_content_only(self):
        payloads = []
        original_request = module.request_json

        def fake_request(url, **kwargs):
            payloads.append(kwargs.get("payload"))
            return {"id": 1939}

        try:
            module.request_json = fake_request
            original = doc("before")
            result = module.Result("before", "after", [module.Action("add_alt", "before", "after", "alt")])
            statuses = module.apply_updates_with_rollback(
                "https://tsurikue.com", "user", "pass", [(original, result)]
            )
        finally:
            module.request_json = original_request

        self.assertEqual(statuses[1939], "updated")
        self.assertEqual(payloads, [{"content": "after"}])

    def test_apply_rolls_back_after_later_failure(self):
        calls = []
        original_request = module.request_json

        def fake_request(url, **kwargs):
            calls.append((url, kwargs.get("payload")))
            if "/posts/1887" in url and kwargs.get("payload") == {"content": "after-2"}:
                raise RuntimeError("simulated")
            return {"id": 1}

        d1 = doc("before-1", post_id=1883, link=module.TARGET_DOCUMENTS[1883][1])
        d2 = doc("before-2", post_id=1887, link=module.TARGET_DOCUMENTS[1887][1])
        r1 = module.Result("before-1", "after-1", [module.Action("add_alt", "", "", "")])
        r2 = module.Result("before-2", "after-2", [module.Action("add_alt", "", "", "")])
        try:
            module.request_json = fake_request
            with self.assertRaises(RuntimeError):
                module.apply_updates_with_rollback(
                    "https://tsurikue.com", "user", "pass", [(d1, r1), (d2, r2)]
                )
        finally:
            module.request_json = original_request

        self.assertEqual(calls[0][1], {"content": "after-1"})
        self.assertEqual(calls[1][1], {"content": "after-2"})
        self.assertEqual(calls[2][1], {"content": "before-1"})


if __name__ == "__main__":
    unittest.main()
