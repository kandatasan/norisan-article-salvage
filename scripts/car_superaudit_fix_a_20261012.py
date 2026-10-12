#!/usr/bin/env python3
"""Editorial pass A: exact-source CTA de-duplication and WordPress block repair.
Branch PR runs GET-only; main updates ONLY if all source SHA checks pass.
"""
from __future__ import annotations
import base64, hashlib, json, os, re, sys, urllib.parse, urllib.request, time
from pathlib import Path
from html.parser import HTMLParser

BASE=[[2222,"ux-resale","f9df0ace29272f94988e17f505d9ee6dda6e40f59a1af47bfd0856ecf9a1f570"],[2240,"ux-mitsumori","e2e61f20022356088ee94a83d79afdc90c5f23d019ddfb35ae0aa08a0c8762a4"],[2329,"ux300h","f70ee2826061ac151f316389cfc9a35efab49e3671b971e569fcb76a94b252ab"],[2517,"ux-koukai","60dfdee41d23b9350d785f2b899397289bf5924cbb9ce0dea1ab7a42386934fe"],[2956,"lexus-ux-price","5a3cfb39cc5f5c64d4316793733b2b2e5371934f6b09c9bb2b15fd1d9cc26a0e"],[3570,"lexus-ux-emotional-explorer","a141fd983dd41bfe0e8605ed65b20b402c7522ea674b217e66ff6dd71173676c"],[3601,"lexus-ux250h-used-vs-ux300h","2c45e1893ad85d13898f7deca135c90ecaeffd6c818aaa2140d2fd1c7b41688f"],[3604,"lexus-ux-vs-nx","0e56387b153357b61da5d3062ed53cf0e023afe6fbbd8c6b47c8adebb6e39810"],[3606,"lexus-ux-vs-lbx","45bd6a170db2eda3b6870b64b91824ba7af8fc362ffb5a3bc9ba66ea3cf1b41f"],[3608,"lexus-lbx-regret","50019899128e2dacc523575357b113177e93ef6106133c0bfabee40ba303aff9"],[3611,"lexus-lbx-options","a1e0a70c8d243f64ff8aa56922d332cd32fccafed5f9c2eec7c9b0be8d5ca0a0"],[3614,"car-sell-high","1c20c9618514389d0c6e7c5462a70390aed8bab87ceda40350939b99f13ac8d2"],[3835,"goodbuy","00a45e47781a110d1c5eb992f50f68a5b10403ec561a41d5dc9bb47a493bde2b"],[4004,"tanto-model-history","55cc74c22f38e046b2018c6db2acfaba3a8abf204a6ce162f8f9d5d564d70307"]]
BASE={int(row[0]):(row[1],row[2]) for row in BASE}
SITE="https://tsurikue.com"
OUT=Path("reports/car-superaudit-20261012-a")
CTN_INLINE=re.compile(r'<br>(?:今の車の)?査定額を見ておくなら、<a href="https://px\.a8\.net/svt/ejp\?a8mat=3Z8YF4[^"]*" rel="nofollow">【CTN一括車査定】</a><img border="0" width="1" height="1" src="https://www19\.a8\.net/0\.gif\?a8mat=3Z8YF4[^"]*" alt="">')
DOUBLE={2240,2956,3570,3601,3604,3606,3608,3611}
WP_DIRECT_GULLIVER=re.compile(r'<!-- wp:paragraph -->\s*<p><a href="https://px\.a8\.net/svt/ejp\?a8mat=4B65SD[^"]+" rel="nofollow">[^<]+</a><img border="0" width="1" height="1" src="https://www15\.a8\.net/0\.gif\?a8mat=4B65SD[^"]+" alt=""></p>\s*<!-- /wp:paragraph -->',re.S)
CTN_FOOTER=re.compile(r'<!-- wp:shortcode -->\s*\[blog_parts id="2184"\]\s*<!-- /wp:shortcode -->',re.S)
PARA=re.compile(r'<!-- wp:paragraph(?: \{[^\n]+\})? -->\s*<p[^>]*>.*?</p>\s*<!-- /wp:paragraph -->',re.S)
def sha(s):return hashlib.sha256(s.encode("utf-8")).hexdigest()
def one(s,old,new,slug):
    if s.count(old)!=1:raise RuntimeError(f"{slug}: expected one exact anchor, got {s.count(old)}: {old[:55]}")
    return s.replace(old,new,1)
def delete_para_containing(s,text,slug):
    matches=[m for m in PARA.finditer(s) if text in m.group()]
    if len(matches)!=1:raise RuntimeError(f"{slug}: paragraph '{text[:35]}' count={len(matches)}")
    m=matches[0]
    return s[:m.start()]+s[m.end():]
def remove_ctn_inline(s,slug):
    if len(CTN_INLINE.findall(s))!=1:raise RuntimeError(f"{slug}: CTN A8 inline pair mismatch {len(CTN_INLINE.findall(s))}")
    return CTN_INLINE.sub("",s,count=1)
def transform(s,pid,slug):
    original=s
    if pid in DOUBLE:s=remove_ctn_inline(s,slug)
    if pid==3570:
        s=one(s,"台数が限られる特別仕様車なら、そのくらいから始めてもいいと思います。\n<!-- tsurikue-ctn-emotional-explorer-funnel:20260907 -->",
          "台数が限られる特別仕様車なら、そのくらいから始めてもいいと思います。</p>\n<!-- /wp:paragraph -->\n<!-- tsurikue-ctn-emotional-explorer-funnel:20260907 -->",slug)
        s=one(s,'<!-- /wp:shortcode --></p>\n<!-- /wp:paragraph -->','<!-- /wp:shortcode -->',slug)
        m=list(WP_DIRECT_GULLIVER.finditer(s))
        if len(m)!=1:raise RuntimeError(f"{slug}: expected single introductory Gulliver direct block")
        s=s[:m[0].start()]+s[m[0].end():]
    if pid==2956:
        s=one(s,"<!-- /wp:post-content -->\n","",slug)
    if pid==2329:
        s=delete_para_containing(s,"<!-- tsurikue-ctn-ux300h-funnel:20260907 -->",slug)
        s=delete_para_containing(s,"売るかどうかは、金額を見てから決めればOK。",slug)
        if len(CTN_FOOTER.findall(s))!=1:raise RuntimeError(f"{slug}: expected CTN button")
        s=CTN_FOOTER.sub("",s,count=1)
        # The article is a driving comparison, not a car-sale landing page. Keep one used-car CTA at the conclusion.
        m=list(WP_DIRECT_GULLIVER.finditer(s))
        if len(m)!=1:raise RuntimeError(f"{slug}: expected one mid-article Gulliver direct block")
        s=s[:m[0].start()]+s[m[0].end():]
        s=delete_para_containing(s,"中古UXを実車ベースで見比べてみる。",slug)
    if pid==3835:
        s=one(s,"補償内容をそろえて比べて、納得できる保険料を探す。<br>私の例と同じ月5,000円差なら、年間6万円、5年で30万円です。",
          "補償内容をそろえて比べて、納得できる保険料を探す。",slug)
    if pid==4004:
        start='<!-- wp:heading {"level":3} -->\n<h3 class="wp-block-heading">買い替えなら、今の車の値段も先に見ておく</h3>'
        if s.count(start)!=1:raise RuntimeError(f"{slug}: missing CTN-only closing H3")
        pos=s.index(start)
        body=s[pos:]
        if body.count('[blog_parts id="2184"]')!=1:raise RuntimeError(f"{slug}: closing CTN shortcode mismatch")
        # Only a blank paragraph may follow this section.
        if "<!-- wp:paragraph -->\n<p></p>\n<!-- /wp:paragraph -->" not in body:
            raise RuntimeError(f"{slug}: unexpected content at article end")
        s=s[:pos].rstrip()+"\n"
    if pid==2222:
        s=one(s,"CTNなら、やり取りする買取店は最大3社。電話対応の負担を抑えて比べられます。",
          "査定先で金額が変われば、次の車に使える予算も変わります。",slug)
        s=one(s,"「今の車がいくらになる？」を見ておくなら、","今の車の査定額を比べてみたいなら、",slug)
        s=one(s,"査定額に納得してから、売るか決めればOK。",
          "申し込みには連絡先・車両情報の入力が必要で、金額は買取店との連絡や実車確認を経て決まります。<br>売るかどうかは、査定額に納得してから。",slug)
    if pid==3614:
        s=one(s,"納得できる金額なら、そのとき売却を考える。",
          "連絡先と車両情報の入力が必要で、買取店とのやり取りや実車査定もあります。<br>金額に納得してから、売るかどうか決めればOK。",slug)
    if pid==3601:
        s=one(s,"その先のローンや保険も含めて考えるなら、<br><a href=\"https://tsurikue.com/goodbuy/\">レクサスを安く買う方法5選</a>では、その先のローン・保険・オプションまでまとめています。",
          "ローンや保険まで含めて購入負担を比べるなら、<a href=\"https://tsurikue.com/goodbuy/\">レクサスを安く買う方法5選</a>へ。",slug)
    if pid==3604:
        s=delete_para_containing(s,"UXにするかNXにするか。その前に「今の車、いくらになる？」を見ておく。",slug)
    if pid==2517:
        # The second telling of the 350/500 curiosity appraisal follows an already complete first-hand account.
        s=delete_para_containing(s,"ちなみに、このとき私がUXを査定に出したきっかけは、",slug)
        s=delete_para_containing(s,"その好奇心で試してみたら、ディーラー350万円に対して一括査定では最高500万円近い提示。",slug)
        s=delete_para_containing(s,"私みたいに「売る気はないけど、愛車の値段はちょっと気になる」",slug)
        m=list(WP_DIRECT_GULLIVER.finditer(s))
        if len(m)!=1:raise RuntimeError(f"{slug}: first Gulliver direct CTA block count {len(m)}")
        s=s[:m[0].start()]+s[m[0].end():]
    if s==original:raise RuntimeError(f"{slug}: no change")
    # No alteration of remaining affiliate issuance code, headlines, pictures or internal-link targets.
    for patt in (r'<h[123]\b[^>]*>.*?</h[123]>',r'<img\b[^>]*src="https?://tsurikue\.com/wp-content/uploads/[^"]+"[^>]*>',r'wp-image-\d+'):
        a=re.findall(patt,original,re.S|re.I);b=re.findall(patt,s,re.S|re.I)
        if pid==4004 and patt.startswith('<h'): # exactly one CTN-only H3 is intentionally gone
            a=[x for x in a if "買い替えなら、今の車の値段も先に見ておく" not in x]
        if a!=b:raise RuntimeError(f"{slug}: protected headings/media altered")
    before=set(re.findall(r'https://px\.a8\.net/svt/ejp\?a8mat=[^"]+',original))
    after=set(re.findall(r'https://px\.a8\.net/svt/ejp\?a8mat=[^"]+',s))
    if not after.issubset(before):raise RuntimeError(f"{slug}: external affiliate URL added/modified")
    if s.count('<!-- wp:')-s.count('<!-- /wp:') not in (0,original.count('<!-- wp:')-original.count('<!-- /wp:')):
        raise RuntimeError(f"{slug}: Gutenberg unexpected imbalance")
    return s
def request(url,auth,content=None):
    headers={"Authorization":auth,"Accept":"application/json","User-Agent":"tsurikue-superaudit-fix-A/20261012"}
    if content is not None:headers["Content-Type"]="application/json; charset=utf-8"
    for retry in range(3):
        try:
            req=urllib.request.Request(SITE+url,headers=headers,method="POST" if content is not None else "GET",
               data=json.dumps(content,ensure_ascii=False).encode() if content is not None else None)
            with urllib.request.urlopen(req,timeout=40) as r:return json.loads(r.read().decode()),dict(r.headers)
        except Exception:
            if retry==2 or content is not None:raise
            time.sleep(2+retry)
def get(pid,auth):
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,content,featured_media,author,categories"})
    return request(f"/wp-json/wp/v2/posts/{pid}?{q}",auth)[0]
def main(mode):
    u=os.getenv("TSURIKUE_WP_USER");p=os.getenv("TSURIKUE_WP_APP_PASSWORD")
    if not u or not p:raise RuntimeError("Missing WP app credentials")
    auth="Basic "+base64.b64encode((u+":"+p).encode()).decode()
    prepared=[]
    for pid,(slug,expected) in BASE.items():
        row=get(pid,auth)
        if (row["id"],row["slug"],row["status"])!=(pid,slug,"publish"):
            raise RuntimeError(f"{slug}: identity/status mismatch")
        raw=row["content"]["raw"];actual=sha(raw)
        print("SOURCE_SHA",pid,slug,actual,flush=True)
        if actual!=expected:raise RuntimeError(f"{slug}: WordPress changed since 2026-10-12 export: stop, no writes")
        result=transform(raw,pid,slug)
        prepared.append((pid,slug,row,result))
        print("PREPARED",pid,slug,"original",len(raw),"updated",len(result),flush=True)
    print("PREFLIGHT_PASS",len(prepared),"articles",flush=True)
    if mode=="check":return
    done=[]
    try:
        for pid,slug,row,result in prepared:
            if sha(get(pid,auth)["content"]["raw"])!=sha(row["content"]["raw"]):
                raise RuntimeError(f"{slug}: concurrent edit")
            done.append((pid,slug,row,result))
            request(f"/wp-json/wp/v2/posts/{pid}",auth,{"content":result})
            v=get(pid,auth)
            for k in ("id","slug","status","title","featured_media","author","categories"):
                if v[k]!=row[k]:raise RuntimeError(f"{slug}: changed protected field {k}")
            if v["content"]["raw"]!=result:raise RuntimeError(f"{slug}: updated content differed")
            print("LIVE_VERIFIED",pid,slug,flush=True)
        for pid,slug,row,result in prepared:
            if get(pid,auth)["content"]["raw"]!=result:raise RuntimeError(f"{slug}: final content mismatch")
        print("FINAL_PASS",len(prepared),"published articles",flush=True)
    except Exception:
        for pid,slug,row,result in reversed(done):
            try:
                if sha(get(pid,auth)["content"]["raw"])==sha(result):
                    request(f"/wp-json/wp/v2/posts/{pid}",auth,{"content":row["content"]["raw"]})
                    print("ROLLED_BACK",pid,slug,flush=True)
            except Exception as e:print("ROLLBACK_FAILED",pid,slug,str(e),flush=True)
        raise
if __name__=="__main__":
    mode=sys.argv[1] if len(sys.argv)>1 else "check"
    if mode not in ("check","apply"):raise SystemExit("check|apply")
    main(mode)
