#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

SITE = "https://tsurikue.com"
UA = "tsurikue-apply-ux-discount-benefit-20260916/1.0"
REPORT = Path("reports/ux-discount-benefit-20260916")

POST_ID = 2962
SLUG = "lexus-ux-discount"
STATUS = "publish"
TITLE = "レクサスUXは値引きできる？値引き0円だった実体験と安く買う方法"
EXPECTED_CURRENT_SHA256 = "792946eeb62927d2056e91b19544ed9476a27cf08ccd2bc15b5587c72c798b75"
EXPECTED_TARGET_SHA256 = "0cdb6bf564d4c9def3b98c1979e7b1bd0c01e0b57c2f304efffb621052034e23"

REPLACEMENTS = [
("intro", """<!-- wp:paragraph -->
<p>「レクサスUXは値引きできる？」<br>「レクサスって本当に値引きゼロ？」<br>「値引きが難しいなら、どうやって負担を減らせばいい？」</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>私はレクサスUX250h F SPORTの特別仕様車「Emotional Explorer」を新車で購入しました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>支払総額は6,156,510円。<br>そして、<strong>値引きは0円でした。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>さらに、知人を3人もレクサスの新車購入につないだ友人でさえ、自分が購入するときは値引きを受けられなかったそうです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ただし、この記事では「レクサスは全国どこでも絶対に値引きしない」とまでは断定しません。<br>店舗・車種・時期・商談条件まで、すべて同じではないからです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ここでは、<strong>私自身の値引き0円だった実体験</strong>を軸に、値引き以外でUXの購入負担を減らす方法まで整理します。</p>
<!-- /wp:paragraph -->""",
"""<!-- wp:paragraph -->
<p><strong>値引き0円でも、欲しかった装備まで全部あきらめる必要はありませんでした。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>私はレクサスUX250h F SPORTの特別仕様車「Emotional Explorer」を新車で購入しました。<br>支払総額は6,156,510円。値引きは<strong>0円</strong>です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>でもUXへ乗り換える前のシエンタは、レクサスディーラーの下取りが50万円、別で査定すると75万円。<br><strong>売却先を変えただけで25万円差が出ました。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>私がUXに付けた三眼フルLEDヘッドランプは16万5,000円、ムーンルーフは11万円。合計27万5,000円です。<br>シエンタの25万円差は、<strong>あと2万5,000円でこの2つの装備に届く金額</strong>でした。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>つまり、見積書の値引き欄は0円でも、<strong>買い替え全体では25万円動かせた</strong>ということです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>「レクサスUXは値引きできる？」「値引きが難しいなら、どうやって負担を減らせばいい？」という人向けに、この記事では私自身の値引き0円だった実体験と、値引き以外で購入負担を減らした方法を整理します。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>なお、「レクサスは全国どこでも絶対に値引きしない」とは断定しません。<br>店舗・車種・時期・商談条件まで、すべて同じではないからです。</p>
<!-- /wp:paragraph -->"""),

("method-open", """<!-- wp:paragraph -->
<p>値引きが動かないなら、ほかの部分を動かします。</p>
<!-- /wp:paragraph -->""",
"""<!-- wp:paragraph -->
<p>値引きが動かないなら、ほかの部分を動かします。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>「車両価格を安くする」ではなく、「買い替え全体の負担を下げる」と考えると選択肢が増えます。</strong></p>
<!-- /wp:paragraph -->"""),

("sale-heading", """<!-- wp:heading -->
<h2 class="wp-block-heading">今の車を高く売って購入資金を増やす</h2>
<!-- /wp:heading -->""",
"""<!-- wp:heading -->
<h2 class="wp-block-heading">値引き0円でも「売却額」は動かせる</h2>
<!-- /wp:heading -->"""),

("sale-benefit", """<!-- wp:paragraph -->
<p>私が一番効果を感じたのは、値引き交渉ではなく<strong>前の車を高く売ること</strong>でした。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>UXへ乗り換える前に乗っていたシエンタは、レクサスディーラーの下取りが50万円。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>その金額でもいいかと思いましたが、別で査定してもらった結果、最終的には75万円で売却できました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>差額は25万円。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>私が付けた三眼フルLEDヘッドランプは16万5,000円、ムーンルーフは11万円。<br>感覚としては、この2つの装備代がほぼ浮いたようなものでした。</p>
<!-- /wp:paragraph -->""",
"""<!-- wp:paragraph -->
<p>私が一番効果を感じたのは、値引き交渉ではなく<strong>前の車を高く売ること</strong>でした。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>UXへ乗り換える前に乗っていたシエンタは、レクサスディーラーの下取りが50万円。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>「もう50万円でいいか」と少し思いましたが、別で査定してもらった結果、最終的には75万円で売却できました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>差額は25万円。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>三眼フルLEDヘッドランプ16万5,000円＋ムーンルーフ11万円＝27万5,000円。<br>25万円あれば、<strong>三眼LEDを付けても8万5,000円残ります。</strong>あと2万5,000円足せば、ムーンルーフまで両方に届きます。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>値引き0円という数字だけを見ると「高く買った」で終わります。<br>でも買い替え全体で見れば、<strong>欲しかった装備を残すための予算は売却側でも作れる</strong>と実感しました。</p>
<!-- /wp:paragraph -->"""),

("ctn", """<!-- wp:paragraph -->
<p>その後、UX自体を手放したときにはCTN車一括査定を利用しました。<br>CTNは最大15社で査定し、やり取りするのは高額査定の上位3社だけ。<br><strong>私のときに連絡が来たのはカーセブンとネクステージの2社で、電話が少なくて快適でした。</strong><br>最終的にはカーセブンへ427万円で売却しています。<br>査定額を見ておくなら、<a href="https://px.a8.net/svt/ejp?a8mat=3Z8YF4+7VEGL6+5I4S+5YRHE" rel="nofollow">【CTN一括車査定】</a><img border="0" width="1" height="1" src="https://www19.a8.net/0.gif?a8mat=3Z8YF4+7VEGL6+5I4S+5YRHE" alt=""></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>査定額は車種・年式・走行距離・状態・時期で変わるので、誰でも同じ結果になるわけではありません。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ただ、<strong>ディーラーの下取りだけで決めず、今の車の相場を確認しておく</strong>価値はあると実感しました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>値引きが0円でも、今の車が25万円高く売れれば、実際の負担は25万円減ります。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>値引き欄を眺めるより、こっちの方が動くこともあります。</p>
<!-- /wp:paragraph -->

<!-- tsurikue-ctn-discount-microcopy:20260907 -->
<!-- wp:paragraph -->
<p><strong>まずは「今の車、いくらになる？」から。</strong></p>
<!-- /wp:paragraph -->""",
"""<!-- wp:paragraph -->
<p>その後、UX自体を手放したときにはCTN車一括査定を利用しました。<br>現在のCTNは最大15社で査定し、やり取りするのは高額査定の上位3社だけ。利用料・手数料も無料です。<br><strong>私のときに連絡が来たのはカーセブンとネクステージの2社で、電話が少なくて快適でした。</strong><br>最終的にはカーセブンへ427万円で売却しています。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>査定額は車種・年式・走行距離・状態・装備・時期で変わるので、誰でも25万円高くなるわけではありません。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>それでも、<strong>ディーラーの下取りだけで決めず、今の車の相場を確認しておく</strong>ことはできます。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>値引きが動かないなら、売却側を比べる。<br>そこで10万円、20万円と差が出れば、欲しかった装備を削らずに済むかもしれません。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>値引き額を見て落ち込む前に、「今の車はいくらになる？」を見ておく。</strong><br>私はこっちの方が買い替え予算を考えやすかったです。</p>
<!-- /wp:paragraph -->

<!-- tsurikue-ctn-discount-microcopy:20260916-benefit -->
<!-- wp:paragraph -->
<p><strong>欲しい装備を削る前に、今の車の価値を確認する。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>査定額を見ておくなら、<a href="https://px.a8.net/svt/ejp?a8mat=3Z8YF4+7VEGL6+5I4S+5YRHE" rel="nofollow">【CTN一括車査定】</a><img border="0" width="1" height="1" src="https://www19.a8.net/0.gif?a8mat=3Z8YF4+7VEGL6+5I4S+5YRHE" alt=""></p>
<!-- /wp:paragraph -->"""),

("ending", """<!-- wp:paragraph -->
<p>私のUXは値引き0円でした。<br>友人の購入例でも値引きはありませんでした。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>だから私は、値引きだけに期待するより、<strong>不要なオプションを削る・今の車を高く売る・中古まで候補を広げる</strong>方が現実的だと思っています。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>欲しいUXを無理に削るのではなく、同じ予算でどう満足度を上げるか。<br>その考え方の方が、レクサスの商談では使いやすかったです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p></p>
<!-- /wp:paragraph -->""",
"""<!-- wp:heading -->
<h2 class="wp-block-heading">まとめ｜値引き0円でも、買い替え全体なら動かせる</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>私のUXは値引き0円でした。<br>友人の購入例でも値引きはありませんでした。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>一方で、シエンタはディーラー下取り50万円から75万円になり、<strong>売却先の違いで25万円差が出ました。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>だから私は、値引きだけに期待するより、<strong>不要なオプションを削る・今の車を高く売る・中古まで候補を広げる</strong>方が現実的だと思っています。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>せっかくレクサスを買うなら、値引き額だけを追って欲しかった装備まで削るのはもったいない。</strong><br>買い替え全体の予算を整えて、自分が乗りたいUXに近づける方がワクワクします。</p>
<!-- /wp:paragraph -->"""),
]

def sha256(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()

def auth_header() -> str:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise RuntimeError("missing WordPress secrets")
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()

AUTH = None

def request(method: str, path: str, payload=None):
    global AUTH
    if AUTH is None:
        AUTH = auth_header()
    headers = {"Authorization": AUTH, "Accept": "application/json", "User-Agent": UA}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(SITE + path, data=data, headers=headers, method=method)
    last = None
    for n in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else None, dict(resp.headers.items())
        except Exception as exc:
            last = exc
            if n < 2:
                time.sleep(2 * (n + 1))
    raise last

def raw_field(row: dict, key: str) -> str:
    value = row.get(key) or {}
    return (value.get("raw") or value.get("rendered") or "") if isinstance(value, dict) else str(value)

def raw_only_field(row: dict, key: str) -> str:
    value = row.get(key) or {}
    return value.get("raw", "") if isinstance(value, dict) else str(value)

def public_count(endpoint: str) -> int:
    q = urllib.parse.urlencode({"status": "publish", "per_page": 1, "_fields": "id"})
    _, headers = request("GET", f"/wp-json/wp/v2/{endpoint}?{q}")
    for k, v in headers.items():
        if k.lower() == "x-wp-total":
            return int(v)
    raise RuntimeError(f"X-WP-Total missing for {endpoint}")

def public_counts():
    return {"posts": public_count("posts"), "pages": public_count("pages")}

def get_post() -> dict:
    q = urllib.parse.urlencode({
        "context": "edit",
        "_fields": "id,slug,status,title,content,author,featured_media,categories,excerpt",
    })
    row, _ = request("GET", f"/wp-json/wp/v2/posts/{POST_ID}?{q}")
    return row

def identity_snapshot(row: dict) -> dict:
    return {
        "id": int(row.get("id") or 0),
        "slug": row.get("slug"),
        "status": row.get("status"),
        "title": html.unescape(raw_field(row, "title")),
        "author": int(row.get("author") or 0),
        "featured_media": int(row.get("featured_media") or 0),
        "categories": list(row.get("categories") or []),
        "excerpt_raw": raw_only_field(row, "excerpt"),
    }

def build_target(current: str) -> str:
    revised = current
    for label, old, new in REPLACEMENTS:
        count = revised.count(old)
        if count != 1:
            raise RuntimeError(f"{label}: expected exactly 1 match, got {count}")
        revised = revised.replace(old, new, 1)
    got = sha256(revised)
    if got != EXPECTED_TARGET_SHA256:
        raise RuntimeError(f"target hash mismatch: {got}")
    for marker in [
        "値引き0円でも、欲しかった装備まで全部あきらめる必要はありませんでした。",
        "あと2万5,000円でこの2つの装備に届く金額",
        "値引き0円でも「売却額」は動かせる",
        "欲しい装備を削る前に、今の車の価値を確認する。",
        'https://px.a8.net/svt/ejp?a8mat=3Z8YF4+7VEGL6+5I4S+5YRHE',
        '[blog_parts id="2843"]',
        '[blog_parts id="2846"]',
    ]:
        if marker not in revised:
            raise RuntimeError(f"missing target marker: {marker}")
    return revised

def validate_current(row: dict) -> str:
    ident = identity_snapshot(row)
    if ident["id"] != POST_ID or ident["slug"] != SLUG or ident["status"] != STATUS or ident["title"] != TITLE:
        raise RuntimeError(f"identity changed: {ident}")
    current = raw_field(row, "content")
    got = sha256(current)
    if got != EXPECTED_CURRENT_SHA256:
        raise RuntimeError(f"content changed since live snapshot: {got}")
    return current

def write_report(data: dict):
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / "result.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# ux-discount benefit rewrite — 2026-09-16",
        "",
        f"- result: **{data['result']}**",
        f"- mode: **{data['mode']}**",
        f"- post_id: **{POST_ID}**",
        f"- slug: **{SLUG}**",
        f"- status: **{data.get('status','-')}**",
        f"- before_sha256: **{data.get('before_sha256','-')}**",
        f"- after_sha256: **{data.get('after_sha256','-')}**",
        f"- public posts before/after: **{data.get('public_before',{}).get('posts','-')} / {data.get('public_after',{}).get('posts','-')}**",
        f"- public pages before/after: **{data.get('public_before',{}).get('pages','-')} / {data.get('public_after',{}).get('pages','-')}**",
    ]
    if data.get("errors"):
        lines += ["", "## Errors"] + [f"- {x}" for x in data["errors"]]
    (REPORT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["preflight", "apply"], default="preflight")
    args = parser.parse_args()

    public_before = public_counts()
    before = get_post()
    original = validate_current(before)
    before_identity = identity_snapshot(before)
    target = build_target(original)

    if args.mode == "preflight":
        write_report({
            "result": "PREFLIGHT_OK_NO_WRITES",
            "mode": args.mode,
            "status": before_identity["status"],
            "before_sha256": sha256(original),
            "after_sha256": sha256(target),
            "public_before": public_before,
            "public_after": public_before,
            "errors": [],
        })
        return 0

    errors = []
    wrote = False
    try:
        request("POST", f"/wp-json/wp/v2/posts/{POST_ID}", {"content": target})
        wrote = True
        saved_row = get_post()
        saved = raw_field(saved_row, "content")
        if saved != target:
            raise RuntimeError("saved content mismatch")
        if identity_snapshot(saved_row) != before_identity:
            raise RuntimeError("identity/metadata changed after write")
        if public_counts() != public_before:
            raise RuntimeError("public post/page counts changed")
    except Exception as exc:
        errors.append(str(exc))
        if wrote:
            try:
                request("POST", f"/wp-json/wp/v2/posts/{POST_ID}", {"content": original})
                rb = get_post()
                if sha256(raw_field(rb, "content")) != EXPECTED_CURRENT_SHA256:
                    errors.append("rollback content hash mismatch")
                if identity_snapshot(rb) != before_identity:
                    errors.append("rollback identity mismatch")
            except Exception as rb_exc:
                errors.append(f"rollback failed: {rb_exc}")
        write_report({
            "result": "APPLY_FAILED_ROLLBACK_ATTEMPTED",
            "mode": args.mode,
            "status": before_identity["status"],
            "before_sha256": sha256(original),
            "after_sha256": "",
            "public_before": public_before,
            "public_after": public_counts(),
            "errors": errors,
        })
        return 3

    final = get_post()
    final_content = raw_field(final, "content")
    final_identity = identity_snapshot(final)
    public_after = public_counts()
    if final_content != target:
        errors.append("final content mismatch")
    if final_identity != before_identity:
        errors.append("final identity mismatch")
    if public_after != public_before:
        errors.append("final public counts changed")

    write_report({
        "result": "APPLIED_OK" if not errors else "APPLIED_BUT_FINAL_VERIFY_FAILED",
        "mode": args.mode,
        "status": final_identity["status"],
        "before_sha256": sha256(original),
        "after_sha256": sha256(final_content),
        "public_before": public_before,
        "public_after": public_after,
        "errors": errors,
    })
    return 0 if not errors else 4

if __name__ == "__main__":
    raise SystemExit(main())
