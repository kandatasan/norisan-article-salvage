import importlib.util
import pathlib
import sys
import types
import unittest

stub = types.ModuleType("old_tsurikue_phase4_create_plan_dry_run")
stub.get_json = lambda *a, **k: ({}, {})
stub.fetch_collection = lambda *a, **k: []
sys.modules[stub.__name__] = stub

HERE = pathlib.Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "old_tsurikue_phase4_create_drafts_apply_once.py"
spec = importlib.util.spec_from_file_location("applymod", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def report(create=45, skip=0, review_slug="aoriika-cooking"):
    results=[]
    for i in range(create):
        results.append({"target_slug":f"s{i}","action":"CREATE_DRAFT","salvage_marker":f"<!-- m{i} -->"})
    for i in range(skip):
        results.append({"target_slug":f"x{i}","action":"SKIP_EXISTING","salvage_marker":f"<!-- x{i} -->"})
    results.append({"target_slug":review_slug,"action":"REVIEW_DUPLICATE","salvage_marker":"<!-- a -->"})
    return {
        "targets":46,"lexus_targets":0,"wordpress_write_count":0,
        "media_validation":{"confirmed_media_refs_checked":105,"confirmed_media_ref_errors":0},
        "results":results,
    }


class ApplySafetyTests(unittest.TestCase):
    def test_confirmation_exact(self):
        mod.ensure_confirmation(mod.CONFIRMATION)
        with self.assertRaises(ValueError): mod.ensure_confirmation("yes")

    def test_initial_preflight_allowed(self):
        mod.validate_preflight_report(report(45,0))

    def test_idempotent_rerun_preflight_allowed(self):
        mod.validate_preflight_report(report(0,45))

    def test_unexpected_review_rejected(self):
        with self.assertRaises(ValueError): mod.validate_preflight_report(report(45,0,"something-else"))

    def test_payload_is_draft_and_narrow(self):
        article={"slug":"safe-slug","title":"Title","content":"<!-- wp:paragraph --><p>Body</p><!-- /wp:paragraph -->"}
        row={"action":"CREATE_DRAFT","salvage_marker":"<!-- marker -->"}
        payload=mod.build_payload(article,row)
        self.assertEqual(set(payload),{"title","slug","content","status"})
        self.assertEqual(payload["status"],"draft")
        self.assertTrue(payload["content"].startswith("<!-- marker -->\n"))

    def test_manual_exclusion_never_posts(self):
        article={"slug":"aoriika-cooking","title":"x","content":"y"}
        row={"action":"CREATE_DRAFT","salvage_marker":"<!-- marker -->"}
        with self.assertRaises(ValueError): mod.build_payload(article,row)

    def test_created_post_must_be_draft(self):
        mod.validate_created_post({"id":1,"slug":"s","status":"draft"},"s")
        with self.assertRaises(ValueError): mod.validate_created_post({"id":1,"slug":"s","status":"publish"},"s")

    def test_public_counts_must_not_change(self):
        before={"live_post_publish_count":31,"live_page_publish_count":4,"live_publish_count":35}
        mod.validate_public_counts(before,dict(before))
        after=dict(before); after["live_post_publish_count"]=32
        with self.assertRaises(ValueError): mod.validate_public_counts(before,after)

    def test_no_update_delete_methods_or_media_upload_path(self):
        source=SCRIPT.read_text(encoding="utf-8")
        self.assertIn('method="POST"',source)
        self.assertNotIn('method="PUT"',source)
        self.assertNotIn('method="PATCH"',source)
        self.assertNotIn('method="DELETE"',source)
        self.assertNotIn('/wp-json/wp/v2/media',source)


if __name__ == "__main__": unittest.main()
