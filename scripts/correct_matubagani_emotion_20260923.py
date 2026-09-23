#!/usr/bin/env python3
from __future__ import annotations
import base64, json, os, re, urllib.request

SITE="https://tsurikue.com"
UA="tsurikue-matubagani-emotion-20260923/1.0"
PID=2644
SLUG="matubagani"
TITLE="境港で松葉ガニを買って食べた｜水産物直売センターで2杯購入、美味しすぎて泣いた"
FEATURED=2692

TOKEN=re.compile(r"<!--\s+/?wp:[\s\S]*?-->")
OPEN=re.compile(r"<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->")
CLOSE=re.compile(r"<!--\s+/wp:([\w\-/]+)\s+-->")

def auth():
    raw=f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()
    return "Basic "+base64.b64encode(raw).decode()

def req(url,method="GET",payload=None):
    headers={"Accept":"application/json","Authorization":auth(),"User-Agent":UA}
    data=None
    if payload is not None:
        data=json.dumps(payload,ensure_ascii=False).encode()
        headers["Content-Type"]="application/json; charset=utf-8"
    rq=urllib.request.Request(url,data=data,headers=headers,method=method)
    with urllib.request.urlopen(rq,timeout=60) as res:
        return json.loads(res.read().decode()),dict(res.headers)

def raw(row,key):
    v=row.get(key) or {}
    if isinstance(v,dict):
        return v.get("raw") or v.get("rendered") or ""
    return str(v)

def get_post():
    row,_=req(f"{SITE}/wp-json/wp/v2/posts/{PID}?context=edit")
    return row

def pub_count():
    _,h=req(f"{SITE}/wp-json/wp/v2/posts?status=publish&per_page=1&_fields=id")
    return int(h.get("X-WP-Total",0))

def block_problems(text):
    stack=[]
    for m in TOKEN.finditer(text):
        t=m.group(0); op=OPEN.fullmatch(t); cl=CLOSE.fullmatch(t)
        if op:
            if op.group(2): continue
            stack.append(op.group(1))
        elif cl:
            name=cl.group(1)
            if not stack or stack[-1]!=name:
                return [("mismatch",stack[-1] if stack else None,name)]
            stack.pop()
    return [("unclosed",stack)] if stack else []

def verify_identity(row):
    assert row.get("id")==PID
    assert row.get("slug")==SLUG
    assert row.get("status")=="publish"
    assert raw(row,"title")==TITLE
    assert int(row.get("featured_media") or 0)==FEATURED

def main():
    before_total=pub_count()
    row=get_post()
    verify_identity(row)
    before=raw(row,"content")
    assert "tsurikue-editorial:matubagani:v3" in before
    assert "罪悪感が、感謝に変わった" not in before
    assert not block_problems(before)

    intro_old="""<!-- wp:paragraph -->
<p>「美味しい！」で終わらず、なぜか涙まで出たくらいです。</p>
<!-- /wp:paragraph -->"""
    intro_new="""<!-- wp:paragraph -->
<p>「さっきまで生きていたのに」と少し罪悪感があったのに、食べた瞬間は<strong>美味しすぎる。</strong><br>そのあと「この命をいただいているんだ」という感謝が一気に込み上げて、涙が出ました。</p>
<!-- /wp:paragraph -->"""
    assert before.count(intro_old)==1
    fixed=before.replace(intro_old,intro_new,1)

    ending_old="""<!-- wp:paragraph -->
<p><strong>美味しいものは、人をちゃんと幸せにする。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>そして、<strong>生きていれば美味しいものが食べられる。</strong></p>
<!-- /wp:paragraph -->"""
    ending_new="""<!-- wp:heading -->
<h2 class="wp-block-heading">罪悪感が、感謝に変わった</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>さっきまで生きていた松葉ガニを食べることに、最初は少し罪悪感がありました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>でも、ひと口食べたら<strong>「美味しすぎる！」</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>その美味しさに驚いたあと、<strong>「この命をいただいているんだ」</strong>という感謝が一気に込み上げてきました。<br>美味しすぎることと、ありがたい気持ちが重なって、涙が出たんです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>美味しいものは、人をちゃんと幸せにする。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>そして、<strong>生きていれば美味しいものが食べられる。</strong></p>
<!-- /wp:paragraph -->"""
    assert fixed.count(ending_old)==1
    fixed=fixed.replace(ending_old,ending_new,1)

    assert "罪悪感が、感謝に変わった" in fixed
    assert "美味しすぎることと、ありがたい気持ちが重なって、涙が出た" in fixed
    assert len(re.findall(r"<!-- wp:image\b",fixed))==len(re.findall(r"<!-- wp:image\b",before))
    assert len(re.findall(r"\[blog_parts\s+id=",fixed))==len(re.findall(r"\[blog_parts\s+id=",before))
    assert not block_problems(fixed)

    before_modified=row.get("modified_gmt")
    req(f"{SITE}/wp-json/wp/v2/posts/{PID}",method="POST",payload={"content":fixed})
    after=get_post()
    verify_identity(after)
    actual=raw(after,"content")
    assert "罪悪感が、感謝に変わった" in actual
    assert "美味しすぎることと、ありがたい気持ちが重なって、涙が出た" in actual
    assert len(re.findall(r"<!-- wp:image\b",actual))==len(re.findall(r"<!-- wp:image\b",before))
    assert len(re.findall(r"\[blog_parts\s+id=",actual))==len(re.findall(r"\[blog_parts\s+id=",before))
    assert not block_problems(actual)
    assert after.get("modified_gmt")!=before_modified
    after_total=pub_count()
    assert after_total==before_total

    print("# Matsubagani emotion correction")
    print("- result: **SUCCESS**")
    print(f"- public posts: **{before_total} → {after_total}**")
    print("- post: **2644 / matubagani / publish → publish**")
    print("- emotional arc: **guilt → deliciousness → gratitude → tears**")
    print("- wife-confirmed firsthand context: **reflected**")
    print("- title / slug / featured_media: **unchanged**")
    print("- image counts / blog_parts counts: **unchanged**")
    print("- Gutenberg problems after: **0**")
    print("- modified date: **updated**")

if __name__=="__main__":
    main()
