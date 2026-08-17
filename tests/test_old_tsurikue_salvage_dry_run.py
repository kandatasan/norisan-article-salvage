import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest
import urllib.parse
from unittest import mock

ROOT = pathlib.Path(__file__).parents[1]
MODULE_PATH = ROOT / "scripts" / "old_tsurikue_salvage_dry_run.py"
spec = importlib.util.spec_from_file_location("old_tsurikue_salvage_dry_run", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
assert spec.loader
spec.loader.exec_module(module)


class OldTsurikueSalvageDryRunTests(unittest.TestCase):
    def test_manifest_has_exactly_46_unique_non_lexus_targets(self):
        targets = module.load_targets()
        self.assertEqual(len(targets), 46)
        self.assertEqual(len({row["slug"] for row in targets}), 46)
        self.assertEqual({row["source_site"] for row in targets}, {"tsurikue.com"})
        self.assertIn("orizuru-tower", {row["slug"] for row in targets})
        self.assertNotIn("orizuru", {row["slug"] for row in targets})

    def test_manifest_rejects_lexus_marker_in_title(self):
        targets = module.load_targets()
        targets[0] = {**targets[0], "title": "レクサスUXの記事"}
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as handle:
            json.dump(targets, handle, ensure_ascii=False)
            handle.flush()
            with self.assertRaisesRegex(ValueError, "Lexus"):
                module.load_targets(pathlib.Path(handle.name))

    def test_reconcile_classifies_exact_title_duplicate_and_create(self):
        targets = [
            {"slug": "exact", "title": "Exact", "source_site": "tsurikue.com", "known_alias_slugs": []},
            {"slug": "new-slug", "title": "同じ　タイトル！", "source_site": "tsurikue.com", "known_alias_slugs": []},
            {"slug": "missing", "title": "Missing", "source_site": "tsurikue.com", "known_alias_slugs": []},
        ]
        content = [
            {"id": 1, "slug": "exact", "status": "publish", "link": "/exact/", "title": {"raw": "Changed"}},
            {"id": 2, "slug": "old-slug", "status": "draft", "link": "/old-slug/", "title": {"raw": "同じタイトル"}},
        ]
        rows = module.reconcile(targets, content)
        self.assertEqual([row["action"] for row in rows], ["SKIP_EXISTING", "SKIP_DUPLICATE", "CREATE_DRAFT"])
        self.assertEqual(rows[1]["match_reason"], "normalized_title")

    def test_collection_fetch_is_get_only_and_paginates(self):
        calls = []
        original = module.get_json

        def fake_get(url, authorization):
            calls.append((url, authorization))
            page = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)["page"][0]
            if page == "1":
                return ([{"id": 1}], {"X-WP-TotalPages": "2"})
            return ([{"id": 2}], {"X-WP-TotalPages": "2"})

        try:
            module.get_json = fake_get
            rows = module.fetch_collection("https://tsurikue.com", "posts", "Basic redacted", context="edit")
        finally:
            module.get_json = original
        self.assertEqual([row["id"] for row in rows], [1, 2])
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(auth == "Basic redacted" for _, auth in calls))

    def test_http_request_explicitly_uses_get(self):
        response = mock.MagicMock()
        response.read.return_value = b"[]"
        response.headers = {}
        response.__enter__.return_value = response
        with mock.patch.object(module.urllib.request, "urlopen", return_value=response) as urlopen:
            rows, headers = module.get_json("https://tsurikue.com/wp-json/wp/v2/posts", "Basic redacted")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.get_header("Authorization"), "Basic redacted")
        self.assertEqual((rows, headers), ([], {}))

    def test_report_explicitly_records_zero_writes_and_writes_three_artifacts(self):
        targets = [{"slug": "one", "title": "One", "source_site": "tsurikue.com", "known_alias_slugs": []}]
        content = [
            {"id": 1, "slug": "published", "status": "publish", "title": {"raw": "Published"}, "rest_endpoint": "posts"},
            {"id": 2, "slug": "draft", "status": "draft", "title": {"raw": "Draft"}, "rest_endpoint": "pages"},
        ]
        report = module.build_report(targets, content, [{"id": 9}])
        self.assertEqual(report["wordpress_write_count"], 0)
        self.assertEqual(report["action_counts"]["CREATE_DRAFT"], 1)
        self.assertEqual(report["live_post_publish_count"], 1)
        self.assertEqual(report["live_page_draft_count"], 1)
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory)
            module.write_artifacts(output, report)
            self.assertEqual({path.name for path in output.iterdir()}, {"result.json", "result.csv", "result.md"})
            saved = json.loads((output / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["wordpress_write_count"], 0)


if __name__ == "__main__":
    unittest.main()
