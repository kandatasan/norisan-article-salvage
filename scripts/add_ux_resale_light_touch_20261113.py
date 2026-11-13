"""UX resale: small info list + actual negotiation, every original byte preserved.

User specifically requested a light addition after reverting a heavy rewrite.
Do not change any original paragraph, heading, table, image, ad or link.
"""
from __future__ import annotations
import hashlib
import html
import json
import re
from pathlib import Path

POST_ID = 2222
SLUG = "ux-resale"
TITLE = "レクサスUXのリセールは？616万円で購入し427万円で売却した記録"
EXPECTED_SHA256 = "f90f4f14e2c5761f4ed4cb43121799b156a994468277f5ef4f8f958817300a10"
META_EXPECTED = {
    "id": POST_ID,
    "slug": SLUG,
    "status": "publish",
    "featured_media": 2223,
    "categories": [10, 11],
    "author": 1,
}
MARKER_STATS = "<!-- tsurikue-ux-resale-light-stats-20261113 -->"
MARKER_CALLS = "<!-- tsurikue-ux-resale-light-real-negotiation-20261113 -->"

P_BLOCK = re.compile(r'<!-- wp:paragraph(?: [^\n]*?)? -->\s*<p[^>]*>.*?</p>\s*<!-- /wp:paragraph -->', re.S)

STAT_ANCHOR = "350万円、500万円前後、430万円、435万円は査定時の提示額。"
CALL_ANCHOR = "CTNは条件に合う買取店を選び"
FOLLOWING_CAVEAT = "なお、購入額616万円の見積もり内訳にはオプションや諸費用も含まれます。"
FOLLOWING_ONSITE = "2社とも電話だけで金額を決めたわけではありません。"

STATS = '''<!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li><strong>車両：</strong>2023年式 UX250h F SPORT 特別仕様車「Emotional Explorer」</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li><strong>新車購入総額：</strong>約616万円（オプション・諸費用込み）</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li><strong>実売却額：</strong>427万円（2025年2月）</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li><strong>購入総額に対する残価率：</strong>約69.3％（427万円 ÷ 616万円）</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->'''

CALLS = '''<!-- wp:paragraph -->
<p>ちなみに、売却時の電話では、まず「ぶっちゃけ、いくらぐらいになりそうですか？」と聞いていました。<br>金額だけじゃなく、どこが買いたがっているかも探ります。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>手応えのあった会社には、こんな感じでひと押し。<br>「大体どこも同じ金額ですよね。正直、手間と時間が惜しいので、現地査定は一社にしたい。他社に負けない金額が出せそうなら、他社の現地査定を断ろうと思う」<br>これ、あとから考えた作戦じゃなくて、実際にやった交渉です。</p>
<!-- /wp:paragraph -->'''


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def visible(block: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", block)).strip()


def unique_paragraph(body: str, phrase: str):
    matches = [m for m in P_BLOCK.finditer(body) if phrase in visible(m.group(0))]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one paragraph matching {phrase!r}; got {len(matches)}")
    return matches[0]


def identity(row: dict) -> dict:
    return {k: row.get(k) for k in META_EXPECTED}


def transform(source: str) -> str:
    if MARKER_STATS in source or MARKER_CALLS in source:
        if (source.count(MARKER_STATS) == source.count(MARKER_CALLS) == 1
            and source.count("427万円 ÷ 616万円") == 1
            and source.count("ぶっちゃけ、いくらぐらいになりそうですか？") == 1
            and source.count('[blog_parts id="4521"]') == 1):
            return source
        raise RuntimeError("Partial or conflicting light-touch edit marker")
    if digest(source) != EXPECTED_SHA256:
        raise RuntimeError("Current WordPress content differs from reverted original; abort")

    stat = unique_paragraph(source, STAT_ANCHOR)
    caveat = unique_paragraph(source, FOLLOWING_CAVEAT)
    call = unique_paragraph(source, CALL_ANCHOR)
    onsite = unique_paragraph(source, FOLLOWING_ONSITE)

    if not (stat.end() < caveat.start() < call.start() < onsite.start()):
        raise RuntimeError("Original episode order changed; abort")
    if source[stat.end():caveat.start()].strip():
        raise RuntimeError("Unexpected content between old estimate summary and caveat")
    if source[call.end():onsite.start()].strip():
        raise RuntimeError("Unexpected content between CTN phone contacts and onsite story")

    # Positions are based on ORIGINAL source only, so the original paragraphs stay byte-for-byte.
    # Insert later anchor first to keep previous original offsets valid.
    augmented = source[:call.end()] + "\n\n" + MARKER_CALLS + "\n" + CALLS + source[call.end():]
    augmented = augmented[:stat.end()] + "\n\n" + MARKER_STATS + "\n" + STATS + augmented[stat.end():]

    # Stronger than comparing counted words: remove just the two inserted spans and
    # prove that every single byte of the 8969-character original remains untouched.
    reverted = augmented.replace("\n\n" + MARKER_STATS + "\n" + STATS, "", 1)
    reverted = reverted.replace("\n\n" + MARKER_CALLS + "\n" + CALLS, "", 1)
    if reverted != source or digest(reverted) != EXPECTED_SHA256:
        raise RuntimeError("Any original writing was rewritten or removed")

    if source.count("<!-- wp:paragraph") + 2 != augmented.count("<!-- wp:paragraph"):
        raise RuntimeError("Original paragraph blocks unexpectedly changed")
    if len(re.findall(r"<!-- wp:list(?:\\s|>)", source)) + 1 != len(re.findall(r"<!-- wp:list(?:\\s|>)", augmented)):
        raise RuntimeError("Only one small fact list may be added")
    for token in [
        "<!-- wp:heading", "<!-- wp:table", "<!-- wp:image", "<!-- wp:embed",
        '[blog_parts id="4521"]', "wp-image-2234", "wp-image-2230", "wp-image-2231",
    ]:
        if source.count(token) != augmented.count(token):
            raise RuntimeError(f"Protected Gutenberg resource changed: {token}")
    if source.count("href=") != augmented.count("href="):
        raise RuntimeError("Existing internal/external links changed")
    if len(re.findall(r'<!-- wp:list-item', augmented)) != len(re.findall(r'<!-- wp:list-item', source)) + 4:
        raise RuntimeError("New list must have exactly four numeric facts")
    if not (augmented.find(MARKER_STATS) < augmented.find(FOLLOWING_CAVEAT)
            < augmented.find(MARKER_CALLS) < augmented.find(FOLLOWING_ONSITE)):
        raise RuntimeError("Inserted content is out of episode sequence")
    return augmented


def apply_light_additions(config_path: Path, config: dict, auth: str, api):
    if (config.get("operation"), config.get("post_id"), config.get("slug"), config.get("expected_sha256")) != (
        "add_ux_resale_light_touch_20261113", POST_ID, SLUG, EXPECTED_SHA256
    ):
        raise RuntimeError("This package targets only the original UX resale post")
    fetch_post, raw_field, public_counts, post_json, site_url = api
    before = fetch_post(POST_ID, auth)
    if identity(before) != META_EXPECTED:
        raise RuntimeError("Post identity/status/featured image/categories/author changed")
    if html.unescape(raw_field(before, "title")) != TITLE:
        raise RuntimeError("Original title changed")
    old = raw_field(before, "content")
    new = transform(old)
    counts_before = public_counts(auth)
    fresh = fetch_post(POST_ID, auth)
    if identity(fresh) != identity(before):
        raise RuntimeError("Post metadata edited concurrently")
    if raw_field(fresh, "content") != old or raw_field(fresh, "title") != raw_field(before, "title"):
        raise RuntimeError("WordPress article edited concurrently; do not overwrite")
    action = "ALREADY_PRESENT" if new == old else "UPDATE"
    if action == "UPDATE":
        result = post_json(site_url + "/wp-json/wp/v2/posts/" + str(POST_ID), auth, {"content": new})
        if identity(result) != META_EXPECTED:
            raise RuntimeError("WordPress returned changed post identity")
    saved = fetch_post(POST_ID, auth)
    if identity(saved) != META_EXPECTED or html.unescape(raw_field(saved, "title")) != TITLE:
        raise RuntimeError("Post metadata/title changed after save")
    if raw_field(saved, "content") != new:
        raise RuntimeError("Saved live WordPress content does not match exact additions")
    counts_after = public_counts(auth)
    if counts_after != counts_before:
        raise RuntimeError("Published post/page count unexpectedly changed")

    report = {
        "post_id": POST_ID, "slug": SLUG, "status": "publish", "title": TITLE,
        "action": action, "writes": 1 if action == "UPDATE" else 0,
        "old_sha": digest(old), "new_sha": digest(new),
        "original_text_preserved_byte_for_byte": True,
        "paragraph_blocks_before": old.count("<!-- wp:paragraph"),
        "paragraph_blocks_after": new.count("<!-- wp:paragraph"),
        "heading_blocks_unchanged": old.count("<!-- wp:heading"),
        "image_blocks_unchanged": old.count("<!-- wp:image"),
        "stats_list_items_added": 4, "phone_paragraphs_added": 2,
        "ctn_shortcode_preserved": '[blog_parts id="4521"]' in new,
        "published_before": counts_before, "published_after": counts_after,
    }
    out = Path("reports/ux-resale-light-touch-20261113")
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "summary.md").write_text("# UX resale: original preserved, light additions only\n\n"
                                   + json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("UX_RESALE_LIGHT_ADDITIONS_RESULT", json.dumps(report, ensure_ascii=False), flush=True)
    return report
