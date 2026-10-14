#!/usr/bin/env python3
"""Wave 1: compact context-aware CTA wrappers, fail closed on any post drift."""
from __future__ import annotations
import base64
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request

SITE = "https://tsurikue.com"
OUT = Path("reports/cta-compact-wave1-20261014")
TARGETS = {
    2222: {"slug":"ux-resale","sha":"e76b2971ff6bc7fe99d407e4cbda1aa87fd7649934664b587d537e5f15d002d4","part":2184,
           "old":"査定額に納得してから、売るか決めればOK。",
           "top":["427万円で売れた私のUX。","あなたの愛車はいくら？"],
           "bottom":["査定額を比べてから、","売るかどうか決められます。"],
           "extra_after":"これが、何度も査定を受けて実際に売却した私の結論です。",
           "extra_top":["1社の査定だけで、","愛車の価値を決めない。"],
           "extra_bottom":["ディーラー下取りとの","比較材料にもなります。"]},
    3614: {"slug":"car-sell-high","sha":"1c20c9618514389d0c6e7c5462a70390aed8bab87ceda40350939b99f13ac8d2","part":2184,
           "old":"納得できる金額なら、そのとき売却を考える。",
           "top":["私の場合、CTNからの連絡は","2社だけでした。"],
           "bottom":["やり取りは最大3社。","売却は金額を見てから。"],
           "extra_after":"高く売れた分は、そのまま次の車を楽しむための予算になります。",
           "extra_top":["今の車をいくらで売れるか。","それも買い替え予算です。"],
           "extra_bottom":["下取り額と比べて、","納得できる売却先を選ぼう。"]},
    3945: {"slug":"lexus-lbx-used","sha":"7a58c82a73605d62ec92a73180f21925504fec758e50f9d86c9c8c32096fd5b6","part":2843,
           "top":["欲しい装備が決まったら、","中古LBXの在庫を比較。"],
           "bottom":["同じグレードでも、","支払総額と保証は要確認。"]},
    3973: {"slug":"tanto-used-best-year","sha":"01e2b309ccc3d780a64a344b73500a78c0128e76332029d67b52b55e1d916517","part":2843,
           "top":["2019年以降の4代目から、","中古タントを探してみよう。"],
           "bottom":["年式だけじゃなく、","装備と支払総額も比べよう。"]},
}
SC = '<!-- wp:shortcode -->\n[blog_parts id="%s"]\n<!-- /wp:shortcode -->'
BLOCK_RE = re.compile(r'<!-- wp:paragraph(?: [^\n]*)? -->.*?<!-- /wp:paragraph -->',re.S)
SAFE_FIELDS = ("id","slug","status","title","featured_media","categories","author")
WPQ = urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,content,featured_media,categories,author"})
def sha(s): return hashlib.sha256(s.encode("utf-8")).hexdigest()
def safe_copy(lines, kind):
    if not (1 <= len(lines) <= 2) or any(not x or len(x) > 20 or "<" in x for x in lines):
        raise ValueError("invalid copy phrase")
    styles = {
        "top":"text-align:center;margin:1.05em auto .35em;line-height:1.55;font-size:clamp(13px,3.6vw,15px);font-weight:700;color:#253c58;",
        "bottom":"text-align:center;margin:.28em auto 1.15em;line-height:1.5;font-size:clamp(12px,3.2vw,13px);color:#576777;"
    }
    spans = "<wbr>".join('<span style="display:inline-block;white-space:nowrap;">'+html.escape(x)+'</span>' for x in lines)
    return ('<!-- wp:html -->\n<div class="tsq-cta-microcopy tsq-cta-'+kind+
            '" style="'+styles[kind]+'">'+spans+'</div>\n<!-- /wp:html -->')
def transform(s, cfg):
    part = cfg["part"]
    anchor = SC % part
    if s.count(anchor) != 1: raise RuntimeError("anchor count mismatched for "+cfg["slug"])
    top = safe_copy(cfg["top"],"top")
    bottom = safe_copy(cfg["bottom"],"bottom")
    if "old" in cfg:
        a,b = s.split(anchor,1)
        pre = re.search(r'<!-- wp:paragraph(?: [^\n]*)? -->\s*<p class="has-text-align-center"><strong>'+re.escape(cfg["old"])+r'</strong></p>\s*<!-- /wp:paragraph -->\s*$',a,re.S)
        if pre is None: raise RuntimeError("existing CTN microcopy changed: "+cfg["slug"])
        s=a[:pre.start()]+top+"\n\n"+anchor+"\n\n"+bottom+b
    else:
        s=s.replace(anchor,top+"\n\n"+anchor+"\n\n"+bottom,1)
    if "extra_after" in cfg:
        blocks=[m for m in BLOCK_RE.finditer(s) if cfg["extra_after"] in m.group(0)]
        if len(blocks)!=1: raise RuntimeError("extra placement anchor mismatched: "+cfg["slug"])
        p=blocks[0].end()
        extra = (safe_copy(cfg["extra_top"],"top")+"\n\n"+anchor+"\n\n"+
                 safe_copy(cfg["extra_bottom"],"bottom"))
        s=s[:p]+"\n\n"+extra+s[p:]
    return s

def request(path,auth,payload=None):
    headers={"Authorization":auth,"Accept":"application/json","User-Agent":"tsurikue-cta-compact-wave1/1.0"}
    if payload is not None: headers["Content-Type"]="application/json; charset=utf-8"
    r=urllib.request.Request(SITE+path,headers=headers,method="POST" if payload is not None else "GET",
        data=json.dumps(payload,ensure_ascii=False).encode("utf-8") if payload is not None else None)
    with urllib.request.urlopen(r,timeout=60) as h: return json.load(h),dict(h.headers)
def fetch(pid,auth): return request("/wp-json/wp/v2/posts/%d?%s"%(pid,WPQ),auth)[0]
def raw(r): return r["content"]["raw"]
def published_count(auth):
    _,headers=request('/wp-json/wp/v2/posts?status=publish&per_page=1&_fields=id',auth)
    return int(headers["X-WP-Total"])
def validate_change(before,after,cfg):
    if before==after: raise RuntimeError("no-op")
    if after.count(SC%cfg["part"])!=1+(1 if "extra_after" in cfg else 0):
        raise RuntimeError("shortcode count unexpected")
    for p in ("<!-- wp:","<!-- /wp:"):
        if before.count(p) == 0 or after.count(p) <= before.count(p): raise RuntimeError("invalid Gutenberg delta")
    for patt in (r'<img\b[^>]*>',r'\bwp-image-\d+',r'https://px\.a8\.net/svt/ejp\?a8mat=[^"\s<]+'):
        if re.findall(patt,before)!=re.findall(patt,after): raise RuntimeError("ads or media modified")
    for pn in re.findall(r'\[blog_parts id="(\d+)"\]',before):
        if pn!=str(cfg["part"]) and after.count('[blog_parts id="'+pn+'"]')!=before.count('[blog_parts id="'+pn+'"]'):
            raise RuntimeError("unrelated blog part changed")
    if "old" in cfg and cfg["old"] in after: raise RuntimeError("old CTN copy not removed")
def main(mode):
    user=os.environ.get("TSURIKUE_WP_USER");password=os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password: raise RuntimeError("WP secrets unavailable; no writes")
    auth="Basic "+base64.b64encode((user+":"+password).encode()).decode()
    count_before=published_count(auth)
    prepared=[]
    for pid,cfg in TARGETS.items():
        post=fetch(pid,auth)
        if (post.get("id"),post.get("slug"),post.get("status")) != (pid,cfg["slug"],"publish"):
            raise RuntimeError("identity/status mismatch: "+cfg["slug"])
        content=raw(post)
        if sha(content)!=cfg["sha"]: raise RuntimeError("live post differs from Oct14 export: "+cfg["slug"]+" "+sha(content))
        modified=transform(content,cfg)
        validate_change(content,modified,cfg)
        prepared.append((pid,cfg,post,modified))
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"preflight.json").write_text(json.dumps([{"id":pid,"slug":cfg["slug"],"from":cfg["sha"],"to":sha(new),"shortcodes":new.count(SC%cfg["part"])} for pid,cfg,old,new in prepared],ensure_ascii=False,indent=2),encoding="utf-8")
    print("PREFLIGHT_OK",len(prepared),"posts; public count",count_before,flush=True)
    if mode=="check": return
    done=[]
    try:
        for pid,cfg,original,new in prepared:
            latest=fetch(pid,auth)
            if sha(raw(latest))!=cfg["sha"] or latest["status"]!="publish": raise RuntimeError("concurrent edit "+cfg["slug"])
            request('/wp-json/wp/v2/posts/%d'%pid,auth,{"content":new})
            done.append((pid,cfg,original,new))
            actual=fetch(pid,auth)
            if any(actual.get(k)!=original.get(k) for k in SAFE_FIELDS): raise RuntimeError("metadata changed "+cfg["slug"])
            if raw(actual)!=new: raise RuntimeError("saved content mismatch "+cfg["slug"])
            rendered=actual["content"]["rendered"]
            if cfg["top"][0] not in rendered or cfg["bottom"][0] not in rendered:
                raise RuntimeError("rendered copy missing "+cfg["slug"])
            print("LIVE_VERIFIED",pid,cfg["slug"],flush=True)
        if published_count(auth)!=count_before: raise RuntimeError("published count changed")
        (OUT/"result.json").write_text(json.dumps({"result":"SUCCESS","post_ids":list(TARGETS),"published_count":count_before},indent=2),encoding="utf-8")
    except Exception:
        for pid,cfg,original,new in reversed(done):
            try:
                now=fetch(pid,auth)
                if sha(raw(now))==sha(new):
                    request('/wp-json/wp/v2/posts/%d'%pid,auth,{"content":raw(original)})
                    print("ROLLBACK",cfg["slug"],flush=True)
            except Exception as err: print("ROLLBACK_FAILED",cfg["slug"],repr(err),flush=True)
        raise
if __name__=="__main__":
    mode=sys.argv[1] if len(sys.argv)>1 else "check"
    if mode not in ("check","apply"): raise SystemExit("usage: check|apply")
    main(mode)
