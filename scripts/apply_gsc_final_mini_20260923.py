#!/usr/bin/env python3
from __future__ import annotations
import base64, json, os, re, urllib.request

SITE="https://tsurikue.com"
UA="tsurikue-gsc-final-mini-20260923/1.0"

TARGETS=[
  {
    "id":2907,
    "slug":"lexus-ux-cargo",
    "title":"レクサスUXの荷室は狭い？ゴルフバッグ・買い物で使えるかをチェック",
    "featured_media":2209,
    "kind":"ux",
    "mark":"横置きできるかは、レクサス公式の参考搭載数だけでは断定できません"
  },
  {
    "id":3611,
    "slug":"lexus-lbx-options",
    "title":"レクサスLBXのおすすめオプションは？ディーラー見積もりから必要・不要を本音で整理",
    "featured_media":1700,
    "kind":"lbx",
    "mark":"LBXで不要だと思うオプションは？私はマークレビンソンを見送る"
  },
  {
    "id":3633,
    "slug":"karato-market",
    "title":"唐戸市場で何食べる？おすすめは一本アナゴとマグロの脳天｜寿司・ふぐも紹介",
    "featured_media":1023,
    "kind":"karato",
    "mark":"唐戸市場のマグロの脳天｜脂トロトロなのにマグロの風味が濃い"
  }
]

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

def get_post(pid):
    row,_=req(f"{SITE}/wp-json/wp/v2/posts/{pid}?context=edit")
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

def h2(t): return f'<!-- wp:heading -->\n<h2 class="wp-block-heading">{t}</h2>\n<!-- /wp:heading -->'
def h3(t): return f'<!-- wp:heading {{"level":3}} -->\n<h3 class="wp-block-heading">{t}</h3>\n<!-- /wp:heading -->'

def replace_heading(content,level,old,new):
    a=h2(old) if level==2 else h3(old)
    b=h2(new) if level==2 else h3(new)
    if content.count(a)!=1:
        raise RuntimeError(f"heading guard failed: {old}")
    return content.replace(a,b,1)

def insert_after_heading(content,title,block):
    a=h2(title)
    if content.count(a)!=1:
        raise RuntimeError(f"heading guard failed: {title}")
    pos=content.index(a)+len(a)
    return content[:pos]+"\n\n"+block+content[pos:]

UX_NOTE='''<!-- wp:paragraph -->
<p><strong>「ゴルフバッグを横置きできる？」</strong>については、レクサス公式の参考搭載数だけでは断定できません。<br>バッグの形状やクラブの長さで変わるため、横置き前提なら<strong>自分のバッグを持って実車で確認するのが確実</strong>です。</p>
<!-- /wp:paragraph -->'''

def make_fixed(content,kind):
    if kind=="ux":
        content=replace_heading(
            content,2,
            "ゴルフバッグは積める？",
            "レクサスUXにゴルフバッグは積める？横置きは実車確認が確実"
        )
        return insert_after_heading(
            content,
            "レクサスUXにゴルフバッグは積める？横置きは実車確認が確実",
            UX_NOTE
        )
    if kind=="lbx":
        return replace_heading(
            content,2,
            "マークレビンソンは魅力的。でも私はLBXなら見送る",
            "LBXで不要だと思うオプションは？私はマークレビンソンを見送る"
        )
    if kind=="karato":
        return replace_heading(
            content,3,
            "マグロの脳天｜脂トロトロなのにマグロの風味が濃い",
            "唐戸市場のマグロの脳天｜脂トロトロなのにマグロの風味が濃い"
        )
    raise RuntimeError(kind)

def verify_identity(row,t):
    assert row.get("id")==t["id"]
    assert row.get("slug")==t["slug"]
    assert row.get("status")=="publish"
    assert raw(row,"title")==t["title"]
    assert int(row.get("featured_media") or 0)==t["featured_media"]

def main():
    before_total=pub_count()
    prepared=[]
    for t in TARGETS:
        row=get_post(t["id"]); verify_identity(row,t)
        before=raw(row,"content")
        assert t["mark"] not in before
        assert not block_problems(before)
        fixed=make_fixed(before,t["kind"])
        assert t["mark"] in fixed
        assert len(re.findall(r"<!-- wp:image\b",fixed))==len(re.findall(r"<!-- wp:image\b",before))
        assert len(re.findall(r"\[blog_parts\s+id=",fixed))==len(re.findall(r"\[blog_parts\s+id=",before))
        assert not block_problems(fixed)
        prepared.append({
          "target":t,
          "before_content":before,
          "before_title":raw(row,"title"),
          "before_modified_gmt":row.get("modified_gmt"),
          "fixed_content":fixed
        })

    changed=[]
    try:
        for item in prepared:
            t=item["target"]
            req(f"{SITE}/wp-json/wp/v2/posts/{t['id']}",method="POST",payload={"content":item["fixed_content"]})
            after=get_post(t["id"])
            verify_identity(after,t)
            actual=raw(after,"content")
            assert t["mark"] in actual
            assert len(re.findall(r"<!-- wp:image\b",actual))==len(re.findall(r"<!-- wp:image\b",item["before_content"]))
            assert len(re.findall(r"\[blog_parts\s+id=",actual))==len(re.findall(r"\[blog_parts\s+id=",item["before_content"]))
            assert not block_problems(actual)
            assert after.get("modified_gmt")!=item["before_modified_gmt"]
            changed.append(item)
    except Exception:
        for item in reversed(changed):
            t=item["target"]
            try:
                req(f"{SITE}/wp-json/wp/v2/posts/{t['id']}",method="POST",payload={"content":item["before_content"]})
            except Exception:
                pass
        raise

    after_total=pub_count()
    assert after_total==before_total
    print("# GSC final mini rewrite 2026-09-23")
    print("- result: **SUCCESS**")
    print(f"- public posts: **{before_total} → {after_total}**")
    print("- posts updated: **3**")
    print("- title / slug / status / featured_media: **unchanged**")
    print("- image counts / blog_parts counts: **unchanged**")
    print("- Gutenberg problems after: **0**")
    print("- modified date: **updated on all 3 posts**")
    for item in changed:
        t=item["target"]
        print(f"- {t['slug']} (post {t['id']}): **publish → publish** / final mini rewrite applied")

if __name__=="__main__":
    main()
