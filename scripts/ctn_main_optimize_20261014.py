#!/usr/bin/env python3
"""CTN primary CTA redesign: scoped copy-only 14-post changes, guarded against live drift.

CTN shortcode/button and other body content remain byte-identical.
New microcopy uses no-wrap short semantic phrases separated only at <wbr>.
Check on PR, apply only on main; save preflight and post-edit QA.
"""
from __future__ import annotations
import base64, hashlib, html, json, os, re, sys, urllib.parse, urllib.request
from pathlib import Path

SITE="https://tsurikue.com"
OUT=Path("reports/cta-ctn-main-20261014")
Q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,featured_media,categories,author,content"})
STAMP="tsq-ctn-primary-20261014"
PROTECTED=("id","slug","status","title","featured_media","categories","author")
PRESERVE={
2222:"ux-resale",3614:"car-sell-high",2329:"ux300h",2517:"ux-koukai",
3608:"lexus-lbx-regret",4004:"tanto-model-history",3945:"lexus-lbx-used",
3965:"tanto-6years-review",3973:"tanto-used-best-year",
3774:"landcruiser-fj-review",3777:"landcruiser-fj-rear-seat",3778:"landcruiser-fj-drawbacks"}
# (slug, SHA observed on Oct14 live WP via authenticated GET audit,
#  shortcode ID, current immediately preceding centered text,
#  [top microcopy two semantic phrases], [bottom two phrases]).
SPECS={
2240:("ux-mitsumori","5c8f5f1ca6bf93bec62b91d73dc011541fdb47d0a265b93740977526387590c1",2184,"売るかどうかは、査定額を見てから。",
      ["見積もり616万円。","今の車はいくらになる？"],["下取り額と比べて、","予算を考えてみよう。"]),
2948:("lexus-ux-used","d8c22be2863e6ed9b754166a49062d37fffd6f0d65550a9c9e87875897d068d2",2184,"やり取りは最大3社。電話の負担を抑えて比較。",
      ["私のシエンタは25万円差。","あなたの車はどうだろう？"],["査定額と下取り額を比べて、","納得できる方を選ぼう。"]),
2956:("lexus-ux-price","75be572867118cdb6235f7229392aa9f5474133fa0602ae4773248bdd4e7ecde",2184,"売却は、査定額を見てから決めればOK。",
      ["UXの価格が見えてきたら、","今の車も査定してみよう。"],["査定と下取りを比べて、","買い替え予算を考えよう。"]),
2962:("lexus-ux-discount","bdbb17a331afa670262e4a2da959da317bda27afce99159b16aac685c63f474d",2184,"売却を決めるのは、査定額を見てから。",
      ["値引き0円なら、","売却額も比べてみよう。"],["下取りだけで決めず、","査定額も確認してみよう。"]),
3570:("lexus-ux-emotional-explorer","121a0ba5b9397104ce3c9a3c932601f4dbb8b7394514ea28f2ffdfea6a634b2f",2184,"売るかどうかは、査定額に納得してから。",
      ["欲しい特別仕様車が見えたら、","乗り換え資金も確認。"],["下取り額と比べて、","納得できる金額を探そう。"]),
3601:("lexus-ux250h-used-vs-ux300h","0d99e9ee22a888a47f0b1e3dd7f667040bd14509002a82f0c51f42e69daefe56",2184,"売るかどうかは、査定額を見てから。",
      ["中古250hか新車300hか。","今の車の価値も確認。"],["今の車の査定額がわかれば、","比較する予算が見えてくる。"]),
3604:("lexus-ux-vs-nx","fed427a7f3e7a2304745afeb3633090a0dfac5f3e7662e3f7f3ce32f2ac71b8c",2184,"売るかどうかは、査定額を見てから。",
      ["UXとNXで迷ったら、","今の車の売値も確認。"],["査定額を見てから、","乗り換え予算を考えよう。"]),
3606:("lexus-ux-vs-lbx","73e7fd084d661878c22bb7e88f7f57d1c775bc3d96b3901cf7ce9e8e43c84417",2184,"やり取りする買取店は最大3社。",
      ["LBXかUXか決める前に、","今の車の査定額も比較。"],["下取り額と並べて、","購入予算を考えてみよう。"]),
3611:("lexus-lbx-options","7bdf2887204cd877b6c0cdfaf060ab19f2ddf9d18a78bc007f6f7387cd3ab5fc",2184,"売却は、査定額に納得してから決めればOK。",
      ["欲しいLBXのオプション。","売却額も判断材料に。"],["下取りとの差を確認して、","装備選びの参考にしよう。"]),
3835:("goodbuy","cd9ad3046683119ffece4e9d744279f48da82f48f3d606e5e0d49293a817630b",2184,"やり取りは最大3社。売るかどうかは金額を見てから。",
      ["値引きに頼らない買い方。","まず愛車の売値を知ろう。"],["買取査定と下取りを比べ、","次の予算を決めよう。"]),
3863:("lexus-lbx-cheap","f2dbd67b94274ffac7ee6f8b906dea4fe6cea2485fc118e245ee755e34af7b6a",2184,"売るかどうかは、査定額を見てから。",
      ["欲しい装備を諦める前に、","愛車の査定額も確認。"],["下取りだけで決めず、","使える予算を比べよう。"]),
3936:("lexus-lbx-price","cccc15f226acf06ed0cc8eb73a033175aebd9aa2eb81c56bf9c195205e1f0c17",2184,"最大3社とのやり取り。売却は納得してから。",
      ["LBXの見積もりを見たら、","今の車はいくらになる？"],["下取りと買取を比較して、","総予算の参考にしよう。"]),
3767:("landcruiser-fj-price","b115d696d051a8c3e06ba2a4f1ece093c33a2bab6326d79a3643e7bbf2681220",3788,"CTNはやり取りする買取店が最大3社。売却は金額を見てから。",
      ["乗り出し約550万円。","今の車は何万円になる？"],["査定額と下取りを比べて、","購入予算を組み立てよう。"]),
3816:("landcruiser-fj-cheap","c3dcc2158edfe030299b0001f4c3d578c9e8b98d8b030cac2d83901962257c70",3788,"買取店とのやり取りは最大3社。売却は納得してから。",
      ["FJの装備を削る前に、","今の車の売値を確認。"],["買取査定と下取りを比べ、","予算の判断材料にしよう。"]),
}
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
def copy_block(phrases,kind):
    if len(phrases)!=2 or any(not phrase or len(phrase)>16 or "<" in phrase or "\n" in phrase for phrase in phrases):
        raise RuntimeError("copy lines must be 1-16 chars with two safe semantic clauses")
    css = ("max-width:100%;text-align:center;font-size:clamp(13px,3.5vw,15px);font-weight:700;"
           "line-height:1.55;color:#29466e;margin:1.05em auto .32em;") if kind=="top" else (
           "max-width:100%;text-align:center;font-size:clamp(12px,3.2vw,13px);font-weight:400;"
           "line-height:1.5;color:#596b7a;margin:.3em auto 1.05em;")
    text="<wbr>".join('<span style="display:inline-block;white-space:nowrap;">'+html.escape(s)+'</span>' for s in phrases)
    return ('<!-- wp:html -->\n<div class="'+STAMP+' '+kind+'" style="'+css+'">'+text+'</div>\n<!-- /wp:html -->')
def paragraph(content):
    return ('<!-- wp:paragraph {"align":"center"} -->\n'
            '<p class="has-text-align-center"><strong>'+content+'</strong></p>\n'
            '<!-- /wp:paragraph -->')
def shortcode(id):
    return '<!-- wp:shortcode -->\n[blog_parts id="'+str(id)+'"]\n<!-- /wp:shortcode -->'
def transform(old,row):
    slug,hash_expected,part,oldcopy,top,bottom=row
    if sha(old)!=hash_expected: raise RuntimeError(slug+": changed since preflight inventory; refuse all edits")
    prev=paragraph(oldcopy);button=shortcode(part)
    if old.count(prev)!=1 or old.count(button)!=1:raise RuntimeError(slug+": original CTN anchor/previous paragraph mismatch")
    match=re.search(re.escape(prev)+r'\s*'+re.escape(button),old)
    if not match:raise RuntimeError(slug+": original copy not directly before its CTN shortcode")
    new=old[:match.start()]+copy_block(top,"top")+"\n\n"+button+"\n\n"+copy_block(bottom,"bottom")+old[match.end():]
    # Very strict: reconstruct exactly the full pre-existing article body.
    reverse=new.replace(copy_block(top,"top")+"\n\n"+button+"\n\n"+copy_block(bottom,"bottom"),old[match.start():match.end()],1)
    if reverse!=old:raise RuntimeError(slug+": replacement altered article outside the CTA")
    if new.count(button)!=old.count(button):raise RuntimeError(slug+": fixed CTN shortcode was altered")
    for kind in (2184,3788,2846,2843,4172):
        if new.count('[blog_parts id="'+str(kind)+'"]')!=old.count('[blog_parts id="'+str(kind)+'"]'):
            raise RuntimeError(slug+": blog part count changed unexpectedly")
    for pattern in (r'<img\b[^>]*>',r'wp-image-\d+',r'https://px\.a8\.net/svt/ejp\?a8mat=[^"\s<]+',
                    r'<h[123]\b[^>]*>.*?</h[123]>'):
        if re.findall(pattern,new,re.S|re.I)!=re.findall(pattern,old,re.S|re.I):
            raise RuntimeError(slug+": protected media/A8/heading changed")
    if new.count("<!-- wp:")-old.count("<!-- wp:")!=1 or new.count("<!-- /wp:")-old.count("<!-- /wp:")!=1:
        raise RuntimeError(slug+": unexpected Gutenberg block count")
    return new
def request(path,auth,payload=None):
    headers={"Authorization":auth,"Accept":"application/json","User-Agent":"tsurikue-ctn-main/20261014"}
    if payload is not None:headers["Content-Type"]="application/json; charset=utf-8"
    req=urllib.request.Request(SITE+path,headers=headers,method="POST" if payload is not None else "GET",
        data=json.dumps(payload,ensure_ascii=False).encode() if payload is not None else None)
    with urllib.request.urlopen(req,timeout=60) as r:return json.load(r),dict(r.headers)
def fetch(pid,auth):return request(f"/wp-json/wp/v2/posts/{pid}?{Q}",auth)[0]
def raw(row):return row["content"]["raw"]
def public_count(auth):
    _,h=request("/wp-json/wp/v2/posts?status=publish&per_page=1&_fields=id",auth)
    return int(h["X-WP-Total"])
def execute(mode):
    user=os.getenv("TSURIKUE_WP_USER");passwd=os.getenv("TSURIKUE_WP_APP_PASSWORD")
    if not user or not passwd:raise RuntimeError("No WordPress secrets; no writes")
    auth="Basic "+base64.b64encode((user+":"+passwd).encode()).decode()
    total=public_count(auth);prepared=[]
    for pid,cfg in SPECS.items():
        row=fetch(pid,auth)
        if (row["id"],row["slug"],row["status"])!=(pid,cfg[0],"publish"):
            raise RuntimeError(cfg[0]+": ID/slug/status mismatch")
        next_body=transform(raw(row),cfg)
        prepared.append((pid,cfg,row,next_body))
    for pid,slug in PRESERVE.items():
        row=fetch(pid,auth)
        if (row["id"],row["slug"],row["status"])!=(pid,slug,"publish"):
            raise RuntimeError(slug+": preserve-only identity/status mismatch")
        if pid in (2222,3614) and raw(row).count("tsq-cta-microcopy")!=4:
            raise RuntimeError(slug+": previously verified two CTA wraps changed")
        if pid in (3774,3777,3778) and any('[blog_parts id="'+x+'"]' in raw(row) for x in ("2184","3788","2846")):
            raise RuntimeError(slug+": intentionally ad-free FJ experience article regained CTN")
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"preflight.json").write_text(json.dumps({
        "status":"READY","target_post_count":len(prepared),
        "preserved_posts":list(PRESERVE),"published_total_before":total,
        "targets":[{"post_id":pid,"slug":cfg[0],"before_sha":sha(raw(row)),"after_sha":sha(new)}
                   for pid,cfg,row,new in prepared]},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("CTN_PREFLIGHT_OK",len(prepared),"primary CTNs; preserve",len(PRESERVE),"public",total,flush=True)
    if mode=="check":return
    done=[]
    try:
        for pid,cfg,before,modified in prepared:
            latest=fetch(pid,auth)
            if sha(raw(latest))!=sha(raw(before)) or latest["status"]!="publish":
                raise RuntimeError(cfg[0]+": concurrent edit; STOP")
            request(f"/wp-json/wp/v2/posts/{pid}",auth,{"content":modified})
            done.append((pid,cfg,before,modified))
            after=fetch(pid,auth)
            if any(after.get(k)!=before.get(k) for k in PROTECTED):
                raise RuntimeError(cfg[0]+": protected post metadata changed")
            if raw(after)!=modified:raise RuntimeError(cfg[0]+": saved content different")
            rendered=after["content"].get("rendered","")
            if cfg[4][0] not in rendered or cfg[5][0] not in rendered:
                raise RuntimeError(cfg[0]+": live rendered microcopy missing")
            if STAMP not in rendered:raise RuntimeError(cfg[0]+": live CTA wrapper missing")
            print("CTN_LIVE_VERIFIED",pid,cfg[0],flush=True)
        if public_count(auth)!=total:raise RuntimeError("published post count changed")
        (OUT/"result.json").write_text(json.dumps({
            "result":"SUCCESS","verified":len(done),"preserved":len(PRESERVE),
            "published_total":total,"updated_post_ids":[x[0] for x in done]
        },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    except Exception:
        for pid,cfg,before,modified in reversed(done):
            try:
                latest=fetch(pid,auth)
                if sha(raw(latest))==sha(modified):
                    request(f"/wp-json/wp/v2/posts/{pid}",auth,{"content":raw(before)})
                    print("CTN_ROLLBACK",pid,cfg[0],flush=True)
            except Exception as e:print("CTN_ROLLBACK_FAILED",pid,cfg[0],str(e),flush=True)
        raise
if __name__=="__main__":
    mode=sys.argv[1] if len(sys.argv)>1 else "check"
    if mode not in ("check","apply"):raise SystemExit("Expected check or apply")
    execute(mode)
