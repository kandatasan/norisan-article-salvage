#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, hashlib, html, json, os, time, urllib.parse, urllib.request
from pathlib import Path

SITE="https://tsurikue.com"
POST_ID=2517
SLUG="ux-koukai"
STATUS="publish"
TITLE="レクサスUXはひどい？616万円で買って後悔した欠点と満足している理由"
AUTHOR=1
FEATURED_MEDIA=2208
CATEGORIES=[10,11]
TAGS=[37]
EXPECTED_CURRENT_SHA256="96342d0ca88056536cd9c6c1dd7a7c1dae1c765bad9a51580c359ceec6c9074f"
EXPECTED_TARGET_SHA256="4597692f1970fd9969fccf3c56eff4fba1dbff5033a06e3d916ce65e4c3637cc"
BASELINE=Path("baselines/ux-koukai-20260921.html")
REPORT=Path("reports/ux-koukai-hub-20260921")
UA="tsurikue-ux-koukai-hub-20260921/1.0"

REPLACEMENTS=[
("used-link",
"""<!-- wp:paragraph -->
<p>200〜300万円台の相場感やCPO、前期・後期の違いは、<a href="https://tsurikue.com/lexus-ux-used/">中古UXの選び方</a>で詳しく整理しています。</p>
<!-- /wp:paragraph -->""",
"""<!-- wp:paragraph -->
<p>200〜300万円台でどこまで条件のいいUXを狙えるかは、<a href="https://tsurikue.com/lexus-ux-used/">200万円台から「最強中古UX」を探す記事</a>で詳しく整理しています。<br>F SPORT・version L・CPO・前期／後期を比べて、何を狙うかまでまとめました。</p>
<!-- /wp:paragraph -->"""),

("gulliver-inline",
"""<!-- wp:paragraph {"align":"center"} -->
<p class="has-text-align-center"><strong>200〜300万円台のお宝UX、探してみる？</strong></p>
<!-- /wp:paragraph -->""",
"""<!-- wp:paragraph {"align":"center"} -->
<p class="has-text-align-center"><strong>200〜300万円台のお宝UX、探してみる？</strong></p>
<!-- /wp:paragraph -->

<!-- wp:shortcode -->
[blog_parts id="2843"]
<!-- /wp:shortcode -->"""),

("ctn-copy",
"""<!-- wp:paragraph -->
<p>CTNなら最大15社で査定して、やり取りするのは<strong>高値を付けた上位3社だけ</strong>。<br>高く売りたい。でも何社からも電話が来るのはイヤ。そんな人向けです。</p>
<!-- /wp:paragraph -->""",
"""<!-- wp:paragraph -->
<p>CTNは、提携する買取店の中から<strong>高額査定の上位3社まで</strong>を紹介する仕組みです。<br>私のときはカーセブンとネクステージの2社から連絡が来ました。高く売りたいけど、電話ラッシュは避けたい人には使いやすかったです。</p>
<!-- /wp:paragraph -->"""),

("decision-links",
"""<!-- wp:paragraph -->
<p><small>※査定額は車種、年式、走行距離、車両状態、査定時期などによって異なります。</small></p>
<!-- /wp:paragraph -->

<h2 class="wp-block-heading">レクサスUXに関するよくある質問</h2>""",
"""<!-- wp:paragraph -->
<p><small>※査定額は車種、年式、走行距離、車両状態、査定時期などによって異なります。</small></p>
<!-- /wp:paragraph -->

<!-- tsurikue-ux-koukai-decision-links:20260921 -->
<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">買う前に、次はここを見ればOK</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>UXが気になっているなら、今どこで迷っているかで次に見る記事を変えると早いです。</p>
<!-- /wp:paragraph -->

<!-- wp:table {"hasFixedLayout":false} -->
<figure class="wp-block-table"><table><thead><tr><th>いま気になること</th><th>次に見る記事</th></tr></thead><tbody><tr><td>200〜300万円台で条件のいいUXを探したい</td><td><a href="https://tsurikue.com/lexus-ux-used/">中古UXの最強個体を探す</a></td></tr><tr><td>現行UXはいくら必要？</td><td><a href="https://tsurikue.com/lexus-ux-price/">UXの価格・乗り出し総額</a></td></tr><tr><td>616万円の見積もりの中身を見たい</td><td><a href="https://tsurikue.com/ux-mitsumori/">実際のUX見積もり</a></td></tr><tr><td>値引き0円でも負担を減らしたい</td><td><a href="https://tsurikue.com/lexus-ux-discount/">UXを安く買う考え方</a></td></tr></tbody></table></figure>
<!-- /wp:table -->

<h2 class="wp-block-heading">レクサスUXに関するよくある質問</h2>"""),

("footer-dedup",
"""<!-- wp:shortcode -->
[blog_parts id="2843"]
<!-- /wp:shortcode -->

<!-- wp:shortcode -->
[blog_parts id="2846"]
<!-- /wp:shortcode -->""",
"""<!-- tsurikue-ux-koukai-affiliate-dedup:20260921 -->""")
]

def sha(s:str)->str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()

def auth_header():
    u=os.environ.get("TSURIKUE_WP_USER")
    p=os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not u or not p:
        raise RuntimeError("missing WordPress secrets")
    return "Basic "+base64.b64encode(f"{u}:{p}".encode()).decode()

def request(method,path,payload=None):
    headers={"Authorization":auth_header(),"Accept":"application/json","User-Agent":UA}
    data=None
    if payload is not None:
        headers["Content-Type"]="application/json; charset=utf-8"
        data=json.dumps(payload,ensure_ascii=False).encode("utf-8")
    last=None
    for n in range(4):
        try:
            req=urllib.request.Request(SITE+path,data=data,headers=headers,method=method)
            with urllib.request.urlopen(req,timeout=90) as resp:
                body=resp.read().decode("utf-8")
                return json.loads(body) if body else None
        except Exception as e:
            last=e
            if n<3: time.sleep(3*(n+1))
    raise last

def raw(row,key):
    v=row.get(key) or {}
    return (v.get("raw") or v.get("rendered") or "") if isinstance(v,dict) else str(v)

def raw_only(row,key):
    v=row.get(key) or {}
    return v.get("raw","") if isinstance(v,dict) else str(v)

def get_post():
    q=urllib.parse.urlencode({
        "context":"edit",
        "_fields":"id,slug,status,title,content,author,featured_media,categories,tags,excerpt"
    })
    return request("GET",f"/wp-json/wp/v2/posts/{POST_ID}?{q}")

def ident(row):
    return {
        "id":int(row.get("id") or 0),
        "slug":row.get("slug"),
        "status":row.get("status"),
        "title":html.unescape(raw(row,"title")),
        "author":int(row.get("author") or 0),
        "featured_media":int(row.get("featured_media") or 0),
        "categories":list(row.get("categories") or []),
        "tags":list(row.get("tags") or []),
        "excerpt_raw":raw_only(row,"excerpt"),
    }

def assert_identity(x):
    if x["id"]!=POST_ID or x["slug"]!=SLUG or x["status"]!=STATUS or x["title"]!=TITLE:
        raise RuntimeError(f"identity mismatch: {x}")
    if x["author"]!=AUTHOR or x["featured_media"]!=FEATURED_MEDIA:
        raise RuntimeError(f"author/media mismatch: {x}")
    if x["categories"]!=CATEGORIES or x["tags"]!=TAGS:
        raise RuntimeError(f"taxonomy mismatch: {x}")

def build(current):
    out=current
    for label,old,new in REPLACEMENTS:
        n=out.count(old)
        if n!=1:
            raise RuntimeError(f"{label}: expected exactly 1 match, got {n}")
        out=out.replace(old,new,1)
    required=[
        '200万円台から「最強中古UX」を探す記事',
        '[blog_parts id="2843"]',
        '[blog_parts id="2184"]',
        'tsurikue-ux-koukai-decision-links:20260921',
        'https://tsurikue.com/lexus-ux-price/',
        'https://tsurikue.com/ux-mitsumori/',
        'https://tsurikue.com/lexus-ux-discount/',
        'tsurikue-ux-koukai-affiliate-dedup:20260921',
        '<h2 class="wp-block-heading">まとめ｜616万円なら文句あり。中古UXならかなりアリ</h2>',
    ]
    for m in required:
        if m not in out:
            raise RuntimeError(f"missing target marker: {m}")
    if out.count('[blog_parts id="2843"]')!=1:
        raise RuntimeError("Gulliver banner count must be 1")
    if out.count('[blog_parts id="2184"]')!=1:
        raise RuntimeError("CTN button count must be 1")
    if '[blog_parts id="2846"]' in out:
        raise RuntimeError("duplicate CTN footer banner remains")
    # SEO-sensitive anchors must be preserved exactly.
    for h in [
        '<h2 class="wp-block-heading">結論｜616万円なら文句あり。でも中古なら話が変わる</h2>',
        '<h2 class="wp-block-heading">レクサスUXを買って「ひどい」と感じた6つの欠点</h2>',
        '<h2 class="wp-block-heading">文句はある。でも私はUXが好きだった</h2>',
        '<h2 class="wp-block-heading">今からレクサスUXを買うなら、私は中古を選ぶ</h2>',
        '<h2 class="wp-block-heading">レクサスUXに関するよくある質問</h2>',
        '<h2 class="wp-block-heading">まとめ｜616万円なら文句あり。中古UXならかなりアリ</h2>',
    ]:
        if h not in out:
            raise RuntimeError(f"SEO heading changed/missing: {h}")
    return out

def validate_saved(saved,target):
    required=[
        '200万円台から「最強中古UX」を探す記事',
        'F SPORT・version L・CPO・前期／後期',
        '[blog_parts id="2843"]',
        '[blog_parts id="2184"]',
        'tsurikue-ux-koukai-decision-links:20260921',
        'https://tsurikue.com/lexus-ux-price/',
        'https://tsurikue.com/ux-mitsumori/',
        'https://tsurikue.com/lexus-ux-discount/',
        'tsurikue-ux-koukai-affiliate-dedup:20260921',
        '高額査定の上位3社まで',
    ]
    missing=[m for m in required if m not in saved]
    if missing:
        raise RuntimeError("saved markers missing: "+repr(missing))
    if saved.count('[blog_parts id="2843"]')!=1:
        raise RuntimeError("saved Gulliver count changed")
    if saved.count('[blog_parts id="2184"]')!=1:
        raise RuntimeError("saved CTN count changed")
    if '[blog_parts id="2846"]' in saved:
        raise RuntimeError("saved duplicate CTN footer remains")
    ratio=len(saved)/max(1,len(target))
    if ratio<0.97 or ratio>1.03:
        raise RuntimeError(f"saved length drift too large: {ratio:.4f}")
    return {"sha256":sha(saved),"length":len(saved),"target_length":len(target),"ratio":ratio}

def write_report(d):
    REPORT.mkdir(parents=True,exist_ok=True)
    (REPORT/"result.json").write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=[
        "# UX koukai hub enhancement — 2026-09-21","",
        f"- result: **{d['result']}**",
        f"- mode: **{d['mode']}**",
        f"- post_id: **{POST_ID}**",
        f"- slug: **{SLUG}**",
        f"- before_sha256: **{d.get('before_sha256','-')}**",
        f"- target_sha256: **{d.get('target_sha256','-')}**",
        f"- after_sha256: **{d.get('after_sha256','-')}**",
    ]
    if d.get("errors"):
        lines+=["","## Errors"]+[f"- {e}" for e in d["errors"]]
    (REPORT/"summary.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--mode",choices=["preflight","apply"],default="preflight")
    args=ap.parse_args()

    if args.mode=="preflight":
        current=BASELINE.read_text(encoding="utf-8")
        if sha(current)!=EXPECTED_CURRENT_SHA256:
            raise RuntimeError(f"baseline hash mismatch: {sha(current)}")
        target=build(current)
        target_hash=sha(target)
        if EXPECTED_TARGET_SHA256 and target_hash!=EXPECTED_TARGET_SHA256:
            raise RuntimeError(f"target hash mismatch: {target_hash}")
        write_report({
            "result":"PREFLIGHT_OK_NO_WRITES","mode":"preflight",
            "before_sha256":sha(current),"target_sha256":target_hash,"after_sha256":"","errors":[]
        })
        return 0

    row=get_post()
    before_ident=ident(row)
    assert_identity(before_ident)
    current=raw(row,"content")
    if sha(current)!=EXPECTED_CURRENT_SHA256:
        raise RuntimeError(f"live content changed: {sha(current)}")
    target=build(current)
    target_hash=sha(target)
    if not EXPECTED_TARGET_SHA256:
        raise RuntimeError("apply refused: target hash not locked")
    if target_hash!=EXPECTED_TARGET_SHA256:
        raise RuntimeError(f"target hash mismatch: {target_hash}")

    errors=[]; wrote=False
    try:
        request("POST",f"/wp-json/wp/v2/posts/{POST_ID}",{"content":target})
        wrote=True
        saved=get_post()
        assert_identity(ident(saved))
        if ident(saved)!=before_ident:
            raise RuntimeError("metadata changed after write")
        saved_content=raw(saved,"content")
        validate_saved(saved_content,target)
    except Exception as e:
        errors.append(str(e))
        if wrote:
            try:
                request("POST",f"/wp-json/wp/v2/posts/{POST_ID}",{"content":current})
            except Exception as rb:
                errors.append("rollback failed: "+str(rb))
        write_report({
            "result":"APPLY_FAILED_ROLLBACK_ATTEMPTED","mode":"apply",
            "before_sha256":sha(current),"target_sha256":target_hash,"after_sha256":"","errors":errors
        })
        return 3

    final=get_post()
    final_content=raw(final,"content")
    try:
        assert_identity(ident(final))
        if ident(final)!=before_ident:
            errors.append("final metadata mismatch")
        validate_saved(final_content,target)
    except Exception as e:
        errors.append(str(e))
    write_report({
        "result":"APPLIED_OK" if not errors else "APPLIED_BUT_VERIFY_FAILED",
        "mode":"apply","before_sha256":sha(current),"target_sha256":target_hash,
        "after_sha256":sha(final_content),"errors":errors
    })
    return 0 if not errors else 4

if __name__=="__main__":
    raise SystemExit(main())
