import inspect
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import old_tsurikue_phase4_create_plan_dry_run as m


def article(slug="target", title="対象記事", content="これは十分に独自な回収済み本文です。" * 20, media=None):
    media = media or []
    return {
        "slug": slug,
        "title": title,
        "content": content,
        "matched_media_ids": [x[0] for x in media],
        "matched_media_source_urls": [x[1] for x in media],
        "placeholders": [],
        "omitted_photo_positions": [],
    }


def current(post_id=1, slug="other", title="別の記事", content="まったく別の本文", status="publish"):
    return {
        "id": post_id,
        "slug": slug,
        "status": status,
        "link": f"https://tsurikue.com/{slug}/",
        "title": {"raw": title},
        "content": {"raw": content},
        "rest_endpoint": "posts",
    }


class Phase4CreatePlanTests(unittest.TestCase):
    def test_baseline_guard(self):
        good = {
            "targets": 46,
            "lexus_targets": 0,
            "articles_generated": 46,
            "matched_images_available": 110,
            "matched_images_used": 105,
            "matched_images_omitted_redundant": 5,
            "placeholders_retained": 28,
            "unresolved_positions_omitted": 225,
            "wordpress_write_count": 0,
            "draft_creation_count": 0,
            "media_upload_count": 0,
        }
        m.validate_final_summary(good)
        bad = dict(good, matched_images_used=104)
        with self.assertRaises(ValueError):
            m.validate_final_summary(bad)

    def test_exact_slug_skips_existing(self):
        a = article(slug="same", title="対象")
        manifest = [{"slug": "same", "title": "対象", "known_alias_slugs": []}]
        row = m.reconcile([a], manifest, [current(slug="same")])[0]
        self.assertEqual(row["action"], "SKIP_EXISTING")
        self.assertEqual(row["reason"], "exact_slug")

    def test_salvage_marker_skips_existing(self):
        a = article(slug="same", title="対象")
        manifest = [{"slug": "same", "title": "対象", "known_alias_slugs": []}]
        c = current(content=m.salvage_marker("same") + "\nold")
        row = m.reconcile([a], manifest, [c])[0]
        self.assertEqual((row["action"], row["reason"]), ("SKIP_EXISTING", "salvage_marker"))

    def test_normalized_title_skips_existing(self):
        a = article(slug="target", title="安芸津『いろは寿司』")
        manifest = [{"slug": "target", "title": "安芸津『いろは寿司』", "known_alias_slugs": []}]
        c = current(title="安芸津 いろは寿司")
        row = m.reconcile([a], manifest, [c])[0]
        self.assertEqual((row["action"], row["reason"]), ("SKIP_EXISTING", "normalized_title"))

    def test_semantic_content_overlap_requires_review(self):
        body = "アオリイカを釣って持ち帰り、イカ墨パスタにして食べました。" * 30
        a = article(slug="aoriika-cooking", title="アオリイカ実食編", content=body)
        manifest = [{"slug": a["slug"], "title": a["title"], "known_alias_slugs": []}]
        c = current(slug="aoriika-oisiiyo", title="釣ったアオリイカを食べてみた", content=body + "別の説明")
        row = m.reconcile([a], manifest, [c])[0]
        self.assertEqual(row["action"], "REVIEW_DUPLICATE")
        self.assertGreaterEqual(row["content_containment"], m.CONTENT_CONTAINMENT_THRESHOLD)

    def test_unrelated_article_is_create_draft(self):
        a = article(slug="new-slug", title="まったく新しい記事")
        manifest = [{"slug": a["slug"], "title": a["title"], "known_alias_slugs": []}]
        row = m.reconcile([a], manifest, [current()])[0]
        self.assertEqual((row["action"], row["reason"]), ("CREATE_DRAFT", "no_current_collision"))
        self.assertTrue(row["salvage_marker"].startswith("<!-- old-tsurikue-salvage:v1"))
        self.assertEqual(len(row["planned_content_sha256"]), 64)

    def test_media_reference_validation(self):
        url = "https://tsurikue.com/wp-content/uploads/2026/05/photo.jpg"
        a = article(media=[(123, url)])
        ok = m.validate_media_references([a], [{"id": 123, "source_url": url, "status": "inherit"}])
        self.assertEqual(ok["confirmed_media_ref_errors"], 0)
        missing = m.validate_media_references([a], [])
        self.assertEqual(missing["confirmed_media_ref_errors"], 1)

    def test_script_defines_get_only_http_request(self):
        source = inspect.getsource(m.get_json)
        self.assertIn('method="GET"', source)
        whole = inspect.getsource(m)
        self.assertNotIn('method="POST"', whole)
        self.assertNotIn('method="PUT"', whole)
        self.assertNotIn('method="PATCH"', whole)
        self.assertEqual(m.EXPECTED_TARGETS, 46)


if __name__ == "__main__":
    unittest.main()
