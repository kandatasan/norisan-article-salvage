#!/usr/bin/env python3
"""READ-ONLY diagnosis of Tom and Jerry post title and rendering."""
import os,base64,json,urllib.request,urllib.parse,re,html,hashlib
from pathlib import Path
SITE="https://tsurikue.com"
POST=4282
def call(path,token):
    req=urllib.request.Request(SITE+path,headers={"Authorization":token,"Accept":"application/json","User-Agent":"tsurikue-title-audit-readonly/1.0"})
    with urllib.request.urlopen(req,timeout=65) as response:
        return json.loads(response.read().decode("utf-8"))
def main():
    u=os.environ["TSURIKUE_WP_USER"]
    p=os.environ["TSURIKUE_WP_APP_PASSWORD"]
    token="Basic "+base64.b64encode((u+":"+p).encode()).decode()
    query=urllib.parse.urlencode({"context":"edit"})
    post=call("/wp-json/wp/v2/posts/"+str(POST)+"?"+query,token)
    title=post.get("title") or {}
    content=post.get("content") or {}
    raw=content.get("raw") or ""
    rendered=content.get("rendered") or ""
    plain=html.unescape(re.sub(r"<[^>]*>"," ",rendered))
    report={
        "id":post.get("id"),
        "status":post.get("status"),
        "slug":post.get("slug"),
        "link":post.get("link"),
        "raw_title":title.get("raw"),
        "rendered_title":title.get("rendered"),
        "title_codepoints":len(title.get("raw") or ""),
        "seo_meta_keys":sorted(k for k in (post.get("meta") or {}) if any(w in k.lower() for w in ("title","rank","yoast","seo"))),
        "post_keys":sorted(post.keys()),
        "post_meta_values":{k:v for k,v in (post.get("meta") or {}).items() if any(w in k.lower() for w in ("title","rank","yoast","seo")) and isinstance(v,(str,int,float))},
        "yoast_head_title":(post.get("yoast_head_json") or {}).get("title") if isinstance(post.get("yoast_head_json"),dict) else None,
        "first_heading_blocks":re.findall(r"<h[1-3][^>]*>[\s\S]*?</h[1-3]>",raw)[:6],
        "h1_count":len(re.findall(r"<h1\b",raw,re.I)),
        "paragraph_count":raw.count("<!-- wp:paragraph -->"),
        "photo_count":raw.count("<!-- wp:image "),
        "body_sha256":hashlib.sha256(raw.encode()).hexdigest(),
        "rendered_excerpt":plain[:330],
    }
    print("READ_ONLY_TOM_JERRY_TITLE_AUDIT",json.dumps(report,ensure_ascii=False),flush=True)
    target=Path("reports/tom-jerry-title-display-audit.json")
    target.parent.mkdir(exist_ok=True,parents=True)
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
if __name__=="__main__": main()
