#!/usr/bin/env python3
from __future__ import annotations

import base64, json, os, re, urllib.request

SITE="https://tsurikue.com"
UA="tsurikue-matubagani-v3-20260923/1.0"
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
    assert "tsurikue-editorial:matubagani:v2" in before
    assert "tsurikue-editorial:matubagani:v3" not in before
    assert not block_problems(before)

    fixed=before.replace(
        "<!-- tsurikue-editorial:matubagani:v2 -->",
        "<!-- tsurikue-editorial:matubagani:v3 -->",
        1
    )

    old_price="""<!-- wp:paragraph -->
<p>最後は境港水産物直売センターで、お店の方に身入りを見てもらって松葉ガニを2杯購入。</p>
<!-- /wp:paragraph -->"""
    new_price="""<!-- wp:paragraph -->
<p>最後は境港水産物直売センターへ。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>この時、目に留まったのが<strong>2杯5000円</strong>の松葉ガニでした。お店の方に身が詰まっているものを選んでもらって購入。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>価格はこの時のものですが、何軒も見て回った末に「これにしよう」と決めた2杯です。</p>
<!-- /wp:paragraph -->"""
    assert fixed.count(old_price)==1
    fixed=fixed.replace(old_price,new_price,1)

    old_raw="""<!-- wp:paragraph -->
<p>私は荷物の片づけをして、食べる準備だけ万全にしました。</p>
<!-- /wp:paragraph -->"""
    new_raw=old_raw+"""

<!-- wp:paragraph -->
<p>その途中、ノリに呼ばれて<strong>茹でる前の足を1本だけ味見。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>甘い!!</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>この時点で、茹で上がりへの期待しかありません。</p>
<!-- /wp:paragraph -->"""
    assert fixed.count(old_raw)==1
    fixed=fixed.replace(old_raw,new_raw,1)

    old_sake="""<!-- wp:paragraph -->
<p>家にあった日本酒を少し合わせて味わってみたら、これがまた……。</p>
<!-- /wp:paragraph -->"""
    new_sake="""<!-- wp:paragraph -->
<p>正月用に買っていた日本酒の<strong>「獺祭」</strong>をカニ味噌に少し入れて味わってみたら、これがまた……。</p>
<!-- /wp:paragraph -->"""
    assert fixed.count(old_sake)==1
    fixed=fixed.replace(old_sake,new_sake,1)

    old_life="""<!-- wp:paragraph -->
<p><strong>美味しいものは、人をちゃんと幸せにする。</strong></p>
<!-- /wp:paragraph -->"""
    new_life=old_life+"""

<!-- wp:paragraph -->
<p>そして、<strong>生きていれば美味しいものが食べられる。</strong></p>
<!-- /wp:paragraph -->"""
    assert fixed.count(old_life)==1
    fixed=fixed.replace(old_life,new_life,1)

    assert "tsurikue-editorial:matubagani:v3" in fixed
    assert "2杯5000円" in fixed
    assert "茹でる前の足を1本だけ味見" in fixed
    assert "「獺祭」" in fixed
    assert "生きていれば美味しいものが食べられる" in fixed
    assert len(re.findall(r"<!-- wp:image\b",fixed))==len(re.findall(r"<!-- wp:image\b",before))
    assert len(re.findall(r"\[blog_parts\s+id=",fixed))==len(re.findall(r"\[blog_parts\s+id=",before))
    assert not block_problems(fixed)

    before_modified=row.get("modified_gmt")
    req(f"{SITE}/wp-json/wp/v2/posts/{PID}",method="POST",payload={"content":fixed})
    after=get_post()
    verify_identity(after)
    actual=raw(after,"content")
    assert "tsurikue-editorial:matubagani:v3" in actual
    assert "2杯5000円" in actual
    assert "茹でる前の足を1本だけ味見" in actual
    assert "「獺祭」" in actual
    assert "生きていれば美味しいものが食べられる" in actual
    assert len(re.findall(r"<!-- wp:image\b",actual))==len(re.findall(r"<!-- wp:image\b",before))
    assert len(re.findall(r"\[blog_parts\s+id=",actual))==len(re.findall(r"\[blog_parts\s+id=",before))
    assert not block_problems(actual)
    assert after.get("modified_gmt")!=before_modified
    after_total=pub_count()
    assert after_total==before_total

    print("# Matsubagani firsthand restoration v3")
    print("- result: **SUCCESS**")
    print(f"- public posts: **{before_total} → {after_total}**")
    print("- post: **2644 / matubagani / publish → publish**")
    print("- historical price detail: **restored (2 crabs / ¥5,000 at that visit)**")
    print("- raw-leg taste detail: **restored**")
    print("- Dassai detail: **restored**")
    print("- original emotional line: **restored**")
    print("- title / slug / featured_media: **unchanged**")
    print("- Gutenberg problems after: **0**")
    print("- modified date: **updated**")

if __name__=="__main__":
    main()
