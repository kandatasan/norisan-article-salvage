import hashlib
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("editorial_apply", ROOT / "scripts" / "apply_editorial_draft_once.py")
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)

FUNNEL = """<!-- wp:loos/button -->
<div class="swell-block-button -html green_"><a href="https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY" rel="nofollow">ガリバーで希望のUXを探してみる</a><img src="https://www13.a8.net/0.gif?a8mat=4B65SD+8DUSHE+9QU+NVHCY"></div>
<!-- /wp:loos/button -->"""

class UxPurchaseFunnelTests(unittest.TestCase):
    def target(self, current, **extra):
        data = {
            "slug": "sample",
            "expected_current_content_sha256": hashlib.sha256(current.encode()).hexdigest(),
            "anchor_heading": "NEXT",
            "marker": "<!-- ux-marker -->",
        }
        data.update(extra)
        return data

    def test_replaces_legacy_triplet_with_4505_and_native_button(self):
        legacy = """<!-- wp:html -->
<div class="tsq-gulliver-micro-20261014 top">TOP COPY</div>
<!-- /wp:html -->

<!-- wp:paragraph -->
<p><a href="https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY" rel="nofollow">old</a><img src="https://www15.a8.net/0.gif?a8mat=4B65SD+8DUSHE+9QU+NVHCY"></p>
<!-- /wp:paragraph -->

<!-- wp:html -->
<div class="tsq-gulliver-micro-20261014 bottom">BOTTOM</div>
<!-- /wp:html -->"""
        heading = """<!-- wp:heading -->
<h2 class="wp-block-heading">NEXT</h2>
<!-- /wp:heading -->"""
        current = legacy + "\n\n" + heading
        target = self.target(current, mode="legacy_gulliver_triplet", legacy_top_phrase="TOP COPY")
        updated, action = MOD.build_ux_purchase_funnel_target(current, target, FUNNEL)
        self.assertEqual(action, "UPDATE")
        self.assertNotIn("tsq-gulliver-micro-20261014", updated)
        self.assertIn('[blog_parts id="4505"]', updated)
        self.assertIn("swell-block-button -html green_", updated)
        self.assertIn("<!-- ux-marker -->", updated)

    def test_replaces_4172_and_adds_happiness_line(self):
        source = """<!-- wp:paragraph -->
<p>OLD LEAD</p>
<!-- /wp:paragraph -->

<!-- wp:shortcode -->
[blog_parts id="4172"]
<!-- /wp:shortcode -->"""
        heading = """<!-- wp:heading -->
<h2 class="wp-block-heading">NEXT</h2>
<!-- /wp:heading -->"""
        current = source + "\n\n" + heading
        target = self.target(
            current,
            mode="legacy_shortcode_4172",
            legacy_paragraph="OLD LEAD",
            lead_paragraph="200〜300万円台で、自分に合うUXが見つけられたら、幸せになれます。",
        )
        updated, action = MOD.build_ux_purchase_funnel_target(current, target, FUNNEL)
        self.assertEqual(action, "UPDATE")
        self.assertNotIn('[blog_parts id="4172"]', updated)
        self.assertIn("幸せになれます。", updated)
        self.assertIn('[blog_parts id="4505"]', updated)

    def test_insert_before_exact_block_keeps_original_text(self):
        anchor = """<!-- wp:paragraph -->
<p>SELLING SECTION</p>
<!-- /wp:paragraph -->"""
        heading = """<!-- wp:heading -->
<h2 class="wp-block-heading">NEXT</h2>
<!-- /wp:heading -->"""
        current = """<!-- wp:paragraph -->
<p>USED UX COPY</p>
<!-- /wp:paragraph -->

""" + anchor + "\n\n" + heading
        target = self.target(
            current,
            mode="insert_before_block",
            anchor_block=anchor,
        )
        updated, action = MOD.build_ux_purchase_funnel_target(current, target, FUNNEL)
        self.assertEqual(action, "UPDATE")
        self.assertIn("USED UX COPY", updated)
        self.assertIn(anchor, updated)
        self.assertLess(updated.index('[blog_parts id="4505"]'), updated.index(anchor))
        self.assertEqual(updated.replace(
            "<!-- ux-marker -->\n\n<!-- wp:shortcode -->\n[blog_parts id=\"4505\"]\n<!-- /wp:shortcode -->\n\n" + FUNNEL + "\n\n",
            "",
            1,
        ), current)

    def test_insert_before_heading_keeps_original_text(self):
        heading = """<!-- wp:heading -->
<h2 class="wp-block-heading">NEXT</h2>
<!-- /wp:heading -->"""
        before = """<!-- wp:heading -->
<h2 class="wp-block-heading">BUDGET</h2>
<!-- /wp:heading -->"""
        current = heading + "\n\n<!-- wp:paragraph -->\n<p>USED UX COPY</p>\n<!-- /wp:paragraph -->\n\n" + before
        target = self.target(
            current,
            mode="insert_before_heading",
            before_heading="BUDGET",
            before_heading_level=2,
        )
        updated, action = MOD.build_ux_purchase_funnel_target(current, target, FUNNEL)
        self.assertEqual(action, "UPDATE")
        self.assertIn("USED UX COPY", updated)
        self.assertLess(updated.index('[blog_parts id="4505"]'), updated.index("BUDGET"))
        self.assertIn(before, updated)


    def test_replaces_legacy_native_button_without_increasing_button_count(self):
        legacy = """<!-- wp:html -->
<div class="tsq-gulliver-micro-20261014 top">TOP COPY</div>
<!-- /wp:html -->

<!-- wp:loos/button -->
<div class="swell-block-button -html green_ -size-l is-style-btn_shiny"><a href="https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY" rel="nofollow">old</a><img src="https://www15.a8.net/0.gif?a8mat=4B65SD+8DUSHE+9QU+NVHCY"></div>
<!-- /wp:loos/button -->

<!-- wp:html -->
<div class="tsq-gulliver-micro-20261014 bottom">BOTTOM</div>
<!-- /wp:html -->"""
        heading = """<!-- wp:heading -->
<h2 class="wp-block-heading">NEXT</h2>
<!-- /wp:heading -->"""
        current = legacy + "\n\n" + heading
        target = self.target(current, mode="legacy_gulliver_native_triplet", legacy_top_phrase="TOP COPY")
        updated, action = MOD.build_ux_purchase_funnel_target(current, target, FUNNEL)
        self.assertEqual(action, "UPDATE")
        self.assertEqual(updated.count("swell-block-button -html green_"), 1)
        self.assertIn('[blog_parts id="4505"]', updated)


if __name__ == "__main__":
    unittest.main()
