#!/usr/bin/env python3
import base64, json, os, urllib.parse, urllib.request, hashlib

SITE="https://tsurikue.com"
POST_ID=3863
UA="tsurikue-lbx-cheap-prepublish-fix/1.0"

OLD_MARKET='<p>2026年9月20日にグーネットを確認すると、LBXは226台掲載され、車両価格は<strong>344.8万円〜777.7万円</strong>でした。</p>'
NEW_MARKET='<p>2026年9月26日時点で、グーネットにはLBXが232台掲載され、車両価格は<strong>379万円〜798万円</strong>でした。</p>'

OLD_GULLIVER='''<!-- wp:paragraph -->
<p>欲しかったHUDやAdvanced Park付きの1台が見つかれば、新車で全部追加するより話が早いこともあります。</p>
<!-- /wp:paragraph -->

<!-- wp:shortcode -->
[blog_parts id="2843"]
<!-- /wp:shortcode -->'''

NEW_GULLIVER='''<!-- wp:paragraph -->
<p>欲しかったHUDやAdvanced Park付きの1台が見つかれば、新車で全部追加するより話が早いこともあります。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>中古LBXを探すなら、<strong>ガリバーの在庫も候補に入れておくと比較しやすい</strong>です。欲しいグレードや装備が決まっている人は、同じ条件で在庫を見比べてみてください。</p>
<!-- /wp:paragraph -->

<!-- wp:shortcode -->
[blog_parts id="2843"]
<!-- /wp:shortcode -->'''

def auth():
    u=os.environ["TSURIKUE_WP_USER"]; p=os.environ["TSURIKUE_WP_APP_PASSWORD"]
    return "Basic "+base64.b64encode(f"{u}:{p}".encode()).decode()

def req(url,a,data=None,method=None):
    headers={"Authorization":a,"Accept":"application/json","User-Agent":UA}
    body=None
    if data is not None:
        body=json.dumps(data,ensure_ascii=False).encode()
        headers["Content-Type"]="application/json"
    r=urllib.request.Request(url,headers=headers,data=body,method=method or ("POST" if body else "GET"))
    with urllib.request.urlopen(r,timeout=60) as x:
        return json.loads(x.read().decode()),dict(x.headers)

def raw(row,key):
    v=row.get(key) or {}
    return (v.get("raw") or v.get("rendered") or "") if isinstance(v,dict) else str(v)

def published_count(a):
    q=urllib.parse.urlencode({"status":"publish","per_page":1,"_fields":"id"})
    _,h=req(f"{SITE}/wp-json/wp/v2/posts?{q}",a)
    return int(h.get("X-WP-Total","0"))

def main():
    a=auth()
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,content,featured_media,categories,tags,modified"})
    before,_=req(f"{SITE}/wp-json/wp/v2/posts/{POST_ID}?{q}",a)
    content=raw(before,"content")
    pub_before=published_count(a)

    if before.get("status")!="draft": raise SystemExit(f"STOP status={before.get('status')}")
    if before.get("slug")!="lexus-lbx-cheap": raise SystemExit("STOP slug mismatch")
    if content.count(OLD_MARKET)!=1: raise SystemExit(f"STOP market old count={content.count(OLD_MARKET)}")
    if content.count(OLD_GULLIVER)!=1: raise SystemExit(f"STOP gulliver anchor count={content.count(OLD_GULLIVER)}")
    if content.count('[blog_parts id="2846"]')!=1 or content.count('[blog_parts id="2843"]')!=1:
        raise SystemExit("STOP affiliate shortcode counts unexpected")

    target=content.replace(OLD_MARKET,NEW_MARKET,1).replace(OLD_GULLIVER,NEW_GULLIVER,1)

    payload={"content":target,"status":"draft"}
    updated,_=req(f"{SITE}/wp-json/wp/v2/posts/{POST_ID}",a,payload,"POST")
    after,_=req(f"{SITE}/wp-json/wp/v2/posts/{POST_ID}?{q}",a)
    final=raw(after,"content")
    pub_after=published_count(a)

    checks={
      "status_draft": after.get("status")=="draft",
      "slug_unchanged": after.get("slug")==before.get("slug"),
      "title_unchanged": raw(after,"title")==raw(before,"title"),
      "featured_unchanged": after.get("featured_media")==before.get("featured_media"),
      "categories_unchanged": after.get("categories")==before.get("categories"),
      "tags_unchanged": after.get("tags")==before.get("tags"),
      "market_updated": NEW_MARKET in final and OLD_MARKET not in final,
      "gulliver_copy_added": "ガリバーの在庫も候補に入れておくと比較しやすい" in final,
      "ctn_once": final.count('[blog_parts id="2846"]')==1,
      "gulliver_once": final.count('[blog_parts id="2843"]')==1,
      "published_count_unchanged": pub_before==pub_after,
    }
    if not all(checks.values()):
        raise SystemExit("STOP verification failed: "+json.dumps(checks,ensure_ascii=False))

    print("# LBX cheap pre-publish fix")
    print("- result: **SUCCESS**")
    print(f"- post: **{POST_ID} / {after.get('slug')} / draft → draft**")
    print(f"- used-market snapshot: **2026-09-20 226台・344.8〜777.7万円 → 2026-09-26 232台・379〜798万円**")
    print("- Gulliver role copy: **added before blog_parts 2843**")
    print("- CTN blog_parts 2846: **unchanged / 1**")
    print("- Gulliver blog_parts 2843: **unchanged / 1**")
    print(f"- title / slug / featured_media / taxonomy: **unchanged**")
    print(f"- public posts: **{pub_before} → {pub_after}**")
    print(f"- content sha256: **{hashlib.sha256(final.encode()).hexdigest()}**")
    print("- publish_count: **0**")
    print("- wordpress write: **draft content only**")

if __name__=="__main__": main()
