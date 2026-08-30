#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

SITE_URL = "https://tsurikue.com"
SLUG = "hiroshima-bokujyou"
EXPECTED_OLD_TITLE = "広島周辺の遊べる牧場へ｜ジェラート食べ比べドライブ旅"
NEW_TITLE = "広島の遊べる牧場5選｜ジェラート食べ比べ！子連れ・ドライブにおすすめ"
USER_AGENT = "tsurikue-hiroshima-bokujyou-reader-first/1.0"
REPORT_DIR = Path("reports/hiroshima-bokujyou-reader-first")
MARKER = "<!-- tsurikue-editorial:hiroshima-bokujyou:reader-first-v1 -->"


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def request_json(url: str, auth: str, *, method: str = "GET", payload: dict[str, Any] | None = None):
    data = None
    headers = {
        "Accept": "application/json",
        "Authorization": auth,
        "User-Agent": USER_AGENT,
    }
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    last: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=75) as response:
                return json.loads(response.read().decode("utf-8")), dict(response.headers)
        except Exception as exc:
            last = exc
            if attempt == 2:
                raise
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(str(last))


def raw_field(row: dict[str, Any], key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def count_published(endpoint: str, auth: str) -> int:
    query = urllib.parse.urlencode({
        "context": "edit",
        "status": "publish",
        "per_page": "1",
        "_fields": "id",
    })
    _, headers = request_json(f"{SITE_URL}/wp-json/wp/v2/{endpoint}?{query}", auth)
    return int(headers.get("X-WP-Total", "0"))


def public_counts(auth: str) -> dict[str, int]:
    posts = count_published("posts", auth)
    pages = count_published("pages", auth)
    return {"published_posts": posts, "published_pages": pages, "published_total": posts + pages}


def fetch_target(auth: str) -> dict[str, Any]:
    params = {
        "context": "edit",
        "status": "publish",
        "slug": SLUG,
        "per_page": "100",
        "_fields": "id,slug,status,title,content,excerpt,featured_media,categories,modified,link",
    }
    rows, _ = request_json(f"{SITE_URL}/wp-json/wp/v2/posts?{urllib.parse.urlencode(params)}", auth)
    if len(rows) != 1:
        raise RuntimeError(f"expected exactly one published /{SLUG}/ post, got {len(rows)}")
    return rows[0]


def image_blocks(content: str) -> list[str]:
    return re.findall(r"<!-- wp:image\b.*?<!-- /wp:image -->", content, flags=re.S)


def wp_p(text: str) -> str:
    return f'<!-- wp:paragraph -->\n<p>{text}</p>\n<!-- /wp:paragraph -->'


def wp_h2(text: str) -> str:
    return f'<!-- wp:heading -->\n<h2 class="wp-block-heading">{text}</h2>\n<!-- /wp:heading -->'


def wp_h3(text: str) -> str:
    return f'<!-- wp:heading {{"level":3}} -->\n<h3 class="wp-block-heading">{text}</h3>\n<!-- /wp:heading -->'


def build_content(images: list[str]) -> str:
    if len(images) < 8:
        raise RuntimeError(f"too few existing image blocks to preserve: {len(images)}")

    def img(index: int) -> str:
        return images[index] if index < len(images) else ""

    parts: list[str] = [MARKER]
    parts += [
        wp_p("広島で「次の休み、どこ行こう？」と迷ったら、牧場もけっこう面白いです。"),
        wp_p("動物とふれあえる。<br>自然の中で遊べる。<br>そして、牧場ならではのジェラートやチーズが旨い。"),
        wp_p("今回紹介するのは、実際に訪れた<strong>上ノ原牧場カドーレ、十夢ミルクファーム、ジェラート工房Donna、ふくふく牧場、久保アグリファーム</strong>の5か所です。"),
        wp_p("同じ牧場でも、行ってみると雰囲気はかなり違います。ジェラートを目当てに行きたい場所、子どもと動物を見たい場所、周辺観光までセットで楽しみやすい場所。目的に合わせて選べます。"),
        wp_p("そしてジェラートも、食べ比べるとちゃんと違う。<br><strong>「全部おいしい」で終わりそうなんですけど、違いはありました。</strong>"),
        img(0),
        wp_h2("広島の遊べる牧場5選をざっくり比較"),
        wp_p("最初に「どこへ行こう？」だけ決めたい人向けに、実際に食べた印象とおすすめの楽しみ方をまとめます。"),
        '''<!-- wp:table -->\n<figure class="wp-block-table"><table><thead><tr><th>牧場</th><th>こんな人におすすめ</th><th>食べた印象</th></tr></thead><tbody><tr><td>上ノ原牧場カドーレ</td><td>ジェラート・動物・ランチまで楽しみたい</td><td>ミルクが濃厚。でもしつこくない</td></tr><tr><td>十夢ミルクファーム</td><td>動物とのふれあい＋スイーツ重視</td><td>まろやかで爽やかな後味</td></tr><tr><td>ジェラート工房Donna</td><td>世羅ドライブと組み合わせたい</td><td>生クリーム感のある濃厚系</td></tr><tr><td>ふくふく牧場</td><td>チーズや牧場そのものに興味がある</td><td>ジェラートではなくチーズが旨い</td></tr><tr><td>久保アグリファーム</td><td>湯来町でのんびり遊びたい</td><td>サラッとした口どけとミルク感</td></tr></tbody></table></figure>\n<!-- /wp:table -->''',
        wp_p("ジェラートだけなら、十夢ミルクファームがかなり好みでした。ただ、カドーレの遊びやすさやDonnaのロケーションも捨てがたい。牧場は味だけで順位を決めるより、<strong>「その日どう遊びたいか」で選ぶ方が楽しい</strong>と思います。"),
        wp_h2("上ノ原牧場カドーレ｜ジェラートも動物も楽しみやすい"),
        img(1),
        wp_p("東広島市福富町の上ノ原牧場カドーレは、<strong>「とりあえず牧場へ遊びに行ってみたい」</strong>という人にも選びやすい場所です。"),
        wp_p("現在も公式サイトでは、牧場のミルクを使ったジェラートやチーズ、ピザの販売に加えて、動物へのエサやりや予約制の牧場体験が案内されています。"),
        wp_p('<a href="https://www.cadore.jp/" target="_blank" rel="noopener">上ノ原牧場カドーレ公式サイト</a>'),
        wp_h3("カドーレのジェラートはミルクが濃い"),
        img(2),
        wp_p("食べたのはミルクとラムレーズン。"),
        wp_p("ミルクは、<strong>濃い。</strong>"),
        wp_p("口に入れるとミルクの風味と甘みがガツンときます。でも、しつこくない。ダブルでもペロッと食べられました。"),
        wp_p("ラムレーズンも、めちゃくちゃ美味しい。<strong>「牧場までジェラートを食べに来たぞ」</strong>という期待にしっかり応えてくれます。"),
        wp_h3("子連れなら湖畔の里 福富とセットもあり"),
        img(3),
        wp_p("カドーレ周辺には、道の駅「湖畔の里 福富」もあります。大きな遊具があるので、<strong>牧場で動物を見る → ジェラート → 道の駅で遊ぶ</strong>まで組みやすいです。"),
        wp_h2("十夢ミルクファーム｜動物との距離が近くて楽しい"),
        img(4),
        wp_p("同じ東広島方面なら、十夢ミルクファームも候補です。現在もふれあい広場では馬・羊・ヤギ・ウサギなどが案内され、ジェラートやプリンなどの乳製品も楽しめます。"),
        wp_p('<a href="https://www.tommilk.co.jp/" target="_blank" rel="noopener">十夢ミルクファーム公式サイト</a>'),
        wp_p("そして、この牧場で忘れられないのが子羊。"),
        wp_p("<strong>脱走子羊ちゃんが可愛すぎてマイッタ！</strong>"),
        wp_p("ジェラートを食べに来たのに、こういう予定外の出来事に全部持っていかれる。牧場の面白いところです。"),
        wp_h3("十夢のジェラートは爽やかな後味"),
        img(5),
        wp_p("ジェラートは、まろやかな口当たりのあとにヨーグルトを思わせる爽やかさが残る味でした。"),
        wp_p("カドーレの濃厚ミルクとはかなり印象が違い、<strong>個人的には大ヒット。</strong>"),
        wp_p("マリトッツォにも同じような爽やかさを感じました。同じミルク系を食べ比べても、ちゃんと個性があります。"),
        wp_h2("ジェラート工房Donna｜世羅ドライブなら寄りたい"),
        img(6),
        wp_p("世羅方面なら、ジェラート工房Donna。世羅町観光協会の案内でも、隣接する牧場の生乳と地元・近県の食材を使ったジェラートが紹介されています。"),
        wp_p('<a href="https://seranan.jp/fac/eat/" target="_blank" rel="noopener">世羅町観光協会のジェラート工房Donna案内</a>'),
        wp_p("ここはジェラートの味だけでなく、自然に囲まれたロケーションも魅力です。"),
        wp_h3("Donnaはまろやかな濃厚系"),
        img(7),
        wp_p("Donnaのジェラートは、生クリームを感じさせるようなまろやかな濃厚さ。カドーレとも、十夢とも違います。"),
        wp_p("なめらかで、濃厚。そして周りには世羅の自然。<br><strong>この環境で、このジェラート。</strong><br>幸せです。"),
        wp_h3("世羅高原農場と組み合わせると一日遊べる"),
        wp_p("せっかく世羅まで来るなら、花の季節は世羅高原農場など周辺観光と組み合わせるのもおすすめです。"),
        wp_p('世羅をまとめて回りたい人は、<a href="https://tsurikue.com/serakankou/">世羅観光の日帰りドライブ記事</a>もどうぞ。花畑をメインにするなら<a href="https://tsurikue.com/serakankounokotsu/">世羅高原農場を楽しむコツ</a>もあります。'),
        wp_h2("ふくふく牧場｜ここだけジェラートじゃなくチーズ"),
        img(8),
        wp_p("庄原市のふくふく牧場は、ここだけ少し方向が違います。"),
        wp_p("ジェラートではなく、<strong>チーズ。</strong>"),
        wp_p("牧場ジェラートの記事なのに。まあいいでしょう。旨いものは旨い。"),
        wp_p("現在も公式サイトでは、山地酪農で育てたジャージー牛のミルクを使ったチーズ作りと、チーズ工房での直売が案内されています。"),
        wp_p('<a href="https://fukufuku-bokujyou.com/" target="_blank" rel="noopener">ふくふく牧場公式サイト</a>'),
        wp_h3("牧場の人と話せるのも面白い"),
        wp_p("ここで印象に残っているのが、オーナーの福元さん。いろいろと教えてくださったのですが、とても優しい方でした。"),
        wp_p("牧場へ行くと、「動物かわいい」だけで終わらず、どう育てているんだろう、どうやってチーズになるんだろう、というところまで少し見えてきます。こういう体験も牧場ならではです。"),
        wp_h3("そしてチーズが旨い"),
        img(9),
        wp_p("肝心のチーズ。<strong>めちゃくちゃ美味しい。</strong>"),
        wp_p("ジェラート巡りの途中にチーズが入ると、甘いものとは違う楽しさが出てきます。結果、大当たりでした。"),
        wp_h2("久保アグリファーム｜湯来町でのんびり過ごしたい人へ"),
        img(10),
        wp_p("広島市佐伯区湯来町にあるサゴタニ牧場・久保アグリファーム。砂谷牛乳の公式サイトでも、自社牧場として現在案内されています。"),
        wp_p('<a href="https://www.sagotani.net/" target="_blank" rel="noopener">砂谷牛乳・サゴタニ牧農公式サイト</a>'),
        wp_p("ここは牧場だけで一日を終わらせなくてもいいのが魅力。湯来町には川遊びや釣り堀、温泉などもあるので、<strong>牧場＋もう一つ</strong>で休日を組みやすいです。"),
        wp_h3("ジェラートはサラッとしたミルク感"),
        img(11),
        wp_p("食べたのはミルクと抹茶。ミルクはサラリとした口どけで、甘さがしつこくなく、それでもしっかりミルクを感じました。"),
        wp_p("抹茶は、<strong>ほろ苦さと甘さのバランスがいい。</strong>"),
        wp_p('湯来町全体で遊ぶなら、<a href="https://tsurikue.com/yukinoasobiba/">湯来町ドライブの日帰りコース</a>へ。時期が合えば<a href="https://tsurikue.com/yuki-hotaru/">湯来町のホタル観賞</a>もあります。'),
        wp_h2("子連れならどの牧場がおすすめ？"),
        wp_p("子どもと動物を見ることを重視するなら、<strong>カドーレ、十夢ミルクファーム、久保アグリファーム</strong>あたりが候補になります。"),
        wp_p("特にカドーレと十夢は東広島方面なので、周辺スポットまで組み合わせやすいです。牧場＋観光まで楽しみたいなら、世羅のDonnaや湯来の久保アグリファームも選びやすいです。"),
        wp_h2("デートで牧場ってどう？"),
        wp_p("デートの行き先としてもありです。動物を見る、自然の中を歩く、ジェラートを食べる、車で次の場所へ移動する。遊園地ほど予定を詰めなくても楽しめます。"),
        wp_p("特に<strong>カドーレ＋福富</strong>、<strong>Donna＋世羅観光</strong>は組みやすいコースです。"),
        wp_h2("ジェラートだけで選ぶならどこ？"),
        wp_p("これはかなり好みが分かれます。"),
        wp_p("濃厚なミルク感なら<strong>カドーレ</strong>。<br>爽やかな後味なら<strong>十夢ミルクファーム</strong>。<br>まろやかな濃厚さなら<strong>Donna</strong>。<br>サラッとしたミルク感なら<strong>久保アグリファーム</strong>。"),
        wp_p("そして「今日は甘いものじゃない」なら、<strong>ふくふく牧場のチーズ</strong>。"),
        wp_p("十夢ミルクファームがかなり好みでしたが、<strong>全部おいしい。</strong><br>結局こうなります。"),
        wp_h2("広島の牧場は周辺スポットと一緒に楽しもう"),
        wp_p("広島の牧場は、一か所だけを目指して行っても楽しめます。でも、せっかく車で出かけるなら周辺まで見ておくと休日の選択肢が増えます。"),
        '''<!-- wp:list -->\n<ul class="wp-block-list"><!-- wp:list-item --><li><strong>東広島：</strong>カドーレ・十夢ミルクファーム・湖畔の里福富</li><!-- /wp:list-item --><!-- wp:list-item --><li><strong>世羅：</strong>Donna・世羅高原農場・夢吊橋</li><!-- /wp:list-item --><!-- wp:list-item --><li><strong>湯来：</strong>久保アグリファーム・川遊び・釣り堀・温泉</li><!-- /wp:list-item --><!-- wp:list-item --><li><strong>庄原：</strong>ふくふく牧場から県北ドライブ</li><!-- /wp:list-item --></ul>\n<!-- /wp:list -->''',
        wp_p("<strong>「牧場へ行く」ではなく、「牧場を入れて一日どう遊ぶ？」</strong>で考えると面白いです。"),
        wp_h2("広島の遊べる牧場まとめ｜ジェラート目当てでも十分楽しい"),
        wp_p("広島には、動物とふれあえて、ジェラートやチーズまで楽しめる牧場があります。"),
        wp_p("カドーレ。<br>十夢ミルクファーム。<br>Donna。<br>ふくふく牧場。<br>久保アグリファーム。"),
        wp_p("どこも同じように見えて、実際に行ってみるとかなり違います。ジェラートも、濃厚、爽やか、まろやか、サラッと、それぞれ個性がありました。"),
        wp_p("途中で脱走した子羊に出会ったり、牧場の人から話を聞いたりするのも、現地へ行くからこその楽しさです。"),
        wp_p("次の休日、<strong>「ちょっと自然のあるところへ行きたいな」</strong>と思ったら、ジェラートを目当てに牧場まで走ってみるのもおすすめですよ。"),
        wp_p("※営業時間・定休日・販売商品・牧場体験の内容は変わることがあります。目的の体験がある場合は、出発前に各施設の公式情報をご確認ください。"),
        wp_p('広島のおでかけ先をもっと探すなら、<a href="https://tsurikue.com/hiroshima-sightseeing/">広島観光・レジャーまとめ</a>もどうぞ。'),
    ]

    used = min(12, len(images))
    if len(images) > used:
        parts.append(wp_h2("写真で見る牧場めぐり"))
        parts.extend(images[used:])
    return "\n\n".join(part for part in parts if part).strip() + "\n"


def write_report(report: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Hiroshima bokujyou reader-first rewrite",
        "",
        f"- result: **{report.get('result')}**",
        f"- post_id: **{report.get('post_id', 0)}**",
        f"- status_before: **{report.get('status_before')}**",
        f"- status_after: **{report.get('status_after')}**",
        f"- old_title: {report.get('old_title', '')}",
        f"- new_title: {report.get('new_title', '')}",
        f"- featured_media_before: **{report.get('featured_media_before', 0)}**",
        f"- featured_media_after: **{report.get('featured_media_after', 0)}**",
        f"- image_blocks_preserved: **{report.get('image_blocks_preserved', 0)}**",
        f"- categories_preserved: **{report.get('categories_preserved', False)}**",
        f"- public_before: **{report.get('public_before', {}).get('published_total', 'unknown')}**",
        f"- public_after: **{report.get('public_after', {}).get('published_total', 'unknown')}**",
        f"- wordpress_write_count: **{report.get('wordpress_write_count', 0)}**",
        f"- source_sha256: `{report.get('source_sha256', '')}`",
        f"- content_sha256: `{report.get('content_sha256', '')}`",
        "- publish_count: **0** (existing published post updated in place)",
    ]
    if report.get("error"):
        lines.append(f"- error: `{report['error']}`")
    (REPORT_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    report: dict[str, Any] = {"result": "BLOCKED", "wordpress_write_count": 0}
    try:
        user = os.environ.get("TSURIKUE_WP_USER")
        password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
        if not user or not password:
            raise RuntimeError("missing WordPress secrets")
        auth = auth_header(user, password)

        before_counts = public_counts(auth)
        before = fetch_target(auth)
        post_id = int(before.get("id") or 0)
        current_content = raw_field(before, "content")
        current_title = html.unescape(raw_field(before, "title"))
        current_images = image_blocks(current_content)
        current_sha = sha256(current_content)
        featured_media = int(before.get("featured_media") or 0)
        categories = [int(x) for x in (before.get("categories") or [])]

        report.update({
            "post_id": post_id,
            "status_before": before.get("status"),
            "old_title": current_title,
            "new_title": NEW_TITLE,
            "featured_media_before": featured_media,
            "public_before": before_counts,
            "source_sha256": current_sha,
            "image_blocks_preserved": len(current_images),
        })

        if before.get("status") != "publish" or before.get("slug") != SLUG:
            raise RuntimeError("target identity/status mismatch")
        if current_title not in {EXPECTED_OLD_TITLE, NEW_TITLE}:
            raise RuntimeError(f"unexpected current title: {current_title!r}")
        if not featured_media:
            raise RuntimeError("featured media missing")
        if not categories:
            raise RuntimeError("categories missing")

        desired = build_content(current_images)
        if "<h1" in desired.casefold():
            raise RuntimeError("body contains H1")
        if "😏" in desired or "🔥" in desired or "🤣" in desired:
            raise RuntimeError("emoji found in article body")

        # Re-fetch immediately before the write. Any concurrent/manual edit blocks this run.
        latest = fetch_target(auth)
        latest_content = raw_field(latest, "content")
        if sha256(latest_content) != current_sha:
            raise RuntimeError("content changed after snapshot; refusing overwrite")
        if int(latest.get("featured_media") or 0) != featured_media:
            raise RuntimeError("featured media changed after snapshot")
        if [int(x) for x in (latest.get("categories") or [])] != categories:
            raise RuntimeError("categories changed after snapshot")

        response, _ = request_json(
            f"{SITE_URL}/wp-json/wp/v2/posts/{post_id}",
            auth,
            method="POST",
            payload={"title": NEW_TITLE, "content": desired, "status": "publish"},
        )
        if int(response.get("id") or 0) != post_id or response.get("status") != "publish":
            raise RuntimeError("WordPress update response validation failed")

        after = fetch_target(auth)
        after_counts = public_counts(auth)
        after_content = raw_field(after, "content")
        after_images = image_blocks(after_content)
        after_title = html.unescape(raw_field(after, "title"))

        if before_counts != after_counts:
            raise RuntimeError(f"published counts changed: {before_counts} -> {after_counts}")
        if after.get("status") != "publish" or after.get("slug") != SLUG:
            raise RuntimeError("post-update identity/status mismatch")
        if after_title != NEW_TITLE:
            raise RuntimeError("post-update title mismatch")
        if int(after.get("featured_media") or 0) != featured_media:
            raise RuntimeError("featured media changed")
        if [int(x) for x in (after.get("categories") or [])] != categories:
            raise RuntimeError("categories changed")
        if after_images != current_images:
            raise RuntimeError("existing image blocks were not preserved exactly")
        if after_content.strip() != desired.strip():
            raise RuntimeError("post-update content mismatch")

        report.update({
            "result": "SUCCESS",
            "status_after": after.get("status"),
            "featured_media_after": int(after.get("featured_media") or 0),
            "categories_preserved": True,
            "public_after": after_counts,
            "wordpress_write_count": 1,
            "content_sha256": sha256(after_content),
        })
        write_report(report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        report["error"] = str(exc)
        write_report(report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
