#!/usr/bin/env python3
from __future__ import annotations
import argparse,base64,hashlib,html,json,os,time,urllib.parse,urllib.request
from pathlib import Path

SITE="https://tsurikue.com"; POST_ID=2962; SLUG="lexus-ux-discount"; STATUS="publish"
TITLE="レクサスUXは値引きできる？値引き0円だった実体験と安く買う方法"
FEATURED_MEDIA=2231
EXPECTED_CURRENT_SHA256="0cdb6bf564d4c9def3b98c1979e7b1bd0c01e0b57c2f304efffb621052034e23"
EXPECTED_TARGET_SHA256=""
UA="tsurikue-lexus-ux-discount-revenue-20260916/1.0"
REPORT=Path("reports/lexus-ux-discount-revenue-20260916")

REPLACEMENTS=[
("intro-teaser",
"""<!-- wp:paragraph -->
<p>つまり、見積書の値引き欄は0円でも、<strong>買い替え全体では25万円動かせた</strong>ということです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>「レクサスUXは値引きできる？」「値引きが難しいなら、どうやって負担を減らせばいい？」という人向けに、この記事では私自身の値引き0円だった実体験と、値引き以外で購入負担を減らした方法を整理します。</p>
<!-- /wp:paragraph -->""",
"""<!-- wp:paragraph -->
<p>つまり、見積書の値引き欄は0円でも、<strong>買い替え全体では25万円動かせた</strong>ということです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>しかも、その後UX自体を査定したときは、査定先の違いで<strong>約150万円差</strong>も出ました。<br>値引き0円より、私はこっちの方が衝撃でした。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>「レクサスUXは値引きできる？」「値引きが難しいなら、どうやって負担を減らせばいい？」という人向けに、この記事では私自身の値引き0円だった実体験と、値引き以外で購入負担を減らした方法を整理します。</p>
<!-- /wp:paragraph -->"""),

("benefit-heading",
"""<!-- wp:heading -->
<h2 class="wp-block-heading">値引き以外で購入総額を下げる方法</h2>
<!-- /wp:heading -->""",
"""<!-- wp:heading -->
<h2 class="wp-block-heading">値引き0円でも、買い替え総額はまだ動かせる</h2>
<!-- /wp:heading -->"""),

("experience-table",
"""<!-- wp:list {"className":"wp-block-list"} -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>使わないオプションを付けない</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>グレードや2WD・AWDを使い方に合わせて選ぶ</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>今乗っている車の売却価格を比較する</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>新車だけでなく中古車・認定中古車まで広げる</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->""",
"""<!-- wp:list {"className":"wp-block-list"} -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>使わないオプションを付けない</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>グレードや2WD・AWDを使い方に合わせて選ぶ</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>今乗っている車の売却価格を比較する</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>新車だけでなく中古車・認定中古車まで広げる</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->

<!-- wp:paragraph -->
<p>実際、私の買い替えでは<strong>値引きより売却側の方が金額が動きました。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:table {"hasFixedLayout":false} -->
<figure class="wp-block-table"><table><thead><tr><th>私の実例</th><th>金額</th><th>結果</th></tr></thead><tbody><tr><td>UX新車の値引き</td><td>0円</td><td>見積書どおり</td></tr><tr><td>シエンタの売却</td><td>50万円 → 75万円</td><td><strong>25万円差</strong></td></tr><tr><td>納車約3か月のUX査定</td><td>350万円 → 500万円前後</td><td><strong>約150万円差</strong><br>売却はせず</td></tr></tbody></table></figure>
<!-- /wp:table -->"""),

("sale-proof-and-ctn",
"""<!-- wp:paragraph -->
<p>その後、UX自体を手放したときにはCTN車一括査定を利用しました。<br>現在のCTNは最大15社で査定し、やり取りするのは高額査定の上位3社だけ。利用料・手数料も無料です。<br><strong>私のときに連絡が来たのはカーセブンとネクステージの2社で、電話が少なくて快適でした。</strong><br>最終的にはカーセブンへ427万円で売却しています。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>査定額は車種・年式・走行距離・状態・装備・時期で変わるので、誰でも25万円高くなるわけではありません。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>それでも、<strong>ディーラーの下取りだけで決めず、今の車の相場を確認しておく</strong>ことはできます。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>値引きが動かないなら、売却側を比べる。<br>そこで10万円、20万円と差が出れば、欲しかった装備を削らずに済むかもしれません。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>値引き額を見て落ち込む前に、「今の車はいくらになる？」を見ておく。</strong><br>私はこっちの方が買い替え予算を考えやすかったです。</p>
<!-- /wp:paragraph -->

<!-- tsurikue-ctn-discount-microcopy:20260916-benefit -->
<!-- wp:paragraph -->
<p><strong>欲しい装備を削る前に、今の車の価値を確認する。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>査定額を見ておくなら、<a href="https://px.a8.net/svt/ejp?a8mat=3Z8YF4+7VEGL6+5I4S+5YRHE" rel="nofollow">【CTN一括車査定】</a><img border="0" width="1" height="1" src="https://www19.a8.net/0.gif?a8mat=3Z8YF4+7VEGL6+5I4S+5YRHE" alt=""></p>
<!-- /wp:paragraph -->



<!-- wp:paragraph -->
<p>UXを427万円で実際に売却するまでの査定記録は、<a href="https://tsurikue.com/ux-resale/">レクサスUXの売却価格を公開した記事</a>に残しています。</p>
<!-- /wp:paragraph -->""",
"""<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">その後、同じUXの査定で約150万円差が出た</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>UXを納車して約3か月、走行距離が約5,000kmのころ。<br>売るつもりはなく、<strong>「今いくらなんだろう？」という好奇心</strong>で査定してみました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>レクサスディーラーの実車査定は350万円。<br>当時使った別の一括査定サービスでは500万円前後。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>ほぼ同じ時期、同じUXで約150万円差です。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>この約150万円差はCTNで出た数字ではありません。<br>当時利用した別の一括査定サービスでの提示額で、このときはUXを売却していません。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>もちろん、どの車でも150万円差が出るわけではありません。<br>ただ、比較しなければ<strong>自分の車に価格差があること自体に気づけない</strong>のも事実でした。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>値引き数万円を気にする一方で、査定を1社だけで決める。私は150万円差を見てから、そっちの方がちょっと怖くなりました。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>その後、2025年2月にUXを実際に手放したときはCTN車一括査定を利用しました。<br>CTNは、提携する買取店の中から高額査定の上位3社までを紹介する仕組みです。<br><strong>私のときに連絡が来たのはカーセブンとネクステージの2社で、電話が少なくて快適でした。</strong><br>最終的にはカーセブンへ427万円で売却しています。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>査定額は車種・年式・走行距離・状態・装備・時期で変わります。<br>高く売れる保証はありません。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>それでも、<strong>ディーラーの下取りだけで決めず、今の車の相場を確認してから決める</strong>ことはできます。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>値引きが動かないなら、売却側を比べる。<br>そこで10万円、20万円と差が出れば、欲しかった装備を削らずに済むかもしれません。</p>
<!-- /wp:paragraph -->

<!-- tsurikue-ctn-discount-microcopy:20260916-totalcost -->
<!-- wp:paragraph -->
<p><strong>値引き交渉の前に、今の車の価値を1社だけで決めない。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:shortcode -->
[blog_parts id="2184"]
<!-- /wp:shortcode -->

<!-- wp:paragraph -->
<p>UXを427万円で実際に売却するまでの査定記録は、<a href="https://tsurikue.com/ux-resale/">レクサスUXの売却価格を公開した記事</a>に残しています。</p>
<!-- /wp:paragraph -->"""),

("summary",
"""<!-- wp:heading -->
<h2 class="wp-block-heading">まとめ｜値引き0円でも、買い替え全体なら動かせる</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>私のUXは値引き0円でした。<br>友人の購入例でも値引きはありませんでした。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>一方で、シエンタはディーラー下取り50万円から75万円になり、<strong>売却先の違いで25万円差が出ました。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>だから私は、値引きだけに期待するより、<strong>不要なオプションを削る・今の車を高く売る・中古まで候補を広げる</strong>方が現実的だと思っています。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>せっかくレクサスを買うなら、値引き額だけを追って欲しかった装備まで削るのはもったいない。</strong><br>買い替え全体の予算を整えて、自分が乗りたいUXに近づける方がワクワクします。</p>
<!-- /wp:paragraph -->""",
"""<!-- wp:heading -->
<h2 class="wp-block-heading">まとめ｜値引き0円でも、買い替え全体なら動かせる</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>私のUX購入時の値引きは0円でした。<br>一方で、シエンタの売却では25万円差、その後のUX査定では約150万円差を経験しています。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>もちろん、誰でも同じ差が出るわけではありません。<br>でも私自身はこの経験から、<strong>値引き額だけではなく、買う金額と売る金額をセットで見る</strong>ようになりました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>だから、値引きだけに期待するより、<strong>不要なオプションを削る・今の車の売却額を比較する・中古まで候補を広げる</strong>方が現実的だと思っています。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>せっかくレクサスを買うなら、値引き0円を見て欲しかった装備まで削る前に、買い替え全体の金額を一度見直す。</strong><br>その方が、自分が本当に乗りたいUXに近づけます。</p>
<!-- /wp:paragraph -->"""),

("remove-footer-banners",
"""<!-- wp:shortcode -->
[blog_parts id="2843"]
<!-- /wp:shortcode -->

<!-- wp:shortcode -->
[blog_parts id="2846"]
<!-- /wp:shortcode -->""",
"""<!-- tsurikue-revenue-cta-dedup:20260916 -->""")
]

def sha(s): return hashlib.sha256((s or "").encode("utf-8")).hexdigest()
AUTH=None
def auth():
    global AUTH
    if AUTH is None:
        raw=f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()
        AUTH="Basic "+base64.b64encode(raw).decode()
    return AUTH
def req(method,path,payload=None):
    headers={"Authorization":auth(),"Accept":"application/json","User-Agent":UA}
    data=None
    if payload is not None:
        headers["Content-Type"]="application/json; charset=utf-8"; data=json.dumps(payload,ensure_ascii=False).encode()
    last=None
    for n in range(3):
        try:
            r=urllib.request.Request(SITE+path,data=data,headers=headers,method=method)
            with urllib.request.urlopen(r,timeout=90) as resp:
                body=resp.read().decode()
                return json.loads(body) if body else None
        except Exception as e:
            last=e
            if n<2: time.sleep(3*(n+1))
    raise last
def raw(row,key):
    v=row.get(key) or {}
    return (v.get("raw") or v.get("rendered") or "") if isinstance(v,dict) else str(v)
def raw_only(row,key):
    v=row.get(key) or {}
    return v.get("raw","") if isinstance(v,dict) else str(v)
def get_post():
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,content,author,featured_media,categories,excerpt"})
    return req("GET",f"/wp-json/wp/v2/posts/{POST_ID}?{q}")
def ident(row):
    return {"id":int(row.get("id") or 0),"slug":row.get("slug"),"status":row.get("status"),
      "title":html.unescape(raw(row,"title")),"author":int(row.get("author") or 0),
      "featured_media":int(row.get("featured_media") or 0),"categories":list(row.get("categories") or []),
      "excerpt_raw":raw_only(row,"excerpt")}
def validate_current(row):
    x=ident(row)
    if x["id"]!=POST_ID or x["slug"]!=SLUG or x["status"]!=STATUS or x["title"]!=TITLE or x["featured_media"]!=FEATURED_MEDIA:
        raise RuntimeError(f"identity changed: {x}")
    c=raw(row,"content"); got=sha(c)
    if got!=EXPECTED_CURRENT_SHA256: raise RuntimeError(f"content changed since discovery: {got}")
    return c
def build(current):
    out=current
    for label,old,new in REPLACEMENTS:
        n=out.count(old)
        if n!=1: raise RuntimeError(f"{label}: expected 1 match, got {n}")
        out=out.replace(old,new,1)
    required=[
      "約150万円差",
      "350万円 → 500万円前後",
      "値引き数万円を気にする一方で、査定を1社だけで決める。",
      "この約150万円差はCTNで出た数字ではありません。",
      "値引き交渉の前に、今の車の価値を1社だけで決めない。",
      '[blog_parts id="2184"]',
      "https://tsurikue.com/ux-resale/",
      "https://tsurikue.com/lexus-ux-price/",
      "https://tsurikue.com/lexus-ux-used/",
      "https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY",
      "tsurikue-revenue-cta-dedup:20260916",
    ]
    for m in required:
        if m not in out: raise RuntimeError(f"missing target marker: {m}")
    if '[blog_parts id="2843"]' in out or '[blog_parts id="2846"]' in out:
        raise RuntimeError("footer affiliate banners remain")
    if out.count('[blog_parts id="2184"]')!=1:
        raise RuntimeError("CTN button count unexpected")
    return out
def validate_saved(saved,target):
    required=[
      "約150万円差",
      "350万円 → 500万円前後",
      "この約150万円差はCTNで出た数字ではありません。",
      "値引き数万円を気にする一方で、査定を1社だけで決める。",
      "CTNは、提携する買取店の中から高額査定の上位3社までを紹介する仕組みです。",
      "値引き交渉の前に、今の車の価値を1社だけで決めない。",
      '[blog_parts id="2184"]',
      "https://tsurikue.com/ux-resale/",
      "https://tsurikue.com/lexus-ux-used/",
      "tsurikue-revenue-cta-dedup:20260916",
    ]
    missing=[m for m in required if m not in saved]
    if missing: raise RuntimeError("saved markers missing: "+repr(missing))
    forbidden=[
      "現在のCTNは最大15社で査定し",
      "tsurikue-ctn-discount-microcopy:20260916-benefit",
      '[blog_parts id="2843"]',
      '[blog_parts id="2846"]',
    ]
    remain=[m for m in forbidden if m in saved]
    if remain: raise RuntimeError("old/duplicate markers remain: "+repr(remain))
    if saved.count('[blog_parts id="2184"]')!=1: raise RuntimeError("CTN button count changed")
    ratio=len(saved)/max(1,len(target))
    if ratio<0.97 or ratio>1.03: raise RuntimeError(f"saved length drift too large: {ratio:.4f}")
    return {"saved_sha256":sha(saved),"saved_length":len(saved),"target_length":len(target),"length_ratio":ratio}
def report(d):
    REPORT.mkdir(parents=True,exist_ok=True)
    (REPORT/"result.json").write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# lexus-ux-discount revenue rewrite — 2026-09-16","",
      f"- result: **{d['result']}**",f"- mode: **{d['mode']}**",f"- post_id: **{POST_ID}**",
      f"- before_sha256: **{d.get('before_sha256','-')}**",f"- target_sha256: **{d.get('target_sha256','-')}**",
      f"- after_sha256: **{d.get('after_sha256','-')}**"]
    if d.get("errors"): lines+=["","## Errors"]+[f"- {e}" for e in d["errors"]]
    (REPORT/"summary.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines))
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--mode",choices=["preflight","apply"],default="preflight"); a=ap.parse_args()
    row=get_post(); original=validate_current(row); before_ident=ident(row); target=build(original)
    target_hash=sha(target)
    if EXPECTED_TARGET_SHA256 and target_hash!=EXPECTED_TARGET_SHA256:
        raise RuntimeError(f"target hash mismatch: {target_hash}")
    if a.mode=="preflight":
        report({"result":"PREFLIGHT_OK_NO_WRITES","mode":a.mode,"before_sha256":sha(original),"target_sha256":target_hash,"after_sha256":"","errors":[]})
        return 0
    if not EXPECTED_TARGET_SHA256:
        raise RuntimeError("apply refused: target hash not locked")
    errors=[]; wrote=False; saved_info={}
    try:
        req("POST",f"/wp-json/wp/v2/posts/{POST_ID}",{"content":target}); wrote=True
        saved=get_post(); saved_content=raw(saved,"content")
        saved_info=validate_saved(saved_content,target)
        if ident(saved)!=before_ident: raise RuntimeError("metadata changed")
    except Exception as e:
        errors.append(str(e))
        if wrote:
            try:
                req("POST",f"/wp-json/wp/v2/posts/{POST_ID}",{"content":original})
                rolled=get_post()
                if ident(rolled)!=before_ident: errors.append("rollback metadata mismatch")
                if sha(raw(rolled,"content"))!=sha(original): errors.append("rollback content hash mismatch")
            except Exception as rb: errors.append(f"rollback failed: {rb}")
        report({"result":"APPLY_FAILED_ROLLBACK_ATTEMPTED","mode":a.mode,"before_sha256":sha(original),"target_sha256":target_hash,"after_sha256":"","errors":errors})
        return 3
    final=get_post(); fc=raw(final,"content")
    try: saved_info=validate_saved(fc,target)
    except Exception as e: errors.append("final saved verify: "+str(e))
    if ident(final)!=before_ident: errors.append("final metadata mismatch")
    report({"result":"APPLIED_OK" if not errors else "APPLIED_BUT_VERIFY_FAILED","mode":a.mode,"before_sha256":sha(original),"target_sha256":target_hash,"after_sha256":sha(fc),"saved":saved_info,"errors":errors})
    return 0 if not errors else 4
if __name__=="__main__": raise SystemExit(main())
