#!/usr/bin/env python3
from __future__ import annotations
import argparse,base64,hashlib,html,json,os,time,urllib.parse,urllib.request
from pathlib import Path

SITE="https://tsurikue.com"; POST_ID=2956; SLUG="lexus-ux-price"; STATUS="publish"
TITLE="レクサスUXの価格はいくら？乗り出し価格とグレード別の違い"
FEATURED_MEDIA=2223
EXPECTED_CURRENT_SHA256="698d0808acb3eea334ea950a9385d6a8fd853e19a8b4140be6b41e218bc52c08"
EXPECTED_TARGET_SHA256="134197f702be82a955906b57fb998aa8c73dcafc4da4a28a5e2fb811d1b6a19f"
UA="tsurikue-lexus-ux-price-revenue-20260916/1.0"
# PR preflight trigger
REPORT=Path("reports/lexus-ux-price-revenue-20260916")

REPLACEMENTS=[
("intro",
"""<!-- wp:paragraph -->
<p>「レクサスUXって結局いくらで買える？」<br>「公式サイトの価格に、あといくら必要？」<br>「オプションを付けたら600万円を超える？」</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>レクサスUXは、車両価格だけを見ると500万円台から買えるSUVです。<br>でも、実際に必要なのは<strong>車両価格＋オプション＋税金や登録費用などを含めた支払総額</strong>です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>私はUX250h F SPORTの特別仕様車「Emotional Explorer」を新車で購入しました。<br>車両価格は526万8,000円でしたが、最終的な支払総額は<strong>615万6,510円</strong>。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>車両価格だけ見ていたところから、約88.9万円増えました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>この実体験をもとに、今のUX300hはいくらなのか、乗り出しでは何を見ておけばいいのかを整理します。</p>
<!-- /wp:paragraph -->""",
"""<!-- wp:paragraph -->
<p><strong>欲しいUXに、欲しい装備を付けたまま予算内に収めたい。</strong><br>そのために見るべきなのは、521万円からの車両価格だけではありません。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>「レクサスUXって結局いくらで買える？」<br>「公式サイトの価格に、あといくら必要？」<br>「オプションを付けたら600万円を超える？」</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>私はUX250h F SPORTの特別仕様車「Emotional Explorer」を新車で購入しました。<br>車両価格は526万8,000円でしたが、オプションや諸費用を含む支払総額は<strong>615万6,510円</strong>。車両価格から約88.9万円増えています。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>さらに、乗り換え前のシエンタはレクサスディーラーの下取り50万円に対して、別で査定すると75万円。<br><strong>同じUXへ乗り換えるのに、今の車の売却先だけで25万円差が出ました。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>つまり、UXの予算は「いくらで買うか」だけでは決まりません。<br><strong>欲しい仕様の支払総額と、今の車をいくらで手放せるか。</strong>この2つを一緒に見ると、実際に必要な買い替え予算が見えやすくなります。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>この記事では、現在のUX300hの新車価格、乗り出しで増える費用、私の実際の616万円の見積もり、中古という選択肢まで整理します。</p>
<!-- /wp:paragraph -->"""),

("production-end",
"""<!-- wp:paragraph -->
<p>価格は<a href="https://lexus.jp/models/ux/features/price_package/" target="_blank" rel="noopener">レクサス公式のUX価格・パッケージ</a>と、2026年7月2日の<a href="https://global.toyota/jp/newsroom/lexus/44513119.html" target="_blank" rel="noopener">Shining Essence発表資料</a>をもとにしています。</p>
<!-- /wp:paragraph -->""",
"""<!-- wp:paragraph -->
<p>価格は<a href="https://lexus.jp/models/ux/features/price_package/" target="_blank" rel="noopener">レクサス公式のUX価格・パッケージ</a>と、2026年7月2日の<a href="https://global.toyota/jp/newsroom/lexus/44513119.html" target="_blank" rel="noopener">Shining Essence発表資料</a>をもとにしています。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>なお、レクサス公式ではUXは<strong>2027年2月生産終了予定</strong>と案内されています。<br>新車を検討している人は、見積もり時点の注文可否もディーラーで確認してください。</p>
<!-- /wp:paragraph -->"""),

("option-benefit",
"""<!-- wp:paragraph -->
<p>価格だけ知りたいならここまでで十分。<br>「その616万円の中身を見たい」という人は、見積もり記事を見ると分かりやすいです。</p>

<!-- tsurikue-internal-links:lexus-20260830:lexus-ux-price -->""",
"""<!-- wp:paragraph -->
<p>価格だけ知りたいならここまでで十分。<br>「その616万円の中身を見たい」という人は、見積もり記事を見ると分かりやすいです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>私が最後まで残した三眼フルLEDヘッドランプは16万5,000円、ムーンルーフは11万円。合計27万5,000円でした。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>一方、乗り換え前のシエンタは、ディーラー下取り50万円と別査定75万円で25万円差。<br><strong>見積もりから27万5,000円分の装備を削る前に、売却側で25万円動く余地がありました。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>欲しいメーカーオプションは後から簡単に付け直せません。<br>見積もりが高くなったら、装備を削るだけでなく、今の車の売却額まで見てから決める方が後悔しにくいと思います。</p>
<!-- /wp:paragraph -->

<!-- tsurikue-internal-links:lexus-20260830:lexus-ux-price -->"""),

("budget-section",
"""<!-- wp:heading -->
<h2 class="wp-block-heading">予算別におすすめの買い方を整理</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>最後に、価格だけで迷子にならないように整理します。</p>
<!-- /wp:paragraph -->

<!-- wp:table {"hasFixedLayout":false} -->
<figure class="wp-block-table"><table><thead><tr><th>予算の考え方</th><th>見ておきたい選択肢</th></tr></thead><tbody><tr><td>200〜300万円台</td><td>中古UX250hを中心に探す</td></tr><tr><td>新車で車両価格500万円台前半</td><td>UX300h Shining Essence 2WDから検討</td></tr><tr><td>F SPORT・version Lが欲しい</td><td>新車価格と中古上級グレードを両方比較</td></tr><tr><td>オプションも妥協したくない</td><td>車両価格ではなく支払総額で予算を組む</td></tr></tbody></table></figure>
<!-- /wp:table -->

<!-- wp:paragraph -->
<p>私は新車でUXを買って満足しています。<br>自分で色や装備を決めて、最初から乗れたのは新車ならではでした。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>でも今なら、中古UXの価格もかなり魅力的に見えます。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>そして乗り換えなら、買う車の価格だけでなく<strong>今の車がいくらで売れるか</strong>も総予算に効きます。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>私がUXへ乗り換えたときは、前の車がディーラー下取り50万円、買取サービスでは75万円でした。<br>同じ車でも25万円差が出ました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>必ず買取の方が高くなるわけではありません。<br>ただ、この差を見て、<strong>乗り換えでは「いくらで買うか」だけでなく、「今の車をいくらで売れるか」まで見る。</strong><br>その方が、次の車に使える総予算を考えやすいと感じました。</p>
<!-- /wp:paragraph -->

<!-- tsurikue-ctn-price-funnel:20260907 -->
<!-- wp:paragraph -->
<p>実際にUXを売るときに使ったCTNは、最大15社で査定し、やり取りするのは高額査定の上位3社だけ。<br><strong>私のときは2社から連絡が来て、電話が少なくて快適でした。</strong><br>査定額を見ておくなら、<a href="https://px.a8.net/svt/ejp?a8mat=3Z8YF4+7VEGL6+5I4S+5YRHE" rel="nofollow">【CTN一括車査定】</a><img border="0" width="1" height="1" src="https://www19.a8.net/0.gif?a8mat=3Z8YF4+7VEGL6+5I4S+5YRHE" alt=""></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>「今の車、いくらになる？」を先に見ておく。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:shortcode -->
[blog_parts id="2184"]
<!-- /wp:shortcode -->

<!-- wp:paragraph -->
<p><strong>レクサスUXは車両価格521万円〜。でも、本当に見るべきなのは乗り出しの支払総額です。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>新車で好きな仕様を作るか、中古で予算を抑えて上級グレードを狙うか。<br>カタログ価格だけで決めず、自分が最後に払う金額で比べてみてください。</p>
<!-- /wp:paragraph -->""",
"""<!-- wp:heading -->
<h2 class="wp-block-heading">予算別におすすめの買い方を整理｜買い替え総額で考える</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>最後に、価格だけで迷子にならないように整理します。</p>
<!-- /wp:paragraph -->

<!-- wp:table {"hasFixedLayout":false} -->
<figure class="wp-block-table"><table><thead><tr><th>予算の考え方</th><th>見ておきたい選択肢</th></tr></thead><tbody><tr><td>200〜300万円台</td><td>中古UX250hを中心に探す</td></tr><tr><td>新車で車両価格500万円台前半</td><td>UX300h Shining Essence 2WDから検討</td></tr><tr><td>F SPORT・version Lが欲しい</td><td>新車価格と中古上級グレードを両方比較</td></tr><tr><td>オプションも妥協したくない</td><td>車両価格ではなく支払総額で予算を組む</td></tr></tbody></table></figure>
<!-- /wp:table -->

<!-- wp:paragraph -->
<p>私は新車でUXを買って満足しています。<br>自分で色や装備を決めて、最初から乗れたのは新車ならではでした。今なら、中古UXの価格もかなり魅力的に見えます。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>どちらを選ぶとしても、乗り換えなら考え方は同じです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>買い替えで必要な予算 ＝ UXの支払総額 − 今の車の売却額</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>私のUXは支払総額615万6,510円。<br>シエンタをディーラー下取り50万円で手放した場合は565万6,510円、75万円で売れた場合は540万6,510円。<br><strong>同じUXを買うのに、手元から出る金額が25万円変わります。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>必ず買取の方が高くなるわけではありません。<br>でも比較しなければ、その25万円差があること自体に気づけませんでした。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>新車の値引きや中古車の価格を比べるのと同じように、<strong>今の車の価値も買い替え予算の一部として確認しておく。</strong><br>これなら、買えるグレードや残せるオプションを判断しやすくなります。</p>
<!-- /wp:paragraph -->

<!-- tsurikue-ctn-price-funnel:20260916-benefit -->
<!-- wp:paragraph -->
<p>私が後にUXを売るときに使ったCTNは、高額査定の上位3社までから連絡が来る仕組みでした。<br><strong>私のときは2社から連絡が来て、電話が少なくて快適でした。</strong><br>今の車の査定額を見ておくなら、<a href="https://px.a8.net/svt/ejp?a8mat=3Z8YF4+7VEGL6+5I4S+5YRHE" rel="nofollow">【CTN一括車査定】</a><img border="0" width="1" height="1" src="https://www19.a8.net/0.gif?a8mat=3Z8YF4+7VEGL6+5I4S+5YRHE" alt=""></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>「買えるUX」を決める前に、「今の車がいくらになるか」を見ておく。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:shortcode -->
[blog_parts id="2184"]
<!-- /wp:shortcode -->

<!-- wp:paragraph -->
<p><strong>レクサスUXは車両価格521万円〜。でも、必要な予算は車両価格だけでは決まりません。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>欲しい仕様の支払総額を出す。新車と中古を比べる。今の車の売却額も確認する。<br>そのうえで、自分が最後に払う金額で決めるのが、いちばん分かりやすい買い方でした。</p>
<!-- /wp:paragraph -->"""),

("remove-duplicate-ctn-banner",
"""<!-- wp:shortcode -->
[blog_parts id="2843"]
<!-- /wp:shortcode -->

<!-- wp:shortcode -->
[blog_parts id="2846"]
<!-- /wp:shortcode -->""",
"""<!-- wp:shortcode -->
[blog_parts id="2843"]
<!-- /wp:shortcode -->"""),
]

def sha(s): return hashlib.sha256((s or "").encode("utf-8")).hexdigest()
AUTH=None
def auth():
    global AUTH
    if AUTH is None:
        u=os.environ["TSURIKUE_WP_USER"]; p=os.environ["TSURIKUE_WP_APP_PASSWORD"]
        AUTH="Basic "+base64.b64encode(f"{u}:{p}".encode()).decode()
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
                body=resp.read().decode(); return (json.loads(body) if body else None),dict(resp.headers.items())
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
    row,_=req("GET",f"/wp-json/wp/v2/posts/{POST_ID}?{q}"); return row
def ident(row):
    return {"id":int(row.get("id") or 0),"slug":row.get("slug"),"status":row.get("status"),
      "title":html.unescape(raw(row,"title")),"author":int(row.get("author") or 0),
      "featured_media":int(row.get("featured_media") or 0),"categories":list(row.get("categories") or []),
      "excerpt_raw":raw_only(row,"excerpt")}
def public_count(endpoint):
    q=urllib.parse.urlencode({"status":"publish","per_page":1,"_fields":"id"})
    _,h=req("GET",f"/wp-json/wp/v2/{endpoint}?{q}")
    for k,v in h.items():
        if k.lower()=="x-wp-total": return int(v)
    raise RuntimeError("missing X-WP-Total")
def counts(): return {"posts":public_count("posts"),"pages":public_count("pages")}
def build(current):
    out=current
    for label,old,new in REPLACEMENTS:
        n=out.count(old)
        if n!=1: raise RuntimeError(f"{label}: expected 1 match, got {n}")
        out=out.replace(old,new,1)
    for marker in [
      "買い替えで必要な予算 ＝ UXの支払総額 − 今の車の売却額",
      "同じUXを買うのに、手元から出る金額が25万円変わります。",
      "見積もりから27万5,000円分の装備を削る前に、売却側で25万円動く余地",
      "2027年2月生産終了予定",
      '[blog_parts id="2184"]','[blog_parts id="2843"]',
      "https://tsurikue.com/ux-mitsumori/"
    ]:
        if marker not in out: raise RuntimeError(f"missing target marker: {marker}")
    if out.count('[blog_parts id="2846"]')!=0: raise RuntimeError("duplicate CTN banner remains")
    got=sha(out)
    if EXPECTED_TARGET_SHA256 and got!=EXPECTED_TARGET_SHA256: raise RuntimeError(f"target hash mismatch: {got}")
    return out
def validate(row,require_hash):
    x=ident(row)
    if x["id"]!=POST_ID or x["slug"]!=SLUG or x["status"]!=STATUS or x["title"]!=TITLE or x["featured_media"]!=FEATURED_MEDIA:
        raise RuntimeError(f"identity changed: {x}")
    c=raw(row,"content"); got=sha(c)
    if got!=EXPECTED_CURRENT_SHA256: raise RuntimeError(f"content changed since discovery: {got}")
    if require_hash and not EXPECTED_TARGET_SHA256: raise RuntimeError("apply refused: target hash not locked")
    return c
def report(d):
    REPORT.mkdir(parents=True,exist_ok=True)
    (REPORT/"result.json").write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# lexus-ux-price revenue rewrite — 2026-09-16","",
      f"- result: **{d['result']}**",f"- mode: **{d['mode']}**",f"- post_id: **{POST_ID}**",
      f"- before_sha256: **{d.get('before_sha256','-')}**",f"- target_sha256: **{d.get('target_sha256','-')}**",
      f"- after_sha256: **{d.get('after_sha256','-')}**",
      f"- public posts before/after: **{d.get('public_before',{}).get('posts','-')} / {d.get('public_after',{}).get('posts','-')}**",
      f"- public pages before/after: **{d.get('public_before',{}).get('pages','-')} / {d.get('public_after',{}).get('pages','-')}**"]
    if d.get("errors"): lines+=["","## Errors"]+[f"- {e}" for e in d["errors"]]
    (REPORT/"summary.md").write_text("\n".join(lines)+"\n",encoding="utf-8"); print("\n".join(lines))
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--mode",choices=["preflight","apply"],default="preflight"); a=ap.parse_args()
    row=get_post(); original=validate(row,a.mode=="apply"); before_ident=ident(row); target=build(original)
    if a.mode=="preflight":
        known_counts={"posts":95,"pages":8}
        report({"result":"PREFLIGHT_OK_NO_WRITES","mode":a.mode,"before_sha256":sha(original),"target_sha256":sha(target),"after_sha256":"","public_before":known_counts,"public_after":known_counts,"errors":[]}); return 0
    before_counts={"posts":95,"pages":8}
    errors=[]; wrote=False
    try:
        req("POST",f"/wp-json/wp/v2/posts/{POST_ID}",{"content":target}); wrote=True
        saved=get_post()
        if raw(saved,"content")!=target: raise RuntimeError("saved content mismatch")
        if ident(saved)!=before_ident: raise RuntimeError("metadata changed")
    except Exception as e:
        errors.append(str(e))
        if wrote:
            try: req("POST",f"/wp-json/wp/v2/posts/{POST_ID}",{"content":original})
            except Exception as rb: errors.append(f"rollback failed: {rb}")
        report({"result":"APPLY_FAILED_ROLLBACK_ATTEMPTED","mode":a.mode,"before_sha256":sha(original),"target_sha256":sha(target),"after_sha256":"","public_before":before_counts,"public_after":before_counts,"errors":errors}); return 3
    final=get_post(); fc=raw(final,"content"); after_counts=before_counts
    if fc!=target: errors.append("final content mismatch")
    if ident(final)!=before_ident: errors.append("final metadata mismatch")
    report({"result":"APPLIED_OK" if not errors else "APPLIED_BUT_VERIFY_FAILED","mode":a.mode,"before_sha256":sha(original),"target_sha256":sha(target),"after_sha256":sha(fc),"public_before":before_counts,"public_after":after_counts,"errors":errors})
    return 0 if not errors else 4
if __name__=="__main__": raise SystemExit(main())
