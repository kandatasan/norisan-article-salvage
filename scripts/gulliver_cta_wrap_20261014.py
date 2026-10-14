#!/usr/bin/env python3
"""Compact, article-specific Gulliver CTA wrappers. WP edits gated by exact source baseline."""
from __future__ import annotations
import base64, hashlib, html, json, os, re, sys, urllib.parse, urllib.request
from pathlib import Path

SITE="https://tsurikue.com"
OUT=Path("reports/gulliver-cta-20261014")
PREFIX="tsq-gulliver-micro-20261014"
CTN_PREFIX="<!-- wp:html -->\n<div class=\"tsq-ctn-last-20261014 top\""
GULLIVER_URL="https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY"
SCRIPT_PART='[blog_parts id="2843"]'
MARKER_REGEX=re.compile(r'<a\b[^>]*\bhref=["\']'+re.escape(GULLIVER_URL)+r'["\']',re.I)
BLOCK_REGEX=re.compile(r'<!-- wp:(paragraph|loos/button)(?: [^\n]*)? -->.*?<!-- /wp:\1 -->',re.S)
SHORTCODE='<!-- wp:shortcode -->\n[blog_parts id="2843"]\n<!-- /wp:shortcode -->'
PROTECTED=("id","slug","status","title","featured_media","categories","author")
QUERY=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,content,featured_media,categories,author"})

# Expected hashes match the user's 2026-10-14 WordPress export (rstrip newlines).
# Thereafter only the verified 2026-10-14 CTN-at-end append is allowed.
# Per anchor: [top phrase 1, top phrase 2, bottom phrase 1, bottom phrase 2].
SPECS={
2329:("ux300h","e3b4a96a1f14a7e6e9bb61dd43c53ff27b047e8c623da59b6c60c06e42ea9386",[
 ["250hも300hも気になったら、","中古UXを並べてみよう。","装備・走行距離・支払総額で","候補を比べてみよう。"]]),
2517:("ux-koukai","2135cd5b18e0e2790a19154600476d8a6a82060fddcfb14d1ba50a9975ab4510",[
 ["中古250hなら、まだまだ面白い。","条件の合う1台を探そう。","欲しい装備を決めてから、","年式と車両状態を比較しよう。"]]),
2948:("lexus-ux-used","92786d1818c12f0bb9b8b9f8d3899a280dfcaa5a28ab374451f82fd4e623b5ac",[
 ["200万円台のF SPORTも候補。","次は実際の在庫を見てみよう。","修復歴・整備履歴・保証まで","見比べて選ぼう。"],
 ["買ったあとも好きでいられる","中古UXを探してみよう。","支払総額と装備を比べて、","自分に合う1台を選ぼう。"]]),
2956:("lexus-ux-price","1f781b84bddef502b577b3d38aa0d4b1180659b8d9c2f2cbb6968ddaa4f78aa0",[
 ["新車と中古では予算が変わる。","いまの中古UXも比べてみよう。","年式・装備・支払総額を","そろえて比べてみよう。"],
 ["予算の候補が見えてきたら、","次は中古の在庫をチェック。","価格だけでなく、","状態や保証も確認しよう。"]]),
2962:("lexus-ux-discount","e93c92f41881e872b565713f7e1239e484f0a4fd9d53c23b3b59ac87a2d515d9",[
 ["値引きゼロでも選択肢はある。","中古UXも並べてみよう。","年式・装備・支払総額まで","比較して考えよう。"]]),
3570:("lexus-ux-emotional-explorer","1bfb16e16e105aecc24335ce4a937a210095a5d1f7663732f03c7923ced0355b",[
 ["ベンチレーションも欲しい。","そんな中古UXを探そう。","欲しい装備が付いているか、","1台ずつ確認しよう。"],
 ["Emotional Explorerが気になるなら、","最後は在庫で条件を比較。","状態・走行距離・保証まで","確認してから選ぼう。"]]),
3601:("lexus-ux250h-used-vs-ux300h","3110bbcc222e8c7b154271fa592db37652b5b91cd2bd7ca4faf04cefbdfc3ee0",[
 ["中古250hは価格が魅力。","条件の合うUXを探そう。","年式・走行距離・装備を","同じ目線で比較しよう。"],
 ["どちらにするか迷ったら、","中古250hの在庫も見てみよう。","新車300hの見積もりと","支払総額を比べよう。"]]),
3604:("lexus-ux-vs-nx","e288a0cfda1dca94b0ce9118688fa9e7c0a90ed37414fe147381ebe68842692c",[
 ["UXもNXも中古まで広げると、","選択肢が変わってくる。","サイズの違いは実車で。","価格と装備は在庫で比較。"],
 ["まだUXかNXか迷うなら、","中古車も候補に入れよう。","年式・装備・支払総額を","見比べて選ぼう。"]]),
3606:("lexus-ux-vs-lbx","a438687b1dcae406b4e570a713d9c811a2d1a57ef0832a1f8a6f10273e19e9fc",[
 ["LBXの新車だけで決めず、","中古UX250hも比べよう。","どちらが自分に合うか、","装備と価格で確かめよう。"],
 ["小さなLBXと中古UX。","候補を広げて探してみよう。","支払総額・走行距離・装備を","まとめて確認しよう。"]]),
3608:("lexus-lbx-regret","23dcd4f0651fb6988c473140b0e9f2f2d20e2ba53c0bd1197c91bf64add3a701",[
 ["新車LBXがしっくり来ないなら、","中古UXも見てみよう。","不満だった点が解消できるか、","装備と実車でチェック。"]]),
3611:("lexus-lbx-options","0817a9d0dc3e4c4491cf8616b4c0bb86db10ba35e1ecf50704b594873c8f94b8",[
 ["欲しい装備はあと付けできない。","条件の合う中古LBXを探そう。","HUD・駐車支援などは、","個体ごとの装備を確認。"],
 ["オプションを選び終えたら、","中古LBXの在庫も見てみよう。","新車の見積もりと","支払総額を比べよう。"]]),
3835:("goodbuy","3a285cc35cc0009a69141a1aada55de059794de9b2cfd7ed27c939330f6e8e77",[
 ["安く買うなら中古も候補。","レクサスの在庫を探そう。","支払総額と保証を比べて、","納得できる1台を選ぼう。"]]),
3863:("lexus-lbx-cheap","54b84a8bd22a2e545c9f1dd52680d65b44aff530dfc22c68297f717423e5aa60",[
 ["装備を諦める前に、","中古LBXも確認してみよう。","欲しいメーカーオプションは","現車の装備表でチェック。"]]),
3965:("tanto-6years-review","6674d828a359dee2996072cacfef660608b3f7e76e764972252091cae68d04fc",[
 ["NAかターボか迷ったら、","中古タントを並べて比較。","年式・走行距離をそろえて、","価格差と装備を見てみよう。"]]),
4004:("tanto-model-history","55cc74c22f38e046b2018c6db2acfaba3a8abf204a6ce162f8f9d5d564d70307",[
 ["欲しいタントの型が決まったら、","次は実際の車両を探そう。","型式・年式・走行距離まで","絞って比べてみよう。"]]),
}
PRESERVE={3945:"lexus-lbx-used",3973:"tanto-used-best-year"}

def sha(s):return hashlib.sha256(s.encode("utf-8")).hexdigest()
def html_copy(phrases,kind):
    if len(phrases)!=2 or any(not x or len(x)>24 or "<" in x or "\n" in x for x in phrases):
        raise ValueError("bad copy length")
    css={
     "top":"text-align:center;margin:1.05em auto .35em;line-height:1.55;font-size:clamp(13px,3.6vw,15px);font-weight:700;color:#253c58;",
     "bottom":"text-align:center;margin:.28em auto 1.15em;line-height:1.5;font-size:clamp(12px,3.2vw,13px);color:#576777;",
    }[kind]
    spans="<wbr>".join('<span style="display:inline-block;white-space:nowrap;">'+html.escape(s)+'</span>' for s in phrases)
    return '<!-- wp:html -->\n<div class="'+PREFIX+' '+kind+'" style="'+css+'">'+spans+'</div>\n<!-- /wp:html -->'

def locate(s):
    found=[]
    if s.count(SHORTCODE)>1: raise RuntimeError("unexpected repeated Gulliver blog parts")
    for m in re.finditer(re.escape(SHORTCODE),s):
        found.append((m.start(),m.end(),"part",m.group(0)))
    for m in BLOCK_REGEX.finditer(s):
        if MARKER_REGEX.search(m.group(0)):
            found.append((m.start(),m.end(),"direct",m.group(0)))
    found.sort(key=lambda x:x[0])
    for i,a in enumerate(found):
        if i and found[i-1][1]>a[0]:raise RuntimeError("overlapping ad blocks")
    return found

def undo(s,copies):
    # Verify exact known wrappers before accepting a repeated run.
    for a in copies:
        before=html_copy(a[:2],"top")+"\n\n"
        after="\n\n"+html_copy(a[2:],"bottom")
        if s.count(before)!=1 or s.count(after)!=1:
            raise RuntimeError("existing wrapper does not match expected text")
        s=s.replace(before,"",1).replace(after,"",1)
    if PREFIX in s:raise RuntimeError("unrecognized CTA wrapper remains")
    return s

def source_base(s):
    if CTN_PREFIX in s:
        if s.count("tsq-ctn-last-20261014")!=2:
            raise RuntimeError("unexpected CTN tail structure")
        s=s.split(CTN_PREFIX,1)[0]
    return s.rstrip("\n")

def transform(s,cfg):
    slug,baseline,copies=cfg
    already=PREFIX in s
    basic=undo(s,copies) if already else s
    if sha(source_base(basic))!=baseline:raise RuntimeError(slug+": current live body differs from Oct14 editorial baseline")
    adblocks=locate(basic)
    if len(adblocks)!=len(copies):raise RuntimeError(slug+": expected "+str(len(copies))+" Gulliver anchors, found "+str(len(adblocks)))
    for marker in ("[blog_parts id=\"3788\"]","tsq-ctn-last-20261014"):
        if marker not in basic and slug!="tanto-model-history":
            raise RuntimeError(slug+": previous CTN end CTA missing")
    if already:
        if len(locate(s))!=len(copies) or s.count(PREFIX)!=2*len(copies):
            raise RuntimeError(slug+": existing wrap count mismatch")
        return s,True,len(adblocks)
    new=basic
    for (start,end,kind,block),a in reversed(list(zip(adblocks,copies))):
        top=html_copy(a[:2],"top")
        bottom=html_copy(a[2:],"bottom")
        new=new[:start]+top+"\n\n"+block+"\n\n"+bottom+new[end:]
    # True preservation: the full pre-existing body must be perfectly recoverable.
    if undo(new,copies)!=s:raise RuntimeError(slug+": existing article content changed")
    if len(locate(new))!=len(copies):raise RuntimeError(slug+": Gulliver anchor lost")
    if new.count("<!-- wp:")-s.count("<!-- wp:")!=2*len(copies):raise RuntimeError(slug+": Gutenberg block delta mismatch")
    if new.count("<!-- /wp:")-s.count("<!-- /wp:")!=2*len(copies):raise RuntimeError(slug+": Gutenberg close delta mismatch")
    return new,False,len(adblocks)

def http(path,auth,payload=None):
    h={"Authorization":auth,"Accept":"application/json","User-Agent":"tsurikue-gulliver-cta/20261014"}
    if payload is not None:h["Content-Type"]="application/json; charset=utf-8"
    r=urllib.request.Request(SITE+path,headers=h,method="POST" if payload is not None else "GET",
        data=json.dumps(payload,ensure_ascii=False).encode("utf-8") if payload is not None else None)
    with urllib.request.urlopen(r,timeout=65) as f: return json.load(f),dict(f.headers)
def get(pid,auth):return http(f"/wp-json/wp/v2/posts/{pid}?{QUERY}",auth)[0]
def raw(r):return r["content"]["raw"]
def count(auth):
    _,h=http("/wp-json/wp/v2/posts?status=publish&per_page=1&_fields=id",auth)
    return int(h["X-WP-Total"])
def prepare(auth):
    count_before=count(auth)
    plan=[]
    for pid,cfg in SPECS.items():
        row=get(pid,auth)
        if (row["id"],row["slug"],row["status"])!=(pid,cfg[0],"publish"):
            raise RuntimeError(cfg[0]+": identity or publish status changed")
        target,done,n=transform(raw(row),cfg)
        plan.append((pid,cfg,row,target,done,n))
        print("PREFLIGHT",pid,cfg[0],"anchor_count",n,"already",done,"current_sha",sha(raw(row)),flush=True)
    for pid,slug in PRESERVE.items():
        row=get(pid,auth)
        if (row["id"],row["slug"],row["status"])!=(pid,slug,"publish"):raise RuntimeError(slug+": protected post changed")
        if '[blog_parts id="2843"]' not in raw(row) or "tsq-cta-microcopy" not in raw(row):
            raise RuntimeError(slug+": earlier Gulliver CTA wrapper missing")
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"preflight.json").write_text(json.dumps({
        "published_count":count_before,"target_post_count":len(plan),"cta_placement_count":sum(x[5] for x in plan),
        "preserved_post_ids":list(PRESERVE),
        "posts":[{"id":pid,"slug":cfg[0],"current_sha":sha(raw(row)),
                  "proposed_sha":sha(target),"already_wrapped":done,"ads":n} for pid,cfg,row,target,done,n in plan]
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("PREFLIGHT_OK",len(plan),"posts",sum(x[5] for x in plan),"placements; published",count_before,flush=True)
    return plan,count_before

def run(mode):
    user=os.getenv("TSURIKUE_WP_USER");passwd=os.getenv("TSURIKUE_WP_APP_PASSWORD")
    if not user or not passwd:raise RuntimeError("WordPress auth secrets not available")
    auth="Basic "+base64.b64encode((user+":"+passwd).encode()).decode()
    plan,before_count=prepare(auth)
    if mode=="check":return
    updated=[]
    try:
        for pid,cfg,before,new,done,n in plan:
            live=get(pid,auth)
            if sha(raw(live))!=sha(raw(before)) or live["status"]!="publish":
                raise RuntimeError(cfg[0]+": concurrent edit before writing")
            if not done:
                http(f"/wp-json/wp/v2/posts/{pid}",auth,{"content":new})
                updated.append((pid,cfg,before,new))
            after=get(pid,auth)
            if any(after[k]!=before[k] for k in PROTECTED):raise RuntimeError(cfg[0]+": protected field modified")
            if raw(after)!=new:raise RuntimeError(cfg[0]+": published raw HTML mismatched")
            rendered=after["content"].get("rendered","")
            for a in cfg[2]:
                if not all(piece in rendered for piece in (a[0],a[2])):raise RuntimeError(cfg[0]+": copy absent from rendered page")
            if "[blog_parts id=\"2843\"]" in new and "ガリバー" not in rendered and "Gulliver" not in rendered:
                raise RuntimeError(cfg[0]+": Gulliver shortcode not rendered")
            print("LIVE_VERIFIED",pid,cfg[0],n,flush=True)
        if count(auth)!=before_count:raise RuntimeError("published post count changed")
        (OUT/"result.json").write_text(json.dumps({
           "result":"SUCCESS","updated_post_ids":[x[0] for x in updated],
           "verified":len(plan),"placements":sum(x[5] for x in plan),
           "preserved_post_ids":list(PRESERVE),"published_count":before_count
        },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    except Exception:
        for pid,cfg,before,new in reversed(updated):
            try:
                latest=get(pid,auth)
                if sha(raw(latest))==sha(new):
                    http(f"/wp-json/wp/v2/posts/{pid}",auth,{"content":raw(before)})
                    print("ROLLBACK",pid,cfg[0],flush=True)
            except Exception as err:print("ROLLBACK_FAILED",pid,cfg[0],repr(err),flush=True)
        raise
if __name__=="__main__":
    mode=sys.argv[1] if len(sys.argv)>1 else "check"
    if mode not in ("check","apply"):raise SystemExit("Expected check or apply")
    run(mode)
