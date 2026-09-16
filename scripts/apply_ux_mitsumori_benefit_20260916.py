#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, hashlib, html, json, os, time, urllib.parse, urllib.request
from pathlib import Path

SITE="https://tsurikue.com"
UA="tsurikue-apply-ux-mitsumori-benefit-20260916/1.0"
REPORT=Path("reports/ux-mitsumori-benefit-20260916")

POST_ID=2240
SLUG="ux-mitsumori"
STATUS="publish"
TITLE="レクサスUXの見積もり公開｜総額616万円で選んだ特別仕様車とオプション"
EXPECTED_CURRENT_SHA256="3028907ae8aaa2e104ab6f396d82e51a503533c4faf0fea2255ae85ca996a7b9"
EXPECTED_TARGET_SHA256="60e792fb670d488e82e57f6d93a6e19a83c3ca37ae98299c6813e3dad40dce2e"

REPLACEMENTS=[
("intro",
"""<!-- wp:paragraph -->
<p>私が購入したのは、2023年に納車されたレクサスUX250h Fスポーツ特別仕様車「Emotional Explorer」です。<br>2023年6月に初度登録され、オプションや諸費用を含む支払総額は6,156,510円でした。</p>

<!-- tsurikue-internal-links:lexus-20260830:ux-mitsumori -->
<!-- wp:paragraph -->
<p>現行UX300hの車両価格や乗り出し価格との違いは、<a href="https://tsurikue.com/lexus-ux-price/">レクサスUXの価格記事</a>で比較しています。</p>
<!-- /wp:paragraph -->
<!-- /wp:paragraph -->""",
"""<!-- wp:paragraph -->
<p><strong>616万円の見積もりを見て、最初に削りたくなるのはオプションです。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>でもメーカーオプションは、契約後や納車後に「やっぱり欲しい」と思っても簡単には戻せません。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>私が最後まで残した三眼フルLEDヘッドランプは16万5,000円、ムーンルーフは11万円。合計27万5,000円でした。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>一方、UXへ乗り換える前のシエンタは、レクサスディーラーの下取り50万円に対して、別で査定すると75万円。<br><strong>売却先の違いで25万円差が出て、あと2万5,000円でこの2つの装備に届く金額になりました。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>この経験から、私は見積もりが高くなったときに<strong>「欲しい装備を削る」だけでなく、「今の車をいくらで手放せるか」も一緒に見る</strong>ようになりました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>私が購入したのは、2023年に納車されたレクサスUX250h Fスポーツ特別仕様車「Emotional Explorer」です。<br>2023年6月に初度登録され、オプションや諸費用を含む支払総額は6,156,510円でした。</p>
<!-- /wp:paragraph -->

<!-- tsurikue-internal-links:lexus-20260830:ux-mitsumori -->
<!-- wp:paragraph -->
<p>現行UX300hの車両価格や乗り出し価格との違いは、<a href="https://tsurikue.com/lexus-ux-price/">レクサスUXの価格記事</a>で比較しています。</p>
<!-- /wp:paragraph -->"""),

("decision-method",
"""<!-- wp:paragraph -->
<p>小さくても、値段はしっかりレクサス。</p>
<!-- /wp:paragraph -->""",
"""<!-- wp:paragraph -->
<p>小さくても、値段はしっかりレクサス。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>そこで私は、見積もりの装備を次の3つに分けて考えました。</p>
<!-- /wp:paragraph -->

<!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li><strong>あとから付けにくいメーカーオプション</strong>：本当に欲しいなら残す</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li><strong>納車後でも追加しやすいディーラーオプション</strong>：後回し候補にする</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li><strong>自分の使い方では出番が少ないもの</strong>：思い切って削る</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->

<!-- wp:paragraph -->
<p><strong>安くするために全部削るのではなく、あとで後悔しにくい順番で整理する。</strong><br>この考え方にすると、616万円という総額でも「どこにお金を使うか」を決めやすくなりました。</p>
<!-- /wp:paragraph -->"""),

("sale-heading",
"""<!-- wp:heading -->
<h2 class="wp-block-heading">前の車を高く売れれば、次の車を安く買えたのと同じ</h2>
<!-- /wp:heading -->""",
"""<!-- wp:heading -->
<h2 class="wp-block-heading">欲しいオプションを削る前に、今の車の売却額を比べる</h2>
<!-- /wp:heading -->"""),

("sale-open",
"""<!-- wp:paragraph -->
<p>UXの支払総額は616万円でした。<br>車両本体価格やオプションばかりに目が向きますが、前に乗っていた車をいくらで手放せるかでも、実際の負担は変わります。</p>
<!-- /wp:paragraph -->""",
"""<!-- wp:paragraph -->
<p>UXの支払総額は616万円でした。<br>見積もりを下げようとすると、どうしてもオプションを削る方へ目が向きます。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>でも、買い替え全体で見ると、前に乗っていた車をいくらで手放せるかでも実際の負担は変わります。</p>
<!-- /wp:paragraph -->"""),

("sale-benefit",
"""<!-- wp:paragraph -->
<p>差額は25万円。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>少しでも高く売れれば、そのぶん次の車を安く買えたのと同じです。<br>私の場合は、ある意味、三眼LEDヘッドランプとムーンルーフをほぼ無料で付けられたようなものでした。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>これは大きい。</p>
<!-- /wp:paragraph -->""",
"""<!-- wp:paragraph -->
<p><strong>差額は25万円。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>三眼フルLEDヘッドランプ16万5,000円＋ムーンルーフ11万円＝27万5,000円。<br>25万円あれば、三眼LEDを付けても8万5,000円残ります。あと2万5,000円足せば、ムーンルーフまで両方に届きます。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>見積もりから27万5,000円分の装備を削る前に、売却側で25万円動く余地があった。</strong><br>私にとっては、こっちの方が大きな発見でした。</p>
<!-- /wp:paragraph -->"""),

("ctn-explain",
"""<!-- wp:paragraph -->
<p>CTNは、高額査定の上位3社までから連絡が来る仕組みです。<br>私がUXを売却したときは2社が実車査定を行い、最終的にカーセブンへ売却しています。</p>
<!-- /wp:paragraph -->""",
"""<!-- wp:paragraph -->
<p>CTNは、買取価格の上位3社のみを紹介する仕組みです。<br>私がUXを売却したときはカーセブンとネクステージの2社が実車査定を行い、最終的にカーセブンへ427万円で売却しています。</p>
<!-- /wp:paragraph -->"""),

("ctn-microcopy",
"""<!-- tsurikue-ctn-mitsumori-microcopy:20260907 -->
<!-- wp:paragraph -->
<p><strong>高く売りたい。でも、あの電話ラッシュはもういらない。</strong></p>
<!-- /wp:paragraph -->""",
"""<!-- tsurikue-ctn-mitsumori-microcopy:20260916-benefit -->
<!-- wp:paragraph -->
<p><strong>欲しいメーカーオプションを削る前に、今の車で何万円動くか見ておく。</strong></p>
<!-- /wp:paragraph -->"""),

("summary",
"""<!-- wp:heading -->
<h2 class="wp-block-heading">まとめ｜総額616万円でも、自分に必要な装備を選んだ</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>私が購入したレクサスUX250h Fスポーツ特別仕様車の支払総額は、6,156,510円でした。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>安い買い物ではありません。<br>それでも、三眼LEDヘッドランプ、ムーンルーフ、ヘッドアップディスプレイなど、所有後も付けてよかったと思えた装備があります。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>反対に、高級フロアマット、ドアバイザー、マークレビンソンは、買わなくても困りませんでした。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>オプションは、付ければ付けるほど満足できるとは限りません。<br>実際の使い方を考えながら、見た目にお金を使うところ、快適性を優先するところ、割り切って削るところを決めました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>最後は理屈だけではありません。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>Fスポーツの顔と、白いボディにブラックルーフ。<br>この見た目が好きだったので、この仕様を選びました。</strong></p>
<!-- /wp:paragraph -->""",
"""<!-- wp:heading -->
<h2 class="wp-block-heading">まとめ｜削る順番を決めれば、616万円の見積もりでも納得しやすい</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>私が購入したレクサスUX250h Fスポーツ特別仕様車の支払総額は、6,156,510円でした。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>安い買い物ではありません。<br>それでも、三眼LEDヘッドランプ、ムーンルーフ、ヘッドアップディスプレイなど、所有後も付けてよかったと思えた装備があります。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>反対に、高級フロアマット、ドアバイザー、マークレビンソンは、買わなくても困りませんでした。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>もし今もう一度見積もりを作るなら、私は<strong>使わないものを削る → 後から足せるものを後回しにする → 今の車の売却額を確認する → それでも予算を超えるなら最後にメーカーオプションを見直す</strong>、の順で考えます。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>欲しい装備を最初から全部あきらめるのではなく、買い替え全体で予算を整える。<br>その方が、納車されたあとに「本当は付けたかった」と残りにくいと思います。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>最後は理屈だけではありません。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>Fスポーツの顔と、白いボディにブラックルーフ。<br>この見た目が好きだったので、この仕様を選びました。</strong></p>
<!-- /wp:paragraph -->"""),
]

def sha256(s:str)->str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()

AUTH=None
def auth_header():
    user=os.environ.get("TSURIKUE_WP_USER"); pw=os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not pw: raise RuntimeError("missing WordPress secrets")
    return "Basic "+base64.b64encode(f"{user}:{pw}".encode()).decode()

def request(method,path,payload=None):
    global AUTH
    if AUTH is None: AUTH=auth_header()
    headers={"Authorization":AUTH,"Accept":"application/json","User-Agent":UA}
    data=None
    if payload is not None:
        headers["Content-Type"]="application/json; charset=utf-8"
        data=json.dumps(payload,ensure_ascii=False).encode("utf-8")
    req=urllib.request.Request(SITE+path,data=data,headers=headers,method=method)
    last=None
    for n in range(3):
        try:
            with urllib.request.urlopen(req,timeout=60) as resp:
                body=resp.read().decode("utf-8")
                return json.loads(body) if body else None, dict(resp.headers.items())
        except Exception as exc:
            last=exc
            if n<2: time.sleep(2*(n+1))
    raise last

def raw_field(row,key):
    value=row.get(key) or {}
    return (value.get("raw") or value.get("rendered") or "") if isinstance(value,dict) else str(value)

def raw_only_field(row,key):
    value=row.get(key) or {}
    return value.get("raw","") if isinstance(value,dict) else str(value)

def public_count(endpoint):
    q=urllib.parse.urlencode({"status":"publish","per_page":1,"_fields":"id"})
    _,headers=request("GET",f"/wp-json/wp/v2/{endpoint}?{q}")
    for k,v in headers.items():
        if k.lower()=="x-wp-total": return int(v)
    raise RuntimeError(f"X-WP-Total missing for {endpoint}")

def public_counts():
    return {"posts":public_count("posts"),"pages":public_count("pages")}

def get_post():
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,content,author,featured_media,categories,excerpt"})
    row,_=request("GET",f"/wp-json/wp/v2/posts/{POST_ID}?{q}")
    return row

def identity_snapshot(row):
    return {
        "id":int(row.get("id") or 0),
        "slug":row.get("slug"),
        "status":row.get("status"),
        "title":html.unescape(raw_field(row,"title")),
        "author":int(row.get("author") or 0),
        "featured_media":int(row.get("featured_media") or 0),
        "categories":list(row.get("categories") or []),
        "excerpt_raw":raw_only_field(row,"excerpt"),
    }

def build_target(current):
    revised=current
    for label,old,new in REPLACEMENTS:
        count=revised.count(old)
        if count!=1:
            raise RuntimeError(f"{label}: expected exactly 1 match, got {count}")
        revised=revised.replace(old,new,1)
    for marker in [
        "616万円の見積もりを見て、最初に削りたくなるのはオプションです。",
        "あと2万5,000円でこの2つの装備に届く金額",
        "あとで後悔しにくい順番で整理する",
        "欲しいオプションを削る前に、今の車の売却額を比べる",
        "欲しいメーカーオプションを削る前に、今の車で何万円動くか見ておく。",
        '[blog_parts id="2184"]',
        "https://tsurikue.com/ux-resale/",
    ]:
        if marker not in revised: raise RuntimeError(f"missing target marker: {marker}")
    got=sha256(revised)
    if EXPECTED_TARGET_SHA256 and got!=EXPECTED_TARGET_SHA256:
        raise RuntimeError(f"target hash mismatch: {got}")
    return revised

def validate_current(row, require_hash):
    ident=identity_snapshot(row)
    if ident["id"]!=POST_ID or ident["slug"]!=SLUG or ident["status"]!=STATUS or ident["title"]!=TITLE:
        raise RuntimeError(f"identity changed: {ident}")
    current=raw_field(row,"content")
    got=sha256(current)
    if require_hash and not EXPECTED_CURRENT_SHA256:
        raise RuntimeError("apply refused: current hash is not locked")
    if EXPECTED_CURRENT_SHA256 and got!=EXPECTED_CURRENT_SHA256:
        raise RuntimeError(f"content changed since reviewed snapshot: {got}")
    return current

def write_report(data):
    REPORT.mkdir(parents=True,exist_ok=True)
    (REPORT/"result.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=[
        "# ux-mitsumori benefit rewrite — 2026-09-16","",
        f"- result: **{data['result']}**",
        f"- mode: **{data['mode']}**",
        f"- post_id: **{POST_ID}**",
        f"- slug: **{SLUG}**",
        f"- status: **{data.get('status','-')}**",
        f"- before_sha256: **{data.get('before_sha256','-')}**",
        f"- target_sha256: **{data.get('target_sha256','-')}**",
        f"- after_sha256: **{data.get('after_sha256','-')}**",
        f"- public posts before/after: **{data.get('public_before',{}).get('posts','-')} / {data.get('public_after',{}).get('posts','-')}**",
        f"- public pages before/after: **{data.get('public_before',{}).get('pages','-')} / {data.get('public_after',{}).get('pages','-')}**",
    ]
    if data.get("errors"):
        lines+=["","## Errors"]+[f"- {x}" for x in data["errors"]]
    (REPORT/"summary.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--mode",choices=["preflight","apply"],default="preflight"); args=ap.parse_args()
    public_before=public_counts()
    before=get_post()
    original=validate_current(before,require_hash=(args.mode=="apply"))
    before_identity=identity_snapshot(before)
    target=build_target(original)
    if args.mode=="preflight":
        write_report({
            "result":"PREFLIGHT_OK_NO_WRITES","mode":args.mode,"status":before_identity["status"],
            "before_sha256":sha256(original),"target_sha256":sha256(target),"after_sha256":"",
            "public_before":public_before,"public_after":public_before,"errors":[]
        })
        return 0

    errors=[]; wrote=False
    try:
        request("POST",f"/wp-json/wp/v2/posts/{POST_ID}",{"content":target}); wrote=True
        saved_row=get_post(); saved=raw_field(saved_row,"content")
        if saved!=target: raise RuntimeError("saved content mismatch")
        if identity_snapshot(saved_row)!=before_identity: raise RuntimeError("identity/metadata changed after write")
        if public_counts()!=public_before: raise RuntimeError("public post/page counts changed")
    except Exception as exc:
        errors.append(str(exc))
        if wrote:
            try:
                request("POST",f"/wp-json/wp/v2/posts/{POST_ID}",{"content":original})
                rb=get_post()
                if sha256(raw_field(rb,"content"))!=sha256(original): errors.append("rollback content hash mismatch")
                if identity_snapshot(rb)!=before_identity: errors.append("rollback identity mismatch")
            except Exception as rb_exc:
                errors.append(f"rollback failed: {rb_exc}")
        write_report({
            "result":"APPLY_FAILED_ROLLBACK_ATTEMPTED","mode":args.mode,"status":before_identity["status"],
            "before_sha256":sha256(original),"target_sha256":sha256(target),"after_sha256":"",
            "public_before":public_before,"public_after":public_counts(),"errors":errors
        })
        return 3

    final=get_post(); final_content=raw_field(final,"content"); final_identity=identity_snapshot(final); public_after=public_counts()
    if final_content!=target: errors.append("final content mismatch")
    if final_identity!=before_identity: errors.append("final identity mismatch")
    if public_after!=public_before: errors.append("final public counts changed")
    write_report({
        "result":"APPLIED_OK" if not errors else "APPLIED_BUT_FINAL_VERIFY_FAILED","mode":args.mode,"status":final_identity["status"],
        "before_sha256":sha256(original),"target_sha256":sha256(target),"after_sha256":sha256(final_content),
        "public_before":public_before,"public_after":public_after,"errors":errors
    })
    return 0 if not errors else 4

if __name__=="__main__":
    raise SystemExit(main())
