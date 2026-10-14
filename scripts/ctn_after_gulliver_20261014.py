#!/usr/bin/env python3
"""Guarded addition of a compact CTN CTA at the end of posts containing Gulliver ads.
    All 16 current, published articles must pass a source-fingerprint check before any write.
    The article whose CTN CTA is already at the end is kept unchanged.
"""
from __future__ import annotations
import base64, hashlib, html, json, os, re, sys, urllib.parse, urllib.request
from pathlib import Path

SITE = "https://tsurikue.com"
REPORT = Path("reports/ctn-after-gulliver-20261014")
POSTS = {
# post_id: (slug, expected SHA256 of live WP raw content, top copy segments, bottom segments)
2329: ("ux300h","52ddcd7b04f70256fc9456e5815a3b7be2939848598f5d4022c1733bcda2e46c",["中古UXも候補に入れるなら、","今の車の値段も確認。"],["下取り額と買取査定を比べて、","乗り換え予算の参考に。"]),
2517: ("ux-koukai","2135cd5b18e0e2790a19154600476d8a6a82060fddcfb14d1ba50a9975ab4510",["次のUXを探し始めたら、","今の車はいくらで売れる？"],["下取りだけで決めず、","査定額も比べてみよう。"]),
2948: ("lexus-ux-used","fc848d96dda8fbe6decade5499fa77b2a1cc43e1f0e482d8719dce8da60320c1",["お宝UXを見つけたら、","今の愛車の売値も確認。"],["下取り額と買取査定を比べて、","買い替え予算を考えよう。"]),
2956: ("lexus-ux-price","5a3cfb39cc5f5c64d4316793733b2b2e5371934f6b09c9bb2b15fd1d9cc26a0e",["欲しいUXの価格が見えたら、","今の車の価値もチェック。"],["下取りだけに絞らず、","査定額を比べて判断しよう。"]),
2962: ("lexus-ux-discount","10b60de9ab12e3cc70fcc51925e44c2629e5a3bd8d43d542242a98da6528c7e1",["値引きだけで予算を決めず、","今の車の売値も比べよう。"],["買取査定と下取りを比較して、","納得できる方を選ぼう。"]),
3570: ("lexus-ux-emotional-explorer","a141fd983dd41bfe0e8605ed65b20b402c7522ea674b217e66ff6dd71173676c",["欲しい特別仕様車が見つかったら、","乗り換え予算も確認。"],["今の車の査定額がわかると、","予算を考えやすくなります。"]),
3601: ("lexus-ux250h-used-vs-ux300h","2c45e1893ad85d13898f7deca135c90ecaeffd6c818aaa2140d2fd1c7b41688f",["中古250hか新車300hか。","今の車の売値も判断材料に。"],["買取査定と下取りを比べて、","購入予算を考えてみよう。"]),
3604: ("lexus-ux-vs-nx","0e56387b153357b61da5d3062ed53cf0e023afe6fbbd8c6b47c8adebb6e39810",["UXとNX、どちらにする？","今の車の売値も比べよう。"],["下取り額と買取査定の差も、","乗り換え予算の判断材料。"]),
3606: ("lexus-ux-vs-lbx","45bd6a170db2eda3b6870b64b91824ba7af8fc362ffb5a3bc9ba66ea3cf1b41f",["LBXかUXか迷ったら、","今の車の売値も確認。"],["査定額を比べてから、","無理のない予算を考えよう。"]),
3608: ("lexus-lbx-regret","6cad1ff3863811edd84dc705df544c1842ace91875982f1a339583efceb6a22d",["乗り換え先を探すなら、","今の車の買取価格も確認。"],["下取りだけで決めず、","いくらになるか比べてみよう。"]),
3611: ("lexus-lbx-options","a1e0a70c8d243f64ff8aa56922d332cd32fccafed5f9c2eec7c9b0be8d5ca0a0",["欲しい装備を諦める前に、","今の車の売値も確認。"],["査定額と下取りを比べて、","購入予算の判断材料に。"]),
3835: ("goodbuy","00a45e47781a110d1c5eb992f50f68a5b10403ec561a41d5dc9bb47a493bde2b",["次のレクサスを決める前に、","今の車の査定額を比較。"],["下取りだけで決めず、","納得できる売り方を選ぼう。"]),
3863: ("lexus-lbx-cheap","5a46b99aad79d0654587b62803dd116078b2d7a16aa3ee59d6bb78a8a05bc1ba",["欲しいLBXを諦める前に、","愛車の売値もチェック。"],["下取りと買取査定を比べて、","買い替え総額を考えよう。"]),
3945: ("lexus-lbx-used","7d6aa22f6c603a90e55626d946c59db018a7eaf8532b639993d4998d4849155b",["中古LBXの候補が決まったら、","今の車の売値も確認。"],["下取り額と査定額を比べて、","買い替え予算の参考に。"]),
3965: ("tanto-6years-review","2fe69299a47d625f0cf350922e86dbd9cdee6bee6d840b3e1a6ef56d13f333ce",["中古タントへ乗り換えるなら、","今の車の査定額も確認。"],["下取りだけで決めず、","買取査定も比べてみよう。"]),
3973: ("tanto-used-best-year","effe9934b449897a14b0e4386957435a3dcc034410534773f3bc8f2628092354",["欲しい年式が決まったら、","今の車の売値もチェック。"],["下取り額と買取査定を比べて、","買い替え予算を考えよう。"]),
}
ALREADY_AT_END = (4004, "tanto-model-history", "55cc74c22f38e046b2018c6db2acfaba3a8abf204a6ce162f8f9d5d564d70307")
SHORTCODE = '<!-- wp:shortcode -->\n[blog_parts id="3788"]\n<!-- /wp:shortcode -->'
SOURCE_MARKERS = ('[blog_parts id="2843"]','[blog_parts id="4172"]','a8mat=4B65SD+8DUSHE+9QU+NVHCY')
MARKER = "tsq-ctn-last-20261014"
PROTECTED = ("id","slug","status","title","featured_media","categories","author")
QUERY = urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,content,featured_media,categories,author"})
STYLE = {
  "top":"max-width:580px;margin:1.1em auto .32em;padding-top:.7em;border-top:1px solid #e1e9f0;text-align:center;font-weight:700;font-size:clamp(13px,3.5vw,15px);line-height:1.65;color:#253c58;",
  "bottom":"max-width:580px;margin:.28em auto 1.2em;text-align:center;font-weight:400;font-size:clamp(12px,3.2vw,13px);line-height:1.6;color:#576777;",
}
def sha(s): return hashlib.sha256(s.encode("utf-8")).hexdigest()
def microcopy(lines,kind):
    if len(lines)!=2 or any(not x or len(x)>19 or "<" in x or "\n" in x for x in lines):
        raise RuntimeError("invalid CTA phrase")
    spans="<wbr>".join('<span style="display:inline-block;white-space:nowrap;">'+html.escape(x)+'</span>' for x in lines)
    return ('<!-- wp:html -->\n<div class="'+MARKER+' '+kind+'" style="'+STYLE[kind]+'">'+spans+'</div>\n<!-- /wp:html -->')
def append_cta(s,top,bottom):
    if MARKER in s or SHORTCODE in s: raise RuntimeError("CTA already present")
    tail="\n" if s.endswith("\n") else "\n\n"
    return s + tail + microcopy(top,"top")+"\n\n"+SHORTCODE+"\n\n"+microcopy(bottom,"bottom")+"\n"
def make_request(path,auth,payload=None):
    headers={"Authorization":auth,"Accept":"application/json","User-Agent":"tsurikue-ctn-after-gulliver/1.0"}
    if payload is not None: headers["Content-Type"]="application/json; charset=utf-8"
    req=urllib.request.Request(SITE+path,headers=headers,method="POST" if payload is not None else "GET",
        data=json.dumps(payload,ensure_ascii=False).encode("utf-8") if payload is not None else None)
    with urllib.request.urlopen(req,timeout=60) as r: return json.load(r),dict(r.headers)
def get(pid,auth): return make_request(f"/wp-json/wp/v2/posts/{pid}?{QUERY}",auth)[0]
def raw(row): return row["content"]["raw"]
def public_count(auth):
    _,h=make_request("/wp-json/wp/v2/posts?status=publish&per_page=1&_fields=id",auth)
    return int(h["X-WP-Total"])
def check_unchanged(ctn_last):
    # The existing 17th Gulliver post already has a CTN CTA at its end.
    if ctn_last.count('[blog_parts id="2184"]')!=1: raise RuntimeError("preserved end CTN moved")
    trailing=ctn_last.split('[blog_parts id="2184"]',1)[-1]
    if len(trailing)>350 or '[blog_parts id="2843"]' in trailing: raise RuntimeError("preserved CTN not at end")
def ensure_rendered_ctn(auth):
    reference=get(3767,auth) # Land Cruiser FJ price uses the live CTN 3104 button.
    if '[blog_parts id="3788"]' not in raw(reference): raise RuntimeError("CTN3104 part not confirmed in currently published post")
    if not reference.get("content",{}).get("rendered","").strip(): raise RuntimeError("CTN shortcode rendering not verifiable")
def prepare(auth):
    count=public_count(auth);ensure_rendered_ctn(auth)
    preserve=get(ALREADY_AT_END[0],auth)
    if (preserve["id"],preserve["slug"],preserve["status"])!=(ALREADY_AT_END[0],ALREADY_AT_END[1],"publish"):
        raise RuntimeError("preserve-only post identity mismatch")
    if sha(raw(preserve))!=ALREADY_AT_END[2]:raise RuntimeError("preserve-only post differs from baseline")
    check_unchanged(raw(preserve))
    plan=[]
    for pid,(slug,expected,top,bottom) in POSTS.items():
        row=get(pid,auth);orig=raw(row)
        if (row["id"],row["slug"],row["status"])!=(pid,slug,"publish"):
            raise RuntimeError("post identity or status changed "+slug)
        if sha(orig)!=expected:
            raise RuntimeError("live body changed since approved source baseline "+slug+"; no writes")
        if not any(m in orig for m in SOURCE_MARKERS):raise RuntimeError("Gulliver link or button missing "+slug)
        new=append_cta(orig,top,bottom)
        if not new.startswith(orig) or new.count(MARKER)!=2 or new.count('[blog_parts id="3788"]')!=orig.count('[blog_parts id="3788"]')+1:
            raise RuntimeError("non-append change or unexpected CTA count "+slug)
        if len(re.findall(r'<!-- wp:',new))-len(re.findall(r'<!-- wp:',orig))!=3:
            raise RuntimeError("new block count mismatch "+slug)
        if len(re.findall(r'<!-- /wp:',new))-len(re.findall(r'<!-- /wp:',orig))!=3:
            raise RuntimeError("new closing block count mismatch "+slug)
        plan.append((pid,slug,expected,row,new,top,bottom))
    REPORT.mkdir(parents=True,exist_ok=True)
    (REPORT/"preflight.json").write_text(json.dumps({
        "status":"PREFLIGHT_OK","published_before":count,"preserved_post":ALREADY_AT_END[0],
        "targets":[{"id":pid,"slug":slug,"before_sha":expected,"proposed_sha":sha(new),"last_ctn_count":1}
                   for pid,slug,expected,row,new,top,bottom in plan]
    },ensure_ascii=False,indent=2),encoding="utf-8")
    print("PREFLIGHT_OK",len(plan),"append-only CTN posts; existing end CTN preserved; published",count,flush=True)
    return plan,count
def run(mode):
    user=os.getenv("TSURIKUE_WP_USER");password=os.getenv("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:raise RuntimeError("WordPress secrets unavailable")
    auth="Basic "+base64.b64encode(f"{user}:{password}".encode()).decode()
    plan,total=prepare(auth)
    if mode=="check":return
    done=[]
    try:
        for pid,slug,expected,before,new,top,bottom in plan:
            live=get(pid,auth)
            if sha(raw(live))!=expected or live["status"]!="publish":
                raise RuntimeError("concurrent content change "+slug)
            make_request(f"/wp-json/wp/v2/posts/{pid}",auth,{"content":new})
            done.append((pid,slug,before,new))
            after=get(pid,auth)
            if any(after[k]!=before[k] for k in PROTECTED):raise RuntimeError("metadata altered "+slug)
            if raw(after)!=new:raise RuntimeError("saved body mismatch "+slug)
            rendered=after["content"].get("rendered","")
            if not all(x in rendered for x in [top[0],bottom[0]]):raise RuntimeError("rendered microcopy missing "+slug)
            # Keep a rendered shortcode check: SWELL may add link wrapper around it.
            if "CTN" not in rendered and "px.a8.net" not in rendered: raise RuntimeError("CTA not rendered "+slug)
            print("LIVE_VERIFIED",pid,slug,flush=True)
        if public_count(auth)!=total:raise RuntimeError("public article count changed")
        preserved=get(ALREADY_AT_END[0],auth)
        if sha(raw(preserved))!=ALREADY_AT_END[2]:raise RuntimeError("preserved CTN was modified")
        (REPORT/"result.json").write_text(json.dumps({
            "result":"SUCCESS","updated_post_ids":[x[0] for x in plan],
            "preserved_post_id":ALREADY_AT_END[0],"published_post_count":total
        },ensure_ascii=False,indent=2),encoding="utf-8")
    except Exception:
        for pid,slug,before,new in reversed(done):
            try:
                now=get(pid,auth)
                if sha(raw(now))==sha(new):
                    make_request(f"/wp-json/wp/v2/posts/{pid}",auth,{"content":raw(before)})
                    print("ROLLBACK",pid,slug,flush=True)
            except Exception as err:print("ROLLBACK_FAILED",pid,slug,repr(err),flush=True)
        raise
if __name__=="__main__":
    mode=sys.argv[1] if len(sys.argv)>1 else "check"
    if mode not in ("check","apply"):raise SystemExit("Expected check or apply")
    run(mode)
