#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

SITE_URL = "https://tsurikue.com"
POST_ID = 2222
EXPECTED_SLUG = "ux-resale"
EXPECTED_STATUS = "publish"
EXPECTED_TITLE = "レクサスUXのリセールは？616万円で購入し427万円で売却した記録"
EXPECTED_FEATURED_MEDIA = 2223
EXPECTED_SOURCE_SHA = "6c348694217e8de9c77652eb44267bcdea1d0d967a377410e6d723ec5b77080a"
EXPECTED_RESULT_SHA = "7dd85f21d943c2ba76cf88ee3a1378460232410ebd5acb0b2f21d87776551bda"
REPORT_DIR = Path("reports/fix-ux-resale-timeline-20260907")
CTN_BANNER = '[blog_parts id="2846"]'
CTN_BUTTON = '[blog_parts id="2184"]'
USER_AGENT = "tsurikue-fix-ux-resale-timeline-20260907/1.0"

TOKEN_RE = re.compile(r"<!--\s+/?wp:[\s\S]*?-->")
OPEN_RE = re.compile(r"<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->")
CLOSE_RE = re.compile(r"<!--\s+/wp:([\w\-/]+)\s+-->")
LEAF = {"paragraph", "heading"}

REPLACEMENTS = [
    (
        '<p>納車約5か月・5,000kmの同じ頃に受けた査定が、<strong>レクサスディーラー350万円</strong>と<strong>別の実車査定500万円前後</strong>。<br>同じUXなのに、約150万円差がありました。</p>',
        '<p>納車から約3か月ごろ。UXを売るつもりはなく、<strong>「今いくらなんだろう？」という好奇心</strong>で査定してみました。<br>そのときの査定が、レクサスディーラー350万円と別の一括査定500万円前後。同じUXなのに、約150万円差がありました。</p>',
    ),
    (
        '<p><strong>車の査定、1社だけ見て決めるのは怖い。</strong><br>この記事は、まだ売るつもりがなかった頃の査定から、2025年2月にカーセブンへ427万円で実際に売却するまでの記録です。</p>',
        '<p><strong>車の査定、1社だけ見て決めるのは怖い。</strong><br>この記事は、納車から約3か月ごろに好奇心で査定したところから、約2年後の2025年2月にカーセブンへ427万円で実際に売却するまでの記録です。</p>',
    ),
    (
        '<tr><td>2023年11月<br>納車約5か月・5,000km</td><td>レクサスディーラー<br>実車査定</td><td><strong>350万円</strong></td><td>売却せず</td></tr><tr><td>2023年11月<br>納車約5か月・5,000km</td><td>当時利用した別の査定サービス<br>実車査定</td><td><strong>500万円前後</strong></td><td>売却せず</td></tr>',
        '<tr><td>納車から約3か月ごろ<br>約5,000km</td><td>レクサスディーラー<br>実車査定</td><td><strong>350万円</strong></td><td>好奇心で査定・売却せず</td></tr><tr><td>納車から約3か月ごろ<br>約5,000km</td><td>当時利用した別の一括査定サービス<br>実車査定</td><td><strong>500万円前後</strong></td><td>好奇心で査定・売却せず</td></tr>',
    ),
    (
        '<tr><td>2025年2月<br>前回の実車査定から半年近く経過</td><td>CTN経由のカーセブン<br>実車査定・買取</td><td><strong>427万円</strong></td><td>実際に売却</td></tr>',
        '<tr><td>納車から約2年<br>2025年2月</td><td>CTN経由のカーセブン<br>実車査定・買取</td><td><strong>427万円</strong></td><td>実際に売却</td></tr>',
    ),
    (
        '<!-- wp:paragraph -->\n<p><strong>ここまで査定額が動くなら、自分の車も1社だけでは判断しにくい。</strong><br>CTNは最大15社で査定し、高額査定の上位3社とやり取りする仕組みです。</p>\n<!-- /wp:paragraph -->',
        '<!-- wp:paragraph -->\n<p><strong>ちなみに、納車から約3か月ごろの500万円前後はCTNの査定ではありません。</strong><br>私がCTNを使ったのは約2年後、実際にUXを売ると決めたときです。</p>\n<!-- /wp:paragraph -->\n\n<!-- wp:paragraph -->\n<p>最初の好奇心査定で「査定先によって、ここまで金額が違うのか」と知っていたので、実際の売却でも1社だけでは決めませんでした。<br>CTNは最大15社で査定し、高額査定の上位3社とやり取りする仕組みです。</p>\n<!-- /wp:paragraph -->',
    ),
    (
        '<h2 class="wp-block-heading">納車5か月のディーラー査定は350万円だった</h2>',
        '<h2 class="wp-block-heading">納車3か月ごろ、好奇心で査定したら350万円だった</h2>',
    ),
    (
        '<p>納車から約5か月、走行距離5,000kmの頃。<br>いつものレクサスディーラーで査定してもらうと、提示額は<strong>350万円</strong>でした。</p>',
        '<p>納車から約3か月ごろ、走行距離は約5,000km。<br>この時点ではUXを売るつもりはなく、「今いくらなんだろう？」という好奇心で、いつものレクサスディーラーに査定してもらいました。提示額は<strong>350万円</strong>でした。</p>',
    ),
    (
        '<p>616万円で購入してまだ5か月。オプションや諸費用込みの購入額と単純比較できないのは分かっています。<br><strong>それでも350万円は、かなりへこみました。</strong></p>',
        '<p>616万円で購入してまだ数か月。オプションや諸費用込みの購入額と単純比較できないのは分かっています。<br><strong>それでも350万円は、かなりへこみました。</strong></p>',
    ),
    (
        '<h2 class="wp-block-heading">同じ時期、別の実車査定では500万円前後だった</h2>',
        '<h2 class="wp-block-heading">同じ頃、別の一括査定では500万円前後だった</h2>',
    ),
    (
        '<p>ディーラー査定と同じ頃、別の査定サービスでもUXを見てもらいました。</p>',
        '<p>ディーラー査定と同じ頃、今度は別の一括査定サービスでもUXを見てもらいました。<br>こちらも売るためではなく、好奇心からの査定です。</p>',
    ),
    (
        '<p>ただし、500万円前後はあくまで提示額。この時点ではUXを売っていません。</p>',
        '<p>ただし、500万円前後はあくまで提示額です。<br>この時点では売却せず、そのままUXに乗り続けました。実際に売ったのは、納車から約2年後です。</p>',
    ),
    (
        '<p>私のUXの記録をまとめると、<strong>ディーラー350万円 → 別の実車査定500万円前後 → 約1年後435万円 → 最終427万円で売却</strong>でした。</p>',
        '<p>私のUXの記録をまとめると、<strong>納車約3か月の好奇心査定でディーラー350万円 → 別の一括査定500万円前後 → 約1年後435万円 → 納車約2年で427万円で売却</strong>でした。</p>',
    ),
]


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def request_json(url: str, auth: str, method: str = "GET", payload=None):
    data = None
    headers = {"Accept": "application/json", "Authorization": auth, "User-Agent": USER_AGENT}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8")), dict(response.headers)


def raw_field(row, key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_post(auth: str):
    row, _ = request_json(f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}?context=edit", auth)
    return row


def get_published_count(auth: str) -> int:
    _, headers = request_json(f"{SITE_URL}/wp-json/wp/v2/posts?status=publish&per_page=1&_fields=id", auth)
    return int(headers.get("X-WP-Total", 0))


def block_problems(text: str):
    stack = []
    problems = []
    for m in TOKEN_RE.finditer(text):
        token = m.group(0)
        om = OPEN_RE.fullmatch(token)
        cm = CLOSE_RE.fullmatch(token)
        if om:
            name = om.group(1)
            if om.group(2):
                continue
            if stack and stack[-1] in LEAF:
                problems.append(("nested_inside_leaf", stack[-1], name))
            stack.append(name)
        elif cm:
            name = cm.group(1)
            if not stack:
                problems.append(("orphan_close", name))
            elif stack[-1] == name:
                stack.pop()
            else:
                problems.append(("mismatched_close", stack[-1], name))
                if name in stack:
                    while stack and stack[-1] != name:
                        stack.pop()
                    if stack:
                        stack.pop()
    if stack:
        problems.append(("unclosed", tuple(stack)))
    return problems


def build(source: str) -> str:
    if sha(source) != EXPECTED_SOURCE_SHA:
        raise RuntimeError(f"source hash changed: {sha(source)}")
    if block_problems(source):
        raise RuntimeError(f"source Gutenberg structure is broken: {block_problems(source)}")
    if source.count(CTN_BANNER) != 3 or source.count(CTN_BUTTON) != 1:
        raise RuntimeError("unexpected CTN counts before update")
    if len(re.findall(r'<!-- wp:image\b.*?<!-- /wp:image -->', source, re.S)) != 3:
        raise RuntimeError("unexpected image-block count before update")

    out = source
    for old, new in REPLACEMENTS:
        count = out.count(old)
        if count != 1:
            raise RuntimeError(f"replacement anchor count={count}: {old[:90]}")
        out = out.replace(old, new)

    if sha(out) != EXPECTED_RESULT_SHA:
        raise RuntimeError(f"result hash mismatch: {sha(out)}")
    if block_problems(out):
        raise RuntimeError(f"result Gutenberg structure is broken: {block_problems(out)}")
    if out.count(CTN_BANNER) != 3 or out.count(CTN_BUTTON) != 1:
        raise RuntimeError("CTN counts changed")
    if len(re.findall(r'<!-- wp:image\b.*?<!-- /wp:image -->', out, re.S)) != 3:
        raise RuntimeError("image-block count changed")
    for marker in [
        "今いくらなんだろう？",
        "納車から約3か月ごろの500万円前後はCTNの査定ではありません",
        "私がCTNを使ったのは約2年後",
        "納車約2年で427万円で売却",
    ]:
        if marker not in out:
            raise RuntimeError("required marker missing: " + marker)
    return out


def main():
    user = os.environ["TSURIKUE_WP_USER"]
    password = os.environ["TSURIKUE_WP_APP_PASSWORD"]
    auth = auth_header(user, password)

    before = get_post(auth)
    source = raw_field(before, "content")
    if before.get("id") != POST_ID or before.get("slug") != EXPECTED_SLUG:
        raise RuntimeError("post identity mismatch")
    if before.get("status") != EXPECTED_STATUS:
        raise RuntimeError("post is not publish")
    if raw_field(before, "title") != EXPECTED_TITLE:
        raise RuntimeError("title mismatch")
    if before.get("featured_media") != EXPECTED_FEATURED_MEDIA:
        raise RuntimeError("featured media mismatch")

    public_before = get_published_count(auth)
    fixed = build(source)

    request_json(
        f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}",
        auth,
        method="POST",
        payload={"content": fixed},
    )

    after = get_post(auth)
    result = raw_field(after, "content")
    public_after = get_published_count(auth)

    if sha(result) != EXPECTED_RESULT_SHA:
        raise RuntimeError("post-update content mismatch")
    if after.get("status") != EXPECTED_STATUS or after.get("slug") != EXPECTED_SLUG:
        raise RuntimeError("post identity/status changed")
    if raw_field(after, "title") != EXPECTED_TITLE:
        raise RuntimeError("title changed")
    if after.get("featured_media") != EXPECTED_FEATURED_MEDIA:
        raise RuntimeError("featured media changed")
    if public_after != public_before:
        raise RuntimeError("published post count changed")
    if block_problems(result):
        raise RuntimeError("Gutenberg structure broken after WordPress save")

    report = {
        "result": "SUCCESS",
        "post_id": POST_ID,
        "slug": EXPECTED_SLUG,
        "status_before": before.get("status"),
        "status_after": after.get("status"),
        "featured_media_before": before.get("featured_media"),
        "featured_media_after": after.get("featured_media"),
        "public_before": public_before,
        "public_after": public_after,
        "source_sha": sha(source),
        "result_sha": sha(result),
        "gutenberg_problems_before": len(block_problems(source)),
        "gutenberg_problems_after": len(block_problems(result)),
        "ctn_banner_count": result.count(CTN_BANNER),
        "ctn_button_count": result.count(CTN_BUTTON),
        "image_block_count": len(re.findall(r'<!-- wp:image\b.*?<!-- /wp:image -->', result, re.S)),
        "wordpress_write_count": 1,
        "payload_fields": ["content"],
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = "\n".join([
        "# UX resale timeline correction",
        "",
        "- result: **SUCCESS**",
        f"- post_id: **{POST_ID}**",
        f"- slug: `{EXPECTED_SLUG}`",
        f"- status: **{before.get('status')} → {after.get('status')}**",
        f"- featured_media: **{before.get('featured_media')} → {after.get('featured_media')}**",
        f"- public_posts: **{public_before} → {public_after}**",
        f"- Gutenberg problems: **{len(block_problems(source))} → {len(block_problems(result))}**",
        f"- CTN banners: **{result.count(CTN_BANNER)}**",
        f"- CTN buttons: **{result.count(CTN_BUTTON)}**",
        f"- image blocks: **{report['image_block_count']}**",
        "- corrected: **trial appraisal ≈ 3 months / actual sale ≈ 2 years**",
        "- clarified: **the ~¥5.0M trial appraisal was not CTN; CTN was used for the later actual sale**",
        "- payload_fields: **content only**",
        "- wordpress_write_count: **1**",
    ]) + "\n"
    (REPORT_DIR / "summary.md").write_text(summary, encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()
