#!/usr/bin/env python3
import base64, html, json, os, re, urllib.parse, urllib.request

SITE="https://tsurikue.com"
UA="tsurikue-lbx-cheap-final-audit/1.0"
IDS=[3863,3835,3611,3608,3816]

def auth():
    u=os.environ["TSURIKUE_WP_USER"]; p=os.environ["TSURIKUE_WP_APP_PASSWORD"]
    return "Basic "+base64.b64encode(f"{u}:{p}".encode()).decode()

def get_json(url,a):
    req=urllib.request.Request(url,headers={"Authorization":a,"Accept":"application/json","User-Agent":UA})
    with urllib.request.urlopen(req,timeout=60) as r:
        return json.loads(r.read().decode()),dict(r.headers)

def raw(row,key):
    v=row.get(key) or {}
    return (v.get("raw") or v.get("rendered") or "") if isinstance(v,dict) else str(v)

def plain(s):
    s=html.unescape(s or "")
    s=re.sub(r"<!--.*?-->"," ",s,flags=re.S)
    s=re.sub(r"<script\b.*?</script>"," ",s,flags=re.I|re.S)
    s=re.sub(r"<style\b.*?</style>"," ",s,flags=re.I|re.S)
    s=re.sub(r"<[^>]+>"," ",s)
    return re.sub(r"\s+"," ",s).strip()

def fetch_post(pid,a):
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,content,excerpt,featured_media,categories,tags,date,modified,link"})
    row,_=get_json(f"{SITE}/wp-json/wp/v2/posts/{pid}?{q}",a)
    return row

def main():
    a=auth()
    rows={r["id"]:r for r in [fetch_post(i,a) for i in IDS]}
    target=rows[3863]
    content=raw(target,"content")
    text=plain(content)
    headings=re.findall(r"<h([1-6])[^>]*>(.*?)</h\1>",content,flags=re.I|re.S)
    heading_text=[(lvl,plain(t)) for lvl,t in headings]
    urls=re.findall(r'href=["\']([^"\']+)["\']',content,flags=re.I)
    shorts=re.findall(r'\[blog_parts\s+id=["\']?(\d+)',content,flags=re.I)
    money=sorted(set(re.findall(r'\d[\d,\.]*\s*(?:円|万円)',text)))
    years=sorted(set(re.findall(r'20\d{2}年(?:\d{1,2}月)?',text)))
    imgs=re.findall(r'<img\b[^>]*>',content,flags=re.I)
    print("# LBX cheap final pre-publish audit")
    print("- mode: **GET ONLY**")
    print("- wordpress_write_count: **0**")
    print(f"- target: **{target['id']} / {target['slug']} / {target['status']}**")
    print(f"- title: **{plain(raw(target,'title'))}**")
    print(f"- modified: **{target.get('modified')}**")
    print(f"- featured_media: **{target.get('featured_media')}**")
    print(f"- categories: **{target.get('categories')}** / tags: **{target.get('tags')}**")
    print(f"- visible chars: **{len(text)}** / body images: **{len(imgs)}**")
    print(f"- blog_parts: **{shorts}**")
    print(f"- URLs: **{len(urls)}**")
    print(f"- money expressions: **{money}**")
    print(f"- year/month expressions: **{years}**")
    print()
    print("## Headings")
    for lvl,t in heading_text: print(f"- H{lvl}: {t}")
    print()
    print("## Intro (visible text first 1500 chars)")
    print(text[:1500])
    print()
    print("## Ending (visible text last 1600 chars)")
    print(text[-1600:])
    print()
    print("## Affiliate / link snippets")
    for pat in ["blog_parts","px.a8.net","ctn","gulliver","ガリバー","一括査定","中古車","ローン","485万","売却","下取り"]:
        ms=list(re.finditer(pat,content,flags=re.I))
        print(f"### {pat}: {len(ms)}")
        for m in ms[:8]:
            s=max(0,m.start()-220); e=min(len(content),m.end()+320)
            print("- "+plain(content[s:e]))
    print()
    print("## Related published posts")
    for pid in [3835,3611,3608,3816]:
        r=rows[pid]; c=plain(raw(r,"content"))
        print(f"- {pid} / {r['slug']} / {r['status']} / {plain(raw(r,'title'))} / chars={len(c)}")
    print()
    print("## Raw Gutenberg guards")
    print(f"- opening wp blocks: {len(re.findall(r'<!--\\s*wp:',content))}")
    print(f"- closing wp blocks: {len(re.findall(r'<!--\\s*/wp:',content))}")
    print(f"- H1 count: {len(re.findall(r'<h1\\b',content,re.I))}")
    print(f"- TODO/FIXME/placeholder: {bool(re.search(r'TODO|FIXME|placeholder|PHOTO[_ -]?SLOT|未完成|準備中',content,re.I))}")

if __name__=="__main__": main()
