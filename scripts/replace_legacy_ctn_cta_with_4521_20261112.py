#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import re
import urllib.request

SITE = "https://tsurikue.com"
UA = "tsurikue-ctn-cta-swap-20261112/1.0"

OLD = """<!-- wp:html -->
<div class="tsq-ctn-cta-20261110 top" style="text-align:center;margin:1.1em auto .35em;font-weight:700;font-size:clamp(14px,3.8vw,16px);line-height:1.55">お試しだけでもOK！</div>
<!-- /wp:html -->

<!-- wp:html -->
<style>
.tsq-ctn-official-002-20261110{max-width:480px;width:100%;margin:0 auto;text-align:center}
.tsq-ctn-official-002-20261110 .tsq-ctn-free-lead{font-size:15px;font-weight:700;line-height:1.55;color:#29466e;margin:0 auto 9px}
.tsq-ctn-official-002-20261110 > a{
display:block!important;box-sizing:border-box!important;width:100%!important;
padding:15px 16px!important;border:1px solid #11703a!important;
border-radius:10px!important;background:#17864c!important;color:#fff!important;
text-decoration:none!important;text-align:center!important;
font-size:17px!important;line-height:1.6!important;font-weight:700!important;
box-shadow:0 3px 0 rgba(8,76,39,.18);transition:background .15s ease
}
.tsq-ctn-official-002-20261110 > a:hover{background:#116e3b!important;color:#fff!important}
.tsq-ctn-official-002-20261110 > a:focus-visible{outline:3px solid #f8ac3a!important;outline-offset:3px}
@media(max-width:480px){
.tsq-ctn-official-002-20261110 > a{font-size:16px!important;padding:15px 10px!important}
}
</style>
<div class="tsq-ctn-official-002-20261110">
<div class="tsq-ctn-free-lead">無料で試してみる</div>
<a href="https://px.a8.net/svt/ejp?a8mat=3Z8YF4+7VEGL6+5I4S+5YRHE" rel="nofollow">【CTN一括車査定】</a>
<img border="0" width="1" height="1" src="https://www11.a8.net/0.gif?a8mat=3Z8YF4+7VEGL6+5I4S+5YRHE" alt="">
</div>
<!-- /wp:html -->

<!-- wp:html -->
<div class="tsq-ctn-cta-20261110 bottom" style="text-align:center;margin:.35em auto 1.15em;font-size:clamp(12px,3.4vw,14px);line-height:1.55">電話ラッシュなし！連絡は最大3社だけ</div>
<!-- /wp:html -->"""

NEW = """<!-- wp:shortcode -->
[blog_parts id="4521"]
<!-- /wp:shortcode -->"""

TARGETS = [
    (2222, "ux-resale", "レクサスUXのリセールは？616万円で購入し427万円で売却した記録", 2223),
    (2240, "ux-mitsumori", "レクサスUXの見積もり公開｜総額616万円で選んだ特別仕様車とオプション", 2241),
    (2517, "ux-koukai", "レクサスUXはひどい？616万円で買って後悔した欠点と満足している理由", 2208),
    (2948, "lexus-ux-used", "レクサスUXの中古は狙い目？新車と比べて中古をおすすめしたい理由", 1001),
    (2956, "lexus-ux-price", "レクサスUXの価格はいくら？乗り出し価格とグレード別の違い", 2223),
    (2962, "lexus-ux-discount", "レクサスUXは値引きできる？値引き0円だった実体験と安く買う方法", 2231),
    (3570, "lexus-ux-emotional-explorer", "レクサスUXの特別仕様車エモーショナルエクスプローラーはお得？実際に選んだ理由", 2223),
    (3601, "lexus-ux250h-used-vs-ux300h", "レクサスUX250h中古とUX300h新車はどっち？元オーナーが今買うなら中古を選ぶ理由", 2330),
    (3604, "lexus-ux-vs-nx", "レクサスUXとNXどっち？元UXオーナーがサイズ・価格・使い勝手を比較", 2197),
    (3606, "lexus-ux-vs-lbx", "レクサスLBXとUXどっち？両方乗った元UXオーナーがサイズ・乗り心地・価格を比較", 1513),
    (3611, "lexus-lbx-options", "レクサスLBXのおすすめオプションは？ディーラー見積もりから必要・不要を本音で整理", 1700),
    (3614, "car-sell-high", "車を楽に高く売る方法は？一括査定とディーラー査定を体験談つきで解説", 3616),
    (3835, "goodbuy", "レクサスを安く買う方法5選｜値引きなしでも購入負担を減らすコツ", 2231),
    (3863, "lexus-lbx-cheap", "レクサスLBXを安く買う方法｜欲しいオプションを諦めず負担を減らす5つのコツ", 1700),
    (3936, "lexus-lbx-price", "レクサスLBXの価格はいくら？パッケージ別価格と実際の見積もりを解説", 1513),
    (3945, "lexus-lbx-used", "レクサスLBXの中古車は狙い目？新車との価格差・CPO・選び方を本音で解説", 1513),
    (3973, "tanto-used-best-year", "タント中古は何年式がおすすめ？注意点も実車オーナーが解説", 3954),
    (3767, "landcruiser-fj-price", "ランドクルーザーFJの乗り出し価格はいくら？実際の見積り総額は550万516円", 3757),
    (3816, "landcruiser-fj-cheap", "ランドクルーザーFJを安く買う方法｜値引きだけに頼らず負担を減らす5つのコツ", 3757),
]

TOKEN = re.compile(r"<!--\s+/?wp:[\s\S]*?-->")
OPEN = re.compile(r"<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->")
CLOSE = re.compile(r"<!--\s+/wp:([\w\-/]+)\s+-->")

def auth():
    raw = f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()
    return "Basic " + base64.b64encode(raw).decode()

def req(url, method="GET", payload=None):
    headers = {"Accept":"application/json", "Authorization":auth(), "User-Agent":UA}
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode()
        headers["Content-Type"] = "application/json; charset=utf-8"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=60) as x:
        return json.loads(x.read().decode()), dict(x.headers)

def raw(row, key):
    v = row.get(key) or {}
    if isinstance(v, dict):
        return v.get("raw") or v.get("rendered") or ""
    return str(v)

def get_post(pid):
    row,_=req(f"{SITE}/wp-json/wp/v2/posts/{pid}?context=edit")
    return row

def pub_count():
    _,h=req(f"{SITE}/wp-json/wp/v2/posts?status=publish&per_page=1&_fields=id")
    return int(h.get("X-WP-Total",0))

def block_problems(text):
    stack=[]; problems=[]
    for m in TOKEN.finditer(text):
        t=m.group(0); om=OPEN.fullmatch(t); cm=CLOSE.fullmatch(t)
        if om:
            if om.group(2): continue
            stack.append(om.group(1))
        elif cm:
            n=cm.group(1)
            if not stack or stack[-1]!=n:
                problems.append(("mismatch",stack[-1] if stack else None,n)); return problems
            stack.pop()
    if stack: problems.append(("unclosed",stack))
    return problems

def verify_identity(row, target):
    pid,slug,title,featured=target
    assert row.get("id")==pid
    assert row.get("slug")==slug
    assert row.get("status")=="publish"
    assert raw(row,"title")==title
    assert row.get("featured_media")==featured

def make_new(content):
    if content.count(OLD)!=1:
        raise RuntimeError("legacy CTA cluster count != 1")
    if NEW in content or '[blog_parts id="4521"]' in content:
        raise RuntimeError("new CTN blog part already present")
    prefix,suffix=content.split(OLD,1)
    fixed=prefix+NEW+suffix
    if prefix+suffix != fixed.replace(NEW,"",1):
        raise RuntimeError("body preservation check failed")
    if "tsq-ctn-official-002-20261110" in fixed:
        raise RuntimeError("legacy CTN HTML remains")
    if "3Z8YF4+7VEGL6+5I4S+5YRHE" in fixed:
        raise RuntimeError("legacy CTN A8 material remains")
    if fixed.count('[blog_parts id="4521"]')!=1:
        raise RuntimeError("new CTN shortcode count mismatch")
    if block_problems(fixed):
        raise RuntimeError("Gutenberg structure would be broken")
    return fixed

def main():
    before_total=pub_count()
    prepared=[]

    # Preflight all targets before the first write.
    for t in TARGETS:
        row=get_post(t[0])
        verify_identity(row,t)
        before=raw(row,"content")
        if block_problems(before):
            raise RuntimeError(f"broken Gutenberg before update: {t[1]}")
        fixed=make_new(before)
        prepared.append((t,before,fixed))

    results=[]
    for t,before,fixed in prepared:
        # Re-fetch immediately before each write to catch concurrent edits.
        live=get_post(t[0])
        verify_identity(live,t)
        live_content=raw(live,"content")
        if live_content!=before:
            raise RuntimeError(f"concurrent edit detected before write: {t[1]}")
        req(f"{SITE}/wp-json/wp/v2/posts/{t[0]}",method="POST",payload={"content":fixed})

        after=get_post(t[0])
        verify_identity(after,t)
        actual=raw(after,"content")
        if actual!=fixed:
            raise RuntimeError(f"saved content mismatch: {t[1]}")
        if actual.count('[blog_parts id="4521"]')!=1:
            raise RuntimeError(f"new shortcode verification failed: {t[1]}")
        if "tsq-ctn-official-002-20261110" in actual or "3Z8YF4+7VEGL6+5I4S+5YRHE" in actual:
            raise RuntimeError(f"legacy CTA still present: {t[1]}")
        if block_problems(actual):
            raise RuntimeError(f"broken Gutenberg after update: {t[1]}")
        results.append((t[0],t[1]))

    after_total=pub_count()
    if before_total!=after_total:
        raise RuntimeError(f"published post count changed: {before_total} -> {after_total}")

    print("CTN_CTA_SWAP_RESULT=SUCCESS")
    print(f"CTN_CTA_SWAP_TARGETS={len(results)}")
    print(f"CTN_CTA_SWAP_PUBLISHED_POSTS={before_total}->{after_total}")
    print("CTN_CTA_SWAP_BODY_POLICY=EXACT_CLUSTER_REPLACEMENT_ONLY")
    print("CTN_CTA_SWAP_NEW_SHORTCODE=[blog_parts id=\"4521\"]")
    for pid,slug in results:
        print(f"CTN_CTA_SWAP_UPDATED={pid}:{slug}")

if __name__=="__main__":
    main()
