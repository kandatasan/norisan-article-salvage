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
    # Fetch the *public* document separately: WordPress post title and the
    # actual HTML document title/visible H1 can differ due to SEO/theme filters.
    try:
        public=post.get("link") or SITE+"/tom-and-jerry-exhibition-review/"
        req=urllib.request.Request(public,headers={"User-Agent":"Mozilla/5.0 (compatible; TsurikueTitleAudit/1.0)"})
        with urllib.request.urlopen(req,timeout=25) as response:
            markup=response.read(400000).decode("utf-8",errors="replace")
            status=response.status
        def find(pattern):
            m=re.search(pattern,markup,re.I|re.S)
            return html.unescape(re.sub(r"<[^>]*>","",m.group(1)).strip()) if m else None
        report["public_page"]={
            "http_status":status,
            "html_title":find(r"<title[^>]*>(.*?)</title>"),
            "h1":re.findall(r"<h1\b[^>]*>[\s\S]*?</h1>",markup,re.I)[:4],
            "og_title":find(r'<meta[^>]*property=["\u0027]og:title["\u0027][^>]*content=["\u0027]([^"\u0027]+)'),
            "canonical":find(r'<link[^>]*rel=["\u0027]canonical["\u0027][^>]*href=["\u0027]([^"\u0027]+)'),
            "title_tag_count":len(re.findall(r"<title\b",markup,re.I)),
            "h1_tag_count":len(re.findall(r"<h1\b",markup,re.I)),
            "first_html_500":markup[:500],
        }
    except Exception as err:
        report["public_page_error"]=type(err).__name__+": "+str(err)[:250]
    print("READ_ONLY_TOM_JERRY_TITLE_AUDIT",json.dumps(report,ensure_ascii=False),flush=True)
    target=Path("reports/tom-jerry-title-display-audit.json")
    target.parent.mkdir(exist_ok=True,parents=True)
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
if __name__=="__main__": main()
