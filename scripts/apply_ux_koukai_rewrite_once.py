#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

SITE_URL = "https://tsurikue.com"
SLUG = "ux-koukai"
EXPECTED_TITLE = "レクサスUXはひどい？616万円で買って後悔した欠点と満足している理由"
USER_AGENT = "tsurikue-ux-koukai-rewrite-once/1.0"
REPORT_DIR = Path("reports/ux-koukai-rewrite-once")

GULLIVER_BANNER_ID = '2843'
CTN_BANNER_ID = '2846'
CTN_BUTTON_ID = '2184'
GULLIVER_A8_HREF = "https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY"
GULLIVER_PIXEL = "https://www15.a8.net/0.gif?a8mat=4B65SD+8DUSHE+9QU+NVHCY"


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def get_json(url: str, auth: str):
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "Authorization": auth, "User-Agent": USER_AGENT},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.loads(response.read().decode("utf-8")), dict(response.headers)


def post_json(url: str, auth: str, payload: dict[str, Any]):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": auth,
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def raw_field(row: dict[str, Any], key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)


def fetch_post_by_slug(auth: str) -> dict[str, Any]:
    query = urllib.parse.urlencode({
        "context": "edit",
        "slug": SLUG,
        "status": "publish,draft,pending,private,future",
        "per_page": "10",
        "_fields": "id,slug,status,title,content,featured_media,modified",
    })
    rows, _ = get_json(f"{SITE_URL}/wp-json/wp/v2/posts?{query}", auth)
    matches = [row for row in rows if row.get("slug") == SLUG]
    if len(matches) != 1:
        raise RuntimeError(f"expected one post for slug {SLUG!r}, got {len(matches)}")
    return matches[0]


def count_published(endpoint: str, auth: str) -> int:
    query = urllib.parse.urlencode({"context": "edit", "status": "publish", "per_page": "1", "_fields": "id"})
    _, headers = get_json(f"{SITE_URL}/wp-json/wp/v2/{endpoint}?{query}", auth)
    return int(headers.get("X-WP-Total", "0"))


def public_total(auth: str) -> int:
    return count_published("posts", auth) + count_published("pages", auth)


def heading_block_start(content: str, heading_text: str) -> int:
    idx = content.find(heading_text)
    if idx < 0:
        raise RuntimeError(f"heading not found: {heading_text}")
    comment_idx = content.rfind("<!-- wp:heading", 0, idx)
    h2_idx = content.rfind("<h2", 0, idx)
    start = max(comment_idx, h2_idx)
    if start < 0:
        raise RuntimeError(f"heading block start not found: {heading_text}")
    return start


def replace_h2_range(content: str, start_heading: str, end_heading: str, replacement: str) -> str:
    start = heading_block_start(content, start_heading)
    end = heading_block_start(content, end_heading)
    if end <= start:
        raise RuntimeError(f"bad heading order: {start_heading} -> {end_heading}")
    return content[:start] + replacement.strip() + "\n\n" + content[end:]


def replace_last_h2_to_end(content: str, start_heading: str, replacement: str) -> str:
    start = heading_block_start(content, start_heading)
    return content[:start] + replacement.strip() + "\n"


def insert_before_h2(content: str, heading_text: str, insertion: str) -> str:
    idx = heading_block_start(content, heading_text)
    return content[:idx] + insertion.strip() + "\n\n" + content[idx:]


def replace_exact_once(content: str, old: str, new: str) -> str:
    count = content.count(old)
    if count != 1:
        raise RuntimeError(f"expected exactly one occurrence of {old!r}, got {count}")
    return content.replace(old, new, 1)


def shortcode_block(shortcode: str) -> str:
    return f"<!-- wp:shortcode -->\n{shortcode}\n<!-- /wp:shortcode -->"


CONCLUSION_SECTION = r'''
<!-- wp:heading -->
<h2 class="wp-block-heading">結論｜レクサスUXはひどくない。でも616万円で見ると気になる</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>先に答えを言うと、<strong>レクサスUXはひどい車ではありません。</strong><br>私はかなり好きでしたし、買ったこと自体も後悔していません。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ただし。<br><strong>約616万円で買った車</strong>として見ると、「いや、ここはもう少し頑張ってよ🤣」と思うところは普通にありました。</p>
<!-- /wp:paragraph -->

<!-- wp:table -->
<figure class="wp-block-table"><table><tbody>
<tr><th>気になったところ</th><th>私の本音</th></tr>
<tr><td>後部座席</td><td><strong>正直、狭い</strong></td></tr>
<tr><td>荷室</td><td><strong>広さより高さがつらい</strong></td></tr>
<tr><td>内装</td><td>前席は良い。でも<strong>後席はあっさり</strong></td></tr>
<tr><td>外装</td><td>フェンダーアーチの線がずっと気になる</td></tr>
<tr><td>購入タイミング</td><td>納車半年後にUX300h。<strong>タイミング悪すぎ</strong></td></tr>
<tr><td>査定</td><td>ディーラー350万円。<strong>これは衝撃</strong></td></tr>
</tbody></table></figure>
<!-- /wp:table -->

<!-- wp:paragraph -->
<p>でも、今UXを買う人は私と少し条件が違います。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>2026年8月時点、新車のUXは500万円台。<br>一方で中古を見ると、<strong>200〜300万円台のUXが現実的に狙えるようになっています。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>616万円で見ると気になった欠点も、250万円や300万円のレクサスとして考えると……。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>いや、めちゃくちゃ良くない？</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>これが、いま元オーナーの私がUXを見ていて一番感じることです。<br>だが！UXの方が好きなのでしょうがない。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>中古UX、ちょっと気になるな。</strong><br>そう思ったら、まず今どんな車が出ているか眺めてみるだけでも楽しいですよ。</p>
<!-- /wp:paragraph -->

<!-- wp:shortcode -->
[blog_parts id="2843"]
<!-- /wp:shortcode -->

<!-- wp:paragraph -->
<p><small>※中古車価格は年式・走行距離・グレード・車両状態などで変わります。この記事内の価格感は2026年8月に確認した掲載状況をもとにしています。</small></p>
<!-- /wp:paragraph -->
'''

CTN_EARLY = r'''
<!-- wp:paragraph -->
<p>そしてもうひとつ。<br>中古UXを見て「この値段ならいけるかも」と思ったら、<strong>今の車がいくらになるか</strong>も見ておくと予算がかなり分かりやすくなります。</p>
<!-- /wp:paragraph -->

<!-- wp:shortcode -->
[blog_parts id="2846"]
<!-- /wp:shortcode -->
'''

USED_SECTION = r'''
<!-- wp:heading -->
<h2 class="wp-block-heading">今からレクサスUXを買うなら、私は中古を選ぶ</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>私はUX250hを新車で買いました。<br>支払総額は約616万円。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>それでも満足していたので、新車で買ったことを後悔しているわけではありません。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>でも<strong>今からもう一度UXを買うなら、私は中古を選びます。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">200〜300万円台なら、UXの弱点がかなり許せる</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>後席は狭い。<br>荷室も大きくない。<br>後席側の内装は、前席ほど気合いが入っていない。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>このあたりは、中古になっても変わりません。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ただ、私が気になったのは<strong>「616万円払った車として見たとき」</strong>という部分もかなり大きいです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>これが200〜300万円台になってくると、見え方はかなり変わります。</p>
<!-- /wp:paragraph -->

<!-- wp:list -->
<ul><li>運転しやすいサイズ</li><li>静かで乗り心地が良い</li><li>前席の質感はしっかりレクサス</li><li>長距離でも疲れにくい</li><li>見た目はいま見ても好き</li></ul>
<!-- /wp:list -->

<!-- wp:paragraph -->
<p>このクルマがその価格なら、<strong>私はかなり満足度が高いと思います。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">UX250hも、急に古くてダメな車になったわけじゃない</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>UX300hは確実に進化しています。<br>私も実際に試乗して、液晶メーターなんかは普通にうらやましかったです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>でも、走ってみて<strong>UX250hが急に古くてダメな車になったとは感じませんでした。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>新しさや燃費を重視するならUX300h。<br>価格と装備のバランスを重視するならUX250h。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>この選び方で良いと思います。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><a href="https://tsurikue.com/ux300h/">UX250hオーナーだった私がUX300hへ試乗して比べた記事はこちら</a></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph {"align":"center"} -->
<p class="has-text-align-center"><strong>200〜300万円台のUX、ちょっと見てみる？</strong></p>
<!-- /wp:paragraph -->

<!-- wp:html -->
<div style="text-align:center;margin:1em 0 2em;">
<a href="https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY" rel="nofollow" style="display:inline-block;padding:14px 24px;border-radius:999px;background:#222;color:#fff;text-decoration:none;font-weight:700;">ガリバーで中古のレクサスUXを探してみる</a>
<img border="0" width="1" height="1" src="https://www15.a8.net/0.gif?a8mat=4B65SD+8DUSHE+9QU+NVHCY" alt="">
</div>
<!-- /wp:html -->

<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">手持ちの車が高く売れれば、中古UXはさらに狙いやすい</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>中古UXを見ていると、200万円台や300万円台が見えてきます。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>すると次に気になるのが、<strong>「今の車、いくらで売れるんだろ？」</strong>ですよね。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>私のUXは、ディーラー査定350万円に対して、一括査定では最高500万円近い提示が出ました。<br>最終的には427万円で売却しています。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>査定先で金額が変わることは普通にあります。<br>今の車が高く売れれば、そのぶん次のUXに使える予算も増えます。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph {"align":"center"} -->
<p class="has-text-align-center"><strong>今の車、思ったより高く売れるかも。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:shortcode -->
[blog_parts id="2184"]
<!-- /wp:shortcode -->

<!-- wp:paragraph -->
<p><small>※査定額は車種、年式、走行距離、車両状態、査定時期などによって異なります。</small></p>
<!-- /wp:paragraph -->
'''

SUMMARY_SECTION = r'''
<!-- wp:heading -->
<h2 class="wp-block-heading">まとめ｜UXは高くて狭い。でも中古なら話が変わる</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>レクサスUXは、万人向けのSUVではありません。</p>
<!-- /wp:paragraph -->

<!-- wp:list -->
<ul><li><strong>後席は狭い</strong></li><li><strong>荷室も大きくない</strong></li><li>後席側の内装は前席よりあっさり</li><li>フェンダーアーチの線が私は気になった</li><li>私の場合は納車半年後にUX300hが登場</li><li>ディーラー査定350万円にはへこんだ</li></ul>
<!-- /wp:list -->

<!-- wp:paragraph -->
<p>約616万円で買った私は、このあたりに普通に文句があります🤣</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>でも、それでもUXは好きでした。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>大きすぎない。<br>運転しやすい。<br>静か。<br>長距離も楽。<br>そして、見るたびにちょっと嬉しい。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>UXに乗ってから、山陰、角島、淡路島と、クルマで出かけることそのものが楽しくなりました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>だから私の結論は、以前より少し変わっています。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>新車で500万円台のUXなら、欠点まで理解して選びたい。</strong><br><strong>でも200〜300万円台の中古UXなら、かなり魅力的。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>広さが必要ならNXや別のSUVを選べばいい。<br>1〜2人で乗ることが多くて、「小さな高級車」が欲しいならUXは今でも面白い選択肢だと思います。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>私はUXの方が好きでした。<br><strong>だから仕方ありません。</strong></p>
<!-- /wp:paragraph -->
'''


def desired_content(current: str) -> str:
    body = current

    # Restore a little of the old tsurikue voice in the introduction and complaints.
    body = replace_exact_once(
        body,
        "この記事では、「レクサスUX ひどい」「レクサスUX 後悔」と調べている人に向けて、実際に所有して後悔した点、それでも満足している理由を、元オーナーの本音で書いていきます。",
        "ということで、UXが好きだった元オーナーの私が、良いところも悪いところもまとめてぶちまけます。購入前に「ほんとに大丈夫？」と気になっている人は、そのままゆるーく読んでみてください。",
    )
    body = replace_exact_once(body, "ここは無理にかばえません。", "ここは、かばえません🤣")
    body = replace_exact_once(body, "タイミングが悪すぎる。", "いや、タイミング悪すぎるって🤣")
    body = replace_exact_once(
        body,
        "でも、細かい。\n細かいけど、一度気になるとずっと気になるんです。",
        "でも、細かい。\nめちゃくちゃ細かい。\nそれでも一度気になると、洗車のたびに目が行くんです。",
    )

    # Replace the opening conclusion with a scan-friendly verdict + first Gulliver banner.
    body = replace_h2_range(
        body,
        "結論｜レクサスUXはひどい車ではない。でも後悔する人はいる",
        "レクサスUXを買って「ひどい」と感じた6つの欠点",
        CONCLUSION_SECTION,
    )

    # First CTN banner lands immediately after the six concrete complaints/appraisal story.
    body = insert_before_h2(body, "それでもレクサスUXを買って後悔していない理由", CTN_EARLY)

    # Collapse the duplicated audience/checklist sections into one strong used-UX section.
    body = replace_h2_range(
        body,
        "レクサスUXで後悔しやすい人・満足しやすい人",
        "レクサスUXに関するよくある質問",
        USED_SECTION,
    )

    # Replace the final repeated CTA-heavy summary with a shorter tsurikue-style ending.
    body = replace_last_h2_to_end(
        body,
        "まとめ｜レクサスUXは広さで選ぶと後悔する。でも小さな高級車としては魅力的",
        SUMMARY_SECTION,
    )

    # Guard the intended affiliate layout: early banners + late microcopy/buttons.
    if body.count(f'[blog_parts id="{GULLIVER_BANNER_ID}"]') != 1:
        raise RuntimeError("unexpected Gulliver banner count")
    if body.count(f'[blog_parts id="{CTN_BANNER_ID}"]') != 1:
        raise RuntimeError("unexpected CTN banner count")
    if body.count(f'[blog_parts id="{CTN_BUTTON_ID}"]') != 1:
        raise RuntimeError("unexpected CTN button count")
    if body.count(GULLIVER_A8_HREF) != 1 or body.count(GULLIVER_PIXEL) != 1:
        raise RuntimeError("unexpected Gulliver free-text tracking count")

    # We deliberately keep the existing title, slug, featured image, FAQ and article images.
    return body


def write_report(report: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# ux-koukai rewrite",
        "",
        f"- result: **{report['result']}**",
        f"- post_id: **{report.get('post_id', 'unknown')}**",
        f"- slug: **{SLUG}**",
        f"- status: **{report.get('status', 'unknown')}**",
        f"- title: {report.get('title', '')}",
        f"- featured_media: **{report.get('featured_media', 0)}**",
        f"- public_before: **{report.get('public_before', 'unknown')}**",
        f"- public_after: **{report.get('public_after', 'unknown')}**",
        f"- wordpress_write_count: **{report.get('wordpress_write_count', 0)}**",
        f"- source_content_sha256: `{report.get('source_content_sha256', '')}`",
        f"- content_sha256: `{report.get('content_sha256', '')}`",
        f"- gulliver_banner_count: **{report.get('gulliver_banner_count', 0)}**",
        f"- gulliver_button_count: **{report.get('gulliver_button_count', 0)}**",
        f"- ctn_banner_count: **{report.get('ctn_banner_count', 0)}**",
        f"- ctn_button_count: **{report.get('ctn_button_count', 0)}**",
    ]
    if report.get("error"):
        lines.append(f"- error: `{report['error']}`")
    (REPORT_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    report: dict[str, Any] = {
        "result": "BLOCKED",
        "status": "unknown",
        "title": "",
        "post_id": "unknown",
        "featured_media": 0,
        "public_before": "unknown",
        "public_after": "unknown",
        "wordpress_write_count": 0,
        "source_content_sha256": "",
        "content_sha256": "",
        "gulliver_banner_count": 0,
        "gulliver_button_count": 0,
        "ctn_banner_count": 0,
        "ctn_button_count": 0,
    }
    try:
        user = os.environ.get("TSURIKUE_WP_USER")
        password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
        if not user or not password:
            raise RuntimeError("missing WordPress secrets")
        auth = auth_header(user, password)

        before_total = public_total(auth)
        before = fetch_post_by_slug(auth)
        current = raw_field(before, "content")
        current_title = html.unescape(raw_field(before, "title"))
        current_status = before.get("status")
        post_id = int(before.get("id") or 0)
        featured_media = int(before.get("featured_media") or 0)
        current_sha = hashlib.sha256(current.encode()).hexdigest()

        report.update({
            "post_id": post_id,
            "status": current_status,
            "title": current_title,
            "featured_media": featured_media,
            "public_before": before_total,
            "source_content_sha256": current_sha,
        })

        if current_status != "publish":
            raise RuntimeError(f"target is not publish: {current_status}")
        if current_title != EXPECTED_TITLE:
            raise RuntimeError(f"title mismatch: {current_title!r}")
        if post_id <= 0:
            raise RuntimeError("invalid post id")

        required_text = [
            "レクサスUXを買って「ひどい」と感じた6つの欠点",
            "それでもレクサスUXを買って後悔していない理由",
            "レクサスUXで後悔しやすい人・満足しやすい人",
            "レクサスUXで後悔しないために購入前に確認したいこと",
            "レクサスUXに関するよくある質問",
            "まとめ｜レクサスUXは広さで選ぶと後悔する。でも小さな高級車としては魅力的",
        ]
        missing = [x for x in required_text if x not in current]
        if missing:
            raise RuntimeError(f"current article structure changed; missing anchors: {missing}")

        desired = desired_content(current)
        desired_sha = hashlib.sha256(desired.encode()).hexdigest()
        if desired_sha == current_sha:
            raise RuntimeError("rewrite produced no change")

        response = post_json(
            f"{SITE_URL}/wp-json/wp/v2/posts/{post_id}",
            auth,
            {"content": desired, "status": "publish"},
        )
        if int(response.get("id") or 0) != post_id or response.get("status") != "publish":
            raise RuntimeError("update response validation failed")

        after = fetch_post_by_slug(auth)
        after_total = public_total(auth)
        after_content = raw_field(after, "content")
        after_title = html.unescape(raw_field(after, "title"))
        after_featured = int(after.get("featured_media") or 0)

        if before_total != after_total:
            raise RuntimeError("published counts changed")
        if after.get("status") != "publish" or after.get("slug") != SLUG:
            raise RuntimeError("post-update state mismatch")
        if after_title != EXPECTED_TITLE:
            raise RuntimeError("post-update title changed")
        if after_featured != featured_media:
            raise RuntimeError("featured_media changed")
        if after_content.strip() != desired.strip():
            raise RuntimeError("post-update content mismatch")

        report.update({
            "result": "SUCCESS",
            "status": "publish",
            "title": after_title,
            "featured_media": after_featured,
            "public_after": after_total,
            "wordpress_write_count": 1,
            "content_sha256": hashlib.sha256(after_content.encode()).hexdigest(),
            "gulliver_banner_count": after_content.count(f'[blog_parts id="{GULLIVER_BANNER_ID}"]'),
            "gulliver_button_count": after_content.count(GULLIVER_A8_HREF),
            "ctn_banner_count": after_content.count(f'[blog_parts id="{CTN_BANNER_ID}"]'),
            "ctn_button_count": after_content.count(f'[blog_parts id="{CTN_BUTTON_ID}"]'),
        })
        write_report(report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        report["error"] = str(exc)
        try:
            write_report(report)
        except Exception:
            pass
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
