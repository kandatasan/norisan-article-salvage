#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request

SITE = "https://tsurikue.com"
UA = "tsurikue-lexus-to-goodbuy-20260920/1.0"
GOODBUY_URL = "https://tsurikue.com/goodbuy/"
GOODBUY_SLUG = "goodbuy"
GOODBUY_POST_ID = 3835
MARKER = "<!-- tsurikue-goodbuy-hub-link:20260920 -->"

POSTS = {
    2222: {
        "slug": "ux-resale",
        "title": "レクサスUXのリセールは？616万円で購入し427万円で売却した記録",
        "sha": "ef52390dfa233893fae41a53e513328400bada7e43fc1bc3ad487939269e418d",
        "h2": "レクサスUXのリセールで私が学んだこと",
        "text": 'UXを売るときに査定先でここまで差が出るなら、買うときも「今の車をいくらで手放せるか」まで含めて考えたい。<br><a href="https://tsurikue.com/goodbuy/">レクサスを安く買う方法5選</a>では、下取り・ローン・保険まで含めて購入負担を減らす方法をまとめています。',
    },
    2240: {
        "slug": "ux-mitsumori",
        "title": "レクサスUXの見積もり公開｜総額616万円で選んだ特別仕様車とオプション",
        "sha": "60e792fb670d488e82e57f6d93a6e19a83c3ca37ae98299c6813e3dad40dce2e",
        "h2": "欲しいオプションを削る前に、今の車の売却額を比べる",
        "text": '三眼LEDやムーンルーフを諦める前に、まず買い替え全体で動かせるお金を見てみる。<br><a href="https://tsurikue.com/goodbuy/">レクサスを安く買う方法5選</a>に、私ならどこから見直すかをまとめました。',
    },
    2329: {
        "slug": "ux300h",
        "title": "レクサスUX300hを試乗｜UX250hオーナーが比較して感じた3つの違い",
        "sha": "8db36f25aa9174f40f007b07525d04105f2172f4f650ed2896545fdb93ab8842",
        "h2": "結論｜UX300hで大きく変わったのは3つ",
        "text": '250hと300h、どちらにするか見えてきたら次は予算です。<br><a href="https://tsurikue.com/goodbuy/">欲しいレクサスの装備をなるべく残して購入負担を減らす方法</a>もまとめています。',
    },
    2517: {
        "slug": "ux-koukai",
        "title": "レクサスUXはひどい？616万円で買って後悔した欠点と満足している理由",
        "sha": "e5bfcd8ed7bbf00c47a2c3a85fa0da5e21c3e9f99fed07560af3a772dc72fdfb",
        "h2": "今からレクサスUXを買うなら、私は中古を選ぶ",
        "text": '中古まで候補に入れると、同じ予算でも選べるUXが一気に増えます。<br><a href="https://tsurikue.com/goodbuy/">レクサスを安く買う方法5選</a>では、中古・CPOだけでなく下取りや保険まで含めて整理しています。',
    },
    2530: {
        "slug": "lexus-spindle-grille-carwash",
        "title": "レクサスのスピンドルグリル洗車は簡単？傷を付けにくいブラシとブロワーの使い方",
        "sha": "9602eb7d7adf0a800a339ae87b22cdcaab7140eb608ef32db6db43e70868ef75",
        "h2": "まとめ｜洗車を早く終わらせて、出かける時間にしよう",
        "text": '洗車が終わったら、あとはレクサスで出かけるだけ。次の乗り換えもレクサスを考えているなら、<a href="https://tsurikue.com/goodbuy/">欲しい1台をなるべく諦めずに買う方法</a>もまとめています。',
    },
    2870: {
        "slug": "lexus-ux-review",
        "title": "レクサスUXの評価・感想は？1万km以上乗った元オーナーが本音レビュー",
        "sha": "8ac5f337df36438ef952c430496c6a602c0769c00f6c20f6448360755ca75f44",
        "h2": "今から買うなら新車と中古どっち？",
        "text": '新車か中古かが見えてきたら、次は「どう買えば負担を減らせるか」。<br><a href="https://tsurikue.com/goodbuy/">レクサスを安く買う方法5選</a>では、下取り・ローン・保険・オプションまでまとめて見ています。',
    },
    2874: {
        "slug": "lexus-ux-poor",
        "title": "レクサスUXは貧乏・見栄っ張りに見える？実際に所有して感じたこと",
        "sha": "3e3af3bda7722106cdd62e6bb090e45ad19f35cbb9c8090e6709d4cd1f95c9d5",
        "h2": "中古なら価格と満足度のバランスがさらに良い",
        "text": '中古UXなら「レクサスは高い」で終わらず、予算内で上位グレードや装備付きまで狙えます。<br><a href="https://tsurikue.com/goodbuy/">レクサスを安く買う方法5選</a>も、購入予算を考えるときの参考にどうぞ。',
    },
    2881: {
        "slug": "lexus-ux-buyer",
        "title": "レクサスUXを買う人はどんな人？年齢層・年収・向いている使い方を考える",
        "sha": "e9df907d6d39fd285baf36ce397e5422128f1b0760c24d389044a5efc1582545",
        "h2": "無理なく買える予算から考える",
        "text": '年収だけで線を引くより、今の車の売値やローン、保険まで含めて「自分はいくらなら気持ちよく乗れるか」を見る方が分かりやすいです。<br><a href="https://tsurikue.com/goodbuy/">レクサスを安く買う方法5選</a>に、その考え方をまとめています。',
    },
    2886: {
        "slug": "lexus-ux-size",
        "title": "レクサスUXのサイズは大きい？車幅・全長・取り回しを元オーナー目線で解説",
        "sha": "7982835427c73b0bb5c1a35299a4a5c5f54c3ed8235eb6865f77aab5e1fa545c",
        "h2": "LBX・NXとサイズを比較",
        "text": 'サイズでUX・LBX・NXの候補が絞れたら、次は予算の組み方です。<br><a href="https://tsurikue.com/goodbuy/">欲しいレクサスをなるべく諦めずに買う方法</a>もまとめています。',
    },
    2897: {
        "slug": "lexus-ux-interior",
        "title": "レクサスUXの内装はしょぼい？実際に触って感じた高級感と気になる部分",
        "sha": "f856be6fa117c00c4b259c64d39c1fb6d792a6eb2b7667a12f9a5a61a7a7cb00",
        "h2": "F SPORTの内装で気に入ったところ",
        "text": '内装や装備まで「これが好き」が決まったら、そこを削らずに買える方法を先に探したい。<br><a href="https://tsurikue.com/goodbuy/">レクサスを安く買う方法5選</a>では、欲しい装備を残すために私が見る順番をまとめています。',
    },
    2902: {
        "slug": "lexus-ux-rear-seat",
        "title": "レクサスUXの後部座席は狭い？大人4人で乗った感想と使い勝手を確認",
        "sha": "8a15b024270e1483923afea5f61b046a449241db568d612cacf41d9cf321cb28",
        "h2": "後部座席をよく使うならNXも候補になる",
        "text": 'UXかNXか、使い方に合う方が見えてきたら次は購入予算です。<br><a href="https://tsurikue.com/goodbuy/">レクサスを安く買う方法5選</a>では、今の車の売値やローン、保険まで含めて負担を減らす方法をまとめています。',
    },
    2907: {
        "slug": "lexus-ux-cargo",
        "title": "レクサスUXの荷室は狭い？ゴルフバッグ・買い物で使えるかをチェック",
        "sha": "c8b906c6811b31227bfbf728956e2c2c591c1e614f09bd13ba0b5d03b132a91d",
        "h2": "実際に使って不便だった場面と向いている人",
        "text": '荷室まで含めて「UXでいけそう」と思えたら、次は値段の話。<br><a href="https://tsurikue.com/goodbuy/">欲しいレクサスをなるべく諦めずに買う方法</a>もまとめています。',
    },
    2948: {
        "slug": "lexus-ux-used",
        "title": "レクサスUXの中古は狙い目？新車と比べて中古をおすすめしたい理由",
        "sha": "913ffb061ede762a524f86d9b400c313a5ef6e17d467d5af7b8a07c79373f4bc",
        "h2": "まとめ｜200万円台のUXは「安いレクサス」じゃなく宝探し",
        "text": '中古でいい個体を見つけたら、あとは今の車の売値やローンまで含めて予算を整えるだけ。<br><a href="https://tsurikue.com/goodbuy/">レクサスを安く買う方法5選</a>も一緒に見ると、買い替え全体の金額を考えやすいです。',
    },
    2956: {
        "slug": "lexus-ux-price",
        "title": "レクサスUXの価格はいくら？乗り出し価格とグレード別の違い",
        "sha": "e75f7933d817ae2fafd9d20ad782f65ed60350c2711eea0b63d80f7d82b3a946",
        "h2": "予算別におすすめの買い方を整理｜買い替え総額で考える",
        "text": '車両価格だけでなく、今の車の売値・ローン・保険まで動かすと、同じ予算でも選べるレクサスは変わります。<br><a href="https://tsurikue.com/goodbuy/">レクサスを安く買う方法5選</a>に、私ならどこから見るかをまとめています。',
    },
    2962: {
        "slug": "lexus-ux-discount",
        "title": "レクサスUXは値引きできる？値引き0円だった実体験と安く買う方法",
        "sha": "7376fc206147b0d032f3e90cccb4037e9dd2e8a28b1fa3d072ca02612b202985",
        "h2": "値引き0円でも、買い替え総額はまだ動かせる",
        "text": 'UXだけでなく、レクサス全体で「値引き以外にどこを動かせる？」をまとめたのがこちらです。<br><a href="https://tsurikue.com/goodbuy/">レクサスを安く買う方法5選</a>では、下取り・ローン・保険・オプション・中古まで5つに整理しています。',
    },
    2975: {
        "slug": "lexus-ux-model-change",
        "title": "レクサスUXのモデルチェンジはいつ？次期型は出る？生産終了の噂も整理",
        "sha": "9e5521a806ac9ea6ae180ffec6b3927427271a8a5ffce6b88312229dd546ea73",
        "h2": "次期UXを待つべき？今買うべき？",
        "text": '「今のUXを買う」と決めたなら、次はどう予算を作るか。<br><a href="https://tsurikue.com/goodbuy/">レクサスを安く買う方法5選</a>では、欲しい装備をなるべく残しながら購入負担を減らす方法をまとめています。',
    },
    3570: {
        "slug": "lexus-ux-emotional-explorer",
        "title": "レクサスUXの特別仕様車エモーショナルエクスプローラーはお得？実際に選んだ理由",
        "sha": "13599dda48d3dc6f98dc59f2ea990572c551b2ed186d498ebc5d1cac48d70433",
        "h2": "中古で見つけたら候補に入る？",
        "text": '欲しい特別仕様車が見つかったら、あとは買い替え全体の予算づくりです。<br><a href="https://tsurikue.com/goodbuy/">レクサスを安く買う方法5選</a>では、今の車の売値からローン・保険までまとめて見ています。',
    },
    3601: {
        "slug": "lexus-ux250h-used-vs-ux300h",
        "title": "レクサスUX250h中古とUX300h新車はどっち？元オーナーが今買うなら中古を選ぶ理由",
        "sha": "95c31e40387b00078450986d17d9f1f0384977226df208a4a18d0d1a4e55dd6c",
        "h2": "買う車の値段だけじゃなく、今の車がいくらで売れるかも見る",
        "text": '新車300hか中古250hかで迷うときも、今の車の売値まで分かると予算は一気に現実的になります。<br><a href="https://tsurikue.com/goodbuy/">レクサスを安く買う方法5選</a>では、その先のローン・保険・オプションまでまとめています。',
    },
    3604: {
        "slug": "lexus-ux-vs-nx",
        "title": "レクサスUXとNXどっち？元UXオーナーがサイズ・価格・使い勝手を比較",
        "sha": "e832b7193103b917e028c5d0866481647b59493560a99ccbe430a22833a3c84a",
        "h2": "UXかNXか決める前に、今の車がいくらになるかも見ておく",
        "text": 'UXとNXの価格差を見るなら、今の車がいくらになるかまで入れて考える。<br><a href="https://tsurikue.com/goodbuy/">レクサスを安く買う方法5選</a>では、そこからさらにローンや保険まで含めて購入負担を整理しています。',
    },
    3606: {
        "slug": "lexus-ux-vs-lbx",
        "title": "レクサスLBXとUXどっち？両方乗った元UXオーナーがサイズ・乗り心地・価格を比較",
        "sha": "c9352755b717b4b3a425762856634e658011a7ec7f741f2f092b5bc01304f1ff",
        "h2": "どちらを買うにしても、今の車の値段を先に知っておくと予算が見えやすい",
        "text": 'LBXかUXかが決まっても、最後は買い替え全体の金額です。<br><a href="https://tsurikue.com/goodbuy/">レクサスを安く買う方法5選</a>では、今の車の売値・ローン・保険・オプションまでまとめています。',
    },
    3608: {
        "slug": "lexus-lbx-regret",
        "title": "レクサスLBXは後悔する？試乗して感じた3つの欠点を元UXオーナーが本音レビュー",
        "sha": "4d9d4fcd0a6749b3d837ecdbc77d9318833a14fb0df82433c0168c504f4c04ed",
        "h2": "乗り換えるなら、今の車の値段も先に見ておく",
        "text": 'LBXが欲しくなったら、オプションを削る前に今の車の売値まで見ておきたい。<br><a href="https://tsurikue.com/goodbuy/">レクサスを安く買う方法5選</a>では、欲しい仕様をなるべく残して負担を減らす方法をまとめています。',
    },
    3611: {
        "slug": "lexus-lbx-options",
        "title": "レクサスLBXのおすすめオプションは？ディーラー見積もりから必要・不要を本音で整理",
        "sha": "db44e0438fc06a7d1146d96e5b5456aafad268496d2b15c1acf7c3a276fae7f5",
        "h2": "乗り換えなら、今の車の値段を見てからオプション予算を決める",
        "text": '今の車の売値に余裕が出れば、「外そうかな」と迷った装備を残せるかもしれません。<br><a href="https://tsurikue.com/goodbuy/">レクサスを安く買う方法5選</a>では、下取り以外も含めて予算を動かす方法をまとめています。',
    },
}

H2_BLOCK_RE = re.compile(
    r'<!--\s+wp:heading(?:\s+\{.*?\})?\s+-->\s*'
    r'<h2[^>]*>(.*?)</h2>\s*'
    r'<!--\s+/wp:heading\s+-->',
    re.S,
)


def auth_header() -> str:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise RuntimeError("missing WordPress secrets")
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


def request(method: str, path: str, payload=None):
    headers = {
        "Authorization": auth_header(),
        "Accept": "application/json",
        "User-Agent": UA,
    }
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    last = None
    for attempt in range(8):
        req = urllib.request.Request(SITE + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                body = resp.read().decode("utf-8")
                return (json.loads(body) if body else None), dict(resp.headers.items())
        except urllib.error.HTTPError as exc:
            last = exc
            if 400 <= exc.code < 500 and exc.code not in {408, 429}:
                raise
        except (urllib.error.URLError, TimeoutError, socket.gaierror, OSError) as exc:
            last = exc
        if attempt < 7:
            time.sleep(min(3 + attempt, 10))
    raise last


def raw(row: dict, key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)


def sha256(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", html.unescape(text or "")).strip()


def public_count(endpoint: str) -> int:
    q = urllib.parse.urlencode({"status": "publish", "per_page": 1, "_fields": "id"})
    _, headers = request("GET", f"/wp-json/wp/v2/{endpoint}?{q}")
    for key, value in headers.items():
        if key.lower() == "x-wp-total":
            return int(value)
    raise RuntimeError(f"missing X-WP-Total for {endpoint}")


def get_post(post_id: int) -> dict:
    q = urllib.parse.urlencode({
        "context": "edit",
        "_fields": "id,slug,status,title,content,author,featured_media,categories,excerpt",
    })
    row, _ = request("GET", f"/wp-json/wp/v2/posts/{post_id}?{q}")
    return row


def identity(row: dict) -> dict:
    return {
        "id": int(row.get("id") or 0),
        "slug": row.get("slug"),
        "status": row.get("status"),
        "title": html.unescape(raw(row, "title")),
        "author": int(row.get("author") or 0),
        "featured_media": int(row.get("featured_media") or 0),
        "categories": sorted(row.get("categories") or []),
        "excerpt": raw(row, "excerpt"),
    }


def validate_goodbuy() -> None:
    q = urllib.parse.urlencode({
        "context": "edit",
        "slug": GOODBUY_SLUG,
        "status": "any",
        "per_page": 10,
        "_fields": "id,slug,status,title",
    })
    rows, _ = request("GET", f"/wp-json/wp/v2/posts?{q}")
    if len(rows) != 1:
        raise RuntimeError(f"goodbuy slug count is {len(rows)}, expected 1")
    row = rows[0]
    if int(row.get("id") or 0) != GOODBUY_POST_ID:
        raise RuntimeError(f"goodbuy id mismatch: {row.get('id')}")
    if row.get("slug") != GOODBUY_SLUG:
        raise RuntimeError("goodbuy slug mismatch")
    if row.get("status") != "publish":
        raise RuntimeError(f"goodbuy must be published before linking: {row.get('status')}")


def insertion_block(text_html: str) -> str:
    return f'''\n\n{MARKER}
<!-- wp:paragraph -->
<p>{text_html}</p>
<!-- /wp:paragraph -->

<!-- wp:embed {{"url":"{GOODBUY_URL}"}} -->
<figure class="wp-block-embed"><div class="wp-block-embed__wrapper">
{GOODBUY_URL}
</div></figure>
<!-- /wp:embed -->
'''


def add_to_h2_end(content: str, h2_text: str, text_html: str) -> str:
    matches = list(H2_BLOCK_RE.finditer(content))
    matching_indexes = []
    for index, match in enumerate(matches):
        heading = strip_tags(match.group(1))
        if heading == h2_text:
            matching_indexes.append(index)
    if len(matching_indexes) != 1:
        raise RuntimeError(
            f"h2 match count for {h2_text!r}: {len(matching_indexes)}"
        )
    index = matching_indexes[0]
    insert_at = matches[index + 1].start() if index + 1 < len(matches) else len(content)
    section = content[matches[index].start():insert_at]
    if MARKER in section or GOODBUY_URL in section:
        raise RuntimeError(f"target h2 already links to goodbuy: {h2_text}")
    return content[:insert_at].rstrip() + insertion_block(text_html) + content[insert_at:].lstrip("\n")


def main() -> None:
    validate_goodbuy()

    posts_before = public_count("posts")
    pages_before = public_count("pages")

    snapshots = {}
    targets = {}

    # Full preflight of all 22 posts before the first write.
    for post_id, cfg in POSTS.items():
        row = get_post(post_id)
        ident = identity(row)
        if ident["id"] != post_id:
            raise RuntimeError(f"{post_id}: id mismatch")
        if ident["slug"] != cfg["slug"]:
            raise RuntimeError(f"{post_id}: slug mismatch: {ident['slug']}")
        if ident["status"] != "publish":
            raise RuntimeError(f"{post_id}: status is not publish: {ident['status']}")
        if ident["title"] != cfg["title"]:
            raise RuntimeError(f"{post_id}: title mismatch: {ident['title']}")

        current = raw(row, "content")
        current_sha = sha256(current)
        if MARKER in current:
            raise RuntimeError(f"{post_id}: marker already present")
        if GOODBUY_URL in current:
            raise RuntimeError(f"{post_id}: goodbuy URL already present")
        if current_sha != cfg["sha"]:
            raise RuntimeError(
                f"{post_id}: content sha mismatch: {current_sha} != {cfg['sha']}"
            )

        target = add_to_h2_end(current, cfg["h2"], cfg["text"])
        if target.count(GOODBUY_URL) != current.count(GOODBUY_URL) + 3:
            raise RuntimeError(f"{post_id}: goodbuy URL count must increase by 3")
        if target.count(MARKER) != 1:
            raise RuntimeError(f"{post_id}: marker count invalid")
        if cfg["text"] not in target:
            raise RuntimeError(f"{post_id}: transition text missing in target")

        snapshots[post_id] = {
            "identity": ident,
            "content": current,
            "sha": current_sha,
        }
        targets[post_id] = target

    updated = []
    try:
        for post_id, target in targets.items():
            request("POST", f"/wp-json/wp/v2/posts/{post_id}", {"content": target})
            updated.append(post_id)

            check = get_post(post_id)
            if identity(check) != snapshots[post_id]["identity"]:
                raise RuntimeError(f"{post_id}: identity/metadata changed after update")
            final_content = raw(check, "content")
            if final_content.strip() != target.strip():
                raise RuntimeError(f"{post_id}: final content mismatch")
            if final_content.count(GOODBUY_URL) != 3:
                raise RuntimeError(f"{post_id}: final goodbuy URL count is not 3")
            if final_content.count(MARKER) != 1:
                raise RuntimeError(f"{post_id}: final marker count invalid")

        posts_after = public_count("posts")
        pages_after = public_count("pages")
        if posts_after != posts_before:
            raise RuntimeError(f"published posts changed: {posts_before} -> {posts_after}")
        if pages_after != pages_before:
            raise RuntimeError(f"published pages changed: {pages_before} -> {pages_after}")

    except Exception:
        # Best-effort rollback of every post this run already changed.
        for post_id in reversed(updated):
            try:
                request(
                    "POST",
                    f"/wp-json/wp/v2/posts/{post_id}",
                    {"content": snapshots[post_id]["content"]},
                )
            except Exception as rollback_exc:
                print(f"ROLLBACK_FAILED {post_id}: {rollback_exc}")
        raise

    print("# Lexus articles -> goodbuy hub links 2026-09-20")
    print("- result: **SUCCESS**")
    print(f"- target hub: **{GOODBUY_URL}**")
    print(f"- updated Lexus posts: **{len(updated)}**")
    print(f"- published posts before/after: **{posts_before} / {posts_after}**")
    print(f"- published pages before/after: **{pages_before} / {pages_after}**")
    print("- link pattern: **contextual text link + blog card at selected H2 end**")
    for post_id in sorted(POSTS):
        cfg = POSTS[post_id]
        final_sha = sha256(targets[post_id])
        print(f"- {post_id} {cfg['slug']}: **{cfg['h2']}** / sha256 **{final_sha}**")


if __name__ == "__main__":
    main()
