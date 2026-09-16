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
UA = "tsurikue-apply-ux-resale-benefit-20260916/1.0"
REPORT = Path("reports/ux-resale-benefit-20260916")

POST_ID = 2222
SLUG = "ux-resale"
STATUS = "publish"
TITLE = "レクサスUXのリセールは？616万円で購入し427万円で売却した記録"
EXPECTED_CURRENT_SHA256 = "8390fbd713b77e6fc9ba6f22fb63072b3d0cdabe1b5ed04a939df5ea616946ae"
EXPECTED_TARGET_SHA256 = "ef52390dfa233893fae41a53e513328400bada7e43fc1bc3ad487939269e418d"

OLD_INTRO = """<!-- wp:paragraph -->
<p>レクサスUXを<strong>616万円で購入して、427万円で売却しました。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ただ、私が一番驚いたのは最終的な売却額ではありません。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>納車から約3か月ごろ。UXを売るつもりはなく、<strong>「今いくらなんだろう？」という好奇心</strong>で査定してみました。<br>そのときの査定が、レクサスディーラー350万円と別の一括査定500万円前後。同じUXなのに、約150万円差がありました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>車の査定、1社だけ見て決めるのは怖い。</strong><br>この記事は、納車から約3か月ごろに好奇心で査定したところから、約2年後の2025年2月にカーセブンへ427万円で実際に売却するまでの記録です。</p>
<!-- /wp:paragraph -->"""

NEW_INTRO = """<!-- wp:paragraph -->
<p><strong>150万円あったら、次の車をどこまで変えられると思いますか？</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>2026年9月現在、<a href="https://lexus.jp/models/ux/" rel="noopener">レクサスUX300hは521万円から</a>、<a href="https://lexus.jp/models/rx/" rel="noopener">RX350は668万円から</a>。<br>車両価格の差は<strong>147万円</strong>です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>つまり150万円あれば、単純な車両価格だけで見れば<strong>UXからRXまで届くくらいの差</strong>になります。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>そして私のUXは、納車から約3か月ごろのほぼ同じ時期に、<strong>レクサスディーラー350万円、別の一括査定500万円前後。</strong><br>査定先によって、実際に約150万円差が出ました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>同じ車なのに、査定先が違うだけで<strong>次に選べる車のクラスまで変わるような金額差</strong>です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>これを一度経験すると、最初の査定額だけで買い替えを決めるの、ちょっと怖くないですか？</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>私が実際にUXを手放したのは約2年後。<br><strong>616万円で購入したUXを、2025年2月に427万円で売却しました。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>この記事では、好奇心で査定した350万円から、500万円前後、435万円、そして実際に427万円で売却するまでを全部残します。</p>
<!-- /wp:paragraph -->"""

OLD_150 = """<!-- wp:paragraph -->
<p><strong>同じ車、ほぼ同じ時期。それでも約150万円違いました。</strong><br>このとき初めて、査定先を変えるだけで見える金額がここまで変わることを実感しました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ただし、500万円前後はあくまで提示額です。<br>この時点では売却せず、そのままUXに乗り続けました。実際に売ったのは、納車から約2年後です。</p>
<!-- /wp:paragraph -->"""

NEW_150 = """<!-- wp:paragraph -->
<p><strong>同じ車、ほぼ同じ時期。それでも約150万円違いました。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>150万円をただの数字で見ると、「大きな差だな」で終わります。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>でも今のレクサスで考えると、UX300hの521万円〜に対してRX350は668万円〜。<br><strong>その差は147万円です。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>私が見た約150万円差は、イメージとしては<strong>「UXを考えていた予算で、RXまで見えてくる」</strong>くらいの金額でした。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>もちろん、査定を比較すれば毎回150万円上がるわけではありません。<br>500万円前後も、この時点ではあくまで提示額です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>それでも、比較しなければ<strong>自分の車にどれくらいの価格差があるのかすら分かりません。</strong><br>私はこのとき初めて、「高く売る」って次の車選びまで変えるんだと実感しました。</p>
<!-- /wp:paragraph -->"""

OLD_CTN = """<!-- wp:paragraph -->
<p><strong>350万円だけ見ていたら、私はUXの価値をかなり低く考えていたはずです。</strong><br>高く売れる会社を探したい。でも何社からも電話が来るのは避けたい。CTNは高額査定の上位3社だけとやり取りする仕組みなので、そこが分かりやすいです。<br>査定額を見ておくなら、<a href="https://px.a8.net/svt/ejp?a8mat=3Z8YF4+7VEGL6+5I4S+5YRHE" rel="nofollow">【CTN一括車査定】</a><img border="0" width="1" height="1" src="https://www19.a8.net/0.gif?a8mat=3Z8YF4+7VEGL6+5I4S+5YRHE" alt=""></p>
<!-- /wp:paragraph -->"""

NEW_CTN = """<!-- wp:paragraph -->
<p><strong>350万円だけ見ていたら、私はUXの価値をかなり低く考えていたはずです。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>次の車を10万円安く買うのも大事です。<br>でも今の車が10万円、20万円高く売れれば、そのお金で欲しかったオプションを付けられるかもしれません。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>もっと差が出れば、私の150万円差のように<strong>次に選べる車そのものが変わる</strong>こともあります。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>高く売れる会社は探したい。<br>でも何社からも電話が来るのは避けたい。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>現在のCTNは最大15社で査定し、やり取りするのは高額査定の上位3社だけ。利用料・手数料も無料です。<br>「今の車がいくらになる？」を見ておくなら、<a href="https://px.a8.net/svt/ejp?a8mat=3Z8YF4+7VEGL6+5I4S+5YRHE" rel="nofollow">【CTN一括車査定】</a><img border="0" width="1" height="1" src="https://www19.a8.net/0.gif?a8mat=3Z8YF4+7VEGL6+5I4S+5YRHE" alt=""></p>
<!-- /wp:paragraph -->"""

OLD_SELL = """<!-- wp:paragraph -->
<p>もっと価格が落ちていると思っていたので、427万円で買い取ってもらえたことには本当に助けられました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>高く売れたから喜んで手放したわけではありません。<br>気に入っていたUXを売る悲しさと、想像していたより高く売れた安堵。その両方がありました。</p>
<!-- /wp:paragraph -->"""

NEW_SELL = """<!-- wp:paragraph -->
<p>もっと価格が落ちていると思っていたので、427万円で買い取ってもらえたことには本当に助けられました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>427万円あれば、次の車を探すときの景色もかなり変わります。<br>中古車なら選択肢が一気に広がるし、新車でも頭金やオプションへ回せる。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>車を高く売ることは、売却で得するだけじゃなく、次の車選びを楽しくすることでもある。</strong><br>今ならそう思います。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ただ、高く売れたから喜んで手放したわけではありません。<br>気に入っていたUXを売る悲しさと、想像していたより高く売れた安堵。その両方がありました。</p>
<!-- /wp:paragraph -->"""

OLD_FINAL = """<!-- wp:paragraph -->
<p>それでも、最初の350万円だけを見ていたら「UXのリセールはかなり厳しい」と思っていたはずです。<br><strong>UXの価値そのものより、査定先によって見えてくる金額が大きく違った。</strong>これが、何度も査定を受けて実際に売却した私の結論です。</p>
<!-- /wp:paragraph -->"""

NEW_FINAL = """<!-- wp:paragraph -->
<p>それでも、最初の350万円だけを見ていたら「UXのリセールはかなり厳しい」と思っていたはずです。<br><strong>UXの価値そのものより、査定先によって見えてくる金額が大きく違った。</strong>これが、何度も査定を受けて実際に売却した私の結論です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>10万円、20万円違えば、欲しかったオプションを付けられるかもしれない。<br>100万円単位で違えば、次に選ぶ車まで変わるかもしれない。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>せっかく買い替えるなら、「いくらで買うか」だけでなく「今の車はいくらになるか」も知ってから、次の1台をワクワクしながら選んでほしいです。</strong></p>
<!-- /wp:paragraph -->"""

OLD_CTA = '<p class="has-text-align-center"><strong>高く売りたい。でも何社からも電話はいらない。</strong></p>'
NEW_CTA = '<p class="has-text-align-center"><strong>今の車の価値を知って、次の1台の選択肢を増やす。</strong></p>'

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
        "_fields": "id,slug,status,title,content,author,modified,featured_media,categories,excerpt",
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
        "excerpt": raw_field(row, "excerpt"),
    }

def replace_once(content: str, old: str, new: str, label: str) -> str:
    count = content.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly 1 match, got {count}")
    return content.replace(old, new, 1)

def build_target(current: str) -> str:
    revised = current
    revised = replace_once(revised, OLD_INTRO, NEW_INTRO, "intro")
    revised = replace_once(revised, OLD_150, NEW_150, "150-benefit")
    revised = replace_once(revised, OLD_CTN, NEW_CTN, "ctn-benefit")
    revised = replace_once(revised, OLD_SELL, NEW_SELL, "sell-benefit")
    revised = replace_once(revised, OLD_FINAL, NEW_FINAL, "final-benefit")
    revised = replace_once(revised, OLD_CTA, NEW_CTA, "cta")
    if sha256(revised) != EXPECTED_TARGET_SHA256:
        raise RuntimeError(f"target hash mismatch: {sha256(revised)}")
    required = [
        "150万円あったら、次の車をどこまで変えられると思いますか？",
        "UXからRXまで届くくらいの差",
        "次に選べる車そのものが変わる",
        "車を高く売ることは、売却で得するだけじゃなく、次の車選びを楽しくすることでもある",
        '[blog_parts id="2184"]',
        '[blog_parts id="2846"]',
    ]
    for marker in required:
        if marker not in revised:
            raise RuntimeError(f"missing target marker: {marker}")
    return revised

def validate_current(row: dict) -> str:
    ident = identity_snapshot(row)
    if ident["id"] != POST_ID or ident["slug"] != SLUG or ident["status"] != STATUS or ident["title"] != TITLE:
        raise RuntimeError(f"identity changed: {ident}")
    current = raw_field(row, "content")
    if sha256(current) != EXPECTED_CURRENT_SHA256:
        raise RuntimeError(f"content changed since audit: {sha256(current)}")
    return current

def write_report(data: dict):
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / "result.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# ux-resale benefit rewrite — 2026-09-16",
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
