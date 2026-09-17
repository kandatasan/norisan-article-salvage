#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, hashlib, html, json, os, re, time, urllib.parse, urllib.request
from pathlib import Path

SITE="https://tsurikue.com"
POST_ID=2948
SLUG="lexus-ux-used"
STATUS="publish"
TITLE="レクサスUXの中古は狙い目？新車と比べて中古をおすすめしたい理由"
FEATURED_MEDIA=1001
EXPECTED_CURRENT_SHA256="49258a7360a97a1ec93e0b5bfc7a31d227bb84fd6488f59580d68b4ec9bd7f80"
EXPECTED_TARGET_SHA256="913ffb061ede762a524f86d9b400c313a5ef6e17d467d5af7b8a07c79373f4bc"
REPORT=Path("reports/lexus-ux-used-best-20260917")
UA="tsurikue-lexus-ux-used-best-20260917/1.0"

NEW_INTRO = r'''<p><!-- lexus-salvage:v1 slug=lexus-ux-used source=lexus-diary.com/used-car/ --><br />
<!-- tsurikue-editorial:v1 slug=lexus-ux-used -->
<!-- tsurikue-media-patch:v1 slug=lexus-ux-used key=interior-comparison-20260830 --></p>

<!-- wp:paragraph -->
<p><strong>UX250h F SPORTが車両本体199.6万円。</strong><br>2026年9月に中古車情報を見て、正直ちょっと笑いました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>私はUX250h F SPORTの特別仕様車「Emotional Explorer」を新車で購入し、オプションや諸費用を含めて約616万円支払っています。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>1年以上・1万km以上乗ったうえで言うと、<strong>前席の居心地と乗り味は、価格が200万円台になってもUXのままです。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>後席は広くない。荷室も大きくない。<br>でも前席2人で乗る時間の心地よさ、扱いやすいサイズ、見た目のかっこよさは、私が新車で乗っていたときに気に入っていた部分です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>だから今の中古UXは、ただ「安くなったレクサス」ではなく、<strong>200万円台でどこまで条件のいい1台を掘れるか</strong>が面白い。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>この記事では、最安値に飛びつくのではなく、<strong>コスパ最強・完成度最強・安心最強</strong>の3方向から「今ならどのUXを狙うか」を考えます。</p>
<!-- /wp:paragraph -->

<!-- wp:image {"id":2587,"sizeSlug":"large","linkDestination":"none"} -->
<figure class="wp-block-image size-large"><img src="http://tsurikue.com/wp-content/uploads/2026/07/IMG_3906-1024x710.jpeg" alt="" class="wp-image-2587"/></figure>
<!-- /wp:image -->

'''
NEW_SEC0 = r'''<!-- wp:heading -->
<h2 class="wp-block-heading">結論｜中古UXは今「最強個体を探す」のが面白い</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>2026年9月13日更新のグーネットでは、UX全体で843台。UX250h F SPORTは<strong>199.6万円〜</strong>、version Lは<strong>209.2万円〜</strong>の掲載があります。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ただし、最安値だけ見て「200万円でF SPORTが買える！」と飛びつくのは違います。</p>
<!-- /wp:paragraph -->

<!-- wp:table {"hasFixedLayout":false} -->
<figure class="wp-block-table"><table><thead><tr><th>掲載例</th><th>支払総額</th><th>年式・走行距離</th><th>私ならどう見るか</th></tr></thead><tbody>
<tr><td>F SPORT<br>車両199.6万円</td><td>208.8万円</td><td>2019年・10.9万km<br>修復歴あり</td><td>最安の理由を理解して見る個体</td></tr>
<tr><td>F SPORT<br>車両228.7万円</td><td>239.9万円</td><td>2019年・8.9万km<br>修復歴なし</td><td>200万円台前半でF SPORTを狙う候補</td></tr>
<tr><td>F SPORT<br>車両268.9万円</td><td>279.9万円</td><td>2020年・3.0万km<br>修復歴なし</td><td><strong>価格と状態のバランスが面白い</strong></td></tr>
<tr><td>F SPORT<br>車両273万円</td><td>278万円</td><td>2018年・4.0万km<br>修復歴なし</td><td>三眼LED・PVMなど装備を見て選びたい</td></tr>
</tbody></table></figure>
<!-- /wp:table -->

<!-- wp:paragraph -->
<p>中古車は毎日入れ替わるので、この4台そのものをおすすめする表ではありません。<br><strong>「200万円台でF SPORTの条件違いを比較できる」</strong>という今の相場感を見るための例です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>私は616万円でUXを買いました。<br>それを知っているからこそ、支払総額200万円台のF SPORTを見ると「いや、これ満足度高いだろ」と思います。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>現在の掲載状況は<a href="https://www.goo-net.com/usedcar/brand-LEXUS/car-UX/grade-16-10052004/" target="_blank" rel="noopener">グーネットのUX250h F SPORT中古車情報</a>などで確認できます。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>まずは条件を決めすぎず、今どんなUXが出ているかを見る。</strong><br>宝探しはそこからです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><a href="https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY" rel="nofollow">ガリバーで中古のレクサスUXを探してみる</a><img border="0" width="1" height="1" src="https://www15.a8.net/0.gif?a8mat=4B65SD+8DUSHE+9QU+NVHCY" alt=""></p>
<!-- /wp:paragraph -->

'''
NEW_SEC1 = r'''<!-- wp:heading -->
<h2 class="wp-block-heading">中古UXの「最強」は3つある</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>私なら中古UXを「一番安い1台」では選びません。<br>何を優先するかで、最強は変わります。</p>
<!-- /wp:paragraph -->

<!-- wp:table {"hasFixedLayout":false} -->
<figure class="wp-block-table"><table><thead><tr><th>狙い方</th><th>私なら見るUX</th><th>こんな人向け</th></tr></thead><tbody>
<tr><td><strong>コスパ最強</strong></td><td>前期UX250h F SPORT / version L</td><td>200万円台で前席の質感と乗り味を取りたい</td></tr>
<tr><td><strong>完成度最強</strong></td><td>2022年改良後のUX250h</td><td>タッチ式ディスプレイ・走り・安全装備も重視</td></tr>
<tr><td><strong>安心最強</strong></td><td>レクサス認定中古車CPO</td><td>価格より保証・整備履歴を優先したい</td></tr>
</tbody></table></figure>
<!-- /wp:table -->

<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">私の本命は「前期F SPORTの装備が濃い個体」</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>価格と満足度のバランスだけで選ぶなら、私はまず前期F SPORTを掘ります。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>見るのは価格だけではありません。<br><strong>三眼LED・パノラミックビューモニター・BSM・ムーンルーフ・HUD</strong>など、新車では追加費用が必要だった装備が付いているかを見ます。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>同じ200万円台なら、ベースグレードを安く買うより、装備の濃いF SPORTやversion Lが出ていないか先に探したいです。</p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">2022年以降は高い。でも中身はしっかり進化</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>2022年の改良では、ボディ剛性、EPSやアブソーバー、安全装備、マルチメディアなどが更新されています。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>2026年9月の掲載では、2022年式F SPORTで支払総額400万円前後の例もあります。<br>200万円台の前期と比べると一気に高くなるので、<strong>「安くUXに乗る」より「完成度の高い250hを選ぶ」方向</strong>です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>なお、現行UX300hは521万円〜575万7,000円で、レクサス公式では<strong>2027年2月生産終了予定</strong>と案内されています。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>最後の新車にこだわるのか。<br>価格がこなれた250hを掘るのか。<br>今はこの比較がかなり面白い時期だと思います。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>新車UX300hとの違いを詳しく比べたい人は、<a href="https://tsurikue.com/lexus-ux250h-used-vs-ux300h/">中古UX250hと新車UX300hを比べた記事</a>もどうぞ。</p>
<!-- /wp:paragraph -->

'''
OLD_CTN = r'''<!-- tsurikue-ctn-used-funnel:20260907 -->
<!-- wp:paragraph -->
<p>中古UXを少しでも安く探すのは、もちろん効果があります。<br>でも乗り換え全体で見ると、<strong>今の車を高く売る方が金額が大きく動くこともあります。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>実際に私がUXを売るときはCTNを使いました。<br>最大15社で査定し、やり取りするのは高額査定の上位3社だけ。<br><strong>私のときは2社から連絡が来て、電話が少なくて快適でした。</strong><br>査定額を見ておくなら、<a href="https://px.a8.net/svt/ejp?a8mat=3Z8YF4+7VEGL6+5I4S+5YRHE" rel="nofollow">【CTN一括車査定】</a><img border="0" width="1" height="1" src="https://www19.a8.net/0.gif?a8mat=3Z8YF4+7VEGL6+5I4S+5YRHE" alt=""></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>まずは「今の車、いくらになる？」から。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:shortcode -->
[blog_parts id="2184"]
<!-- /wp:shortcode -->

'''
NEW_CTN = r'''<!-- tsurikue-ctn-used-funnel:20260917-treasure -->
<!-- wp:paragraph -->
<p>中古UXは、予算が上がるほど走行距離・状態・装備の選択肢が増えます。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>私がUXへ乗り換えたときは、前のシエンタがディーラー下取り50万円、別査定75万円。<br><strong>25万円差が出ました。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>25万円あれば、200万円台前半のUXを探していた人が、走行距離や装備をもう一段こだわれる予算に近づきます。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>実際に私がUXを売るときはCTNを使い、連絡が来たのはカーセブンとネクステージの2社でした。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>「安いUXを探す」だけでなく、「今の車をいくらで売れるか」も一緒に見る。</strong><br>その方が、宝探しの選択肢を減らさずに済みます。</p>
<!-- /wp:paragraph -->

<!-- wp:shortcode -->
[blog_parts id="2184"]
<!-- /wp:shortcode -->

'''
OLD_SUMMARY = r'''<!-- wp:paragraph -->
<p>私は新車でUXを買って良かったと思っています。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>それでも、今もう一度UXを選ぶなら中古車からも探します。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>新車では500万円前後から。中古なら200〜300万円台も見えてくる。</strong><br>UXのサイズ感とデザインが好きな人にとって、この価格差は大きいです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>年式やグレードだけで決めず、状態・装備・保証・支払総額まで見て、自分に合う1台を探してみてください。</p>
<!-- /wp:paragraph -->

'''
NEW_SUMMARY = r'''<!-- wp:heading -->
<h2 class="wp-block-heading">まとめ｜200万円台のUXは「安いレクサス」じゃなく宝探し</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>私は新車でUXを買って良かったと思っています。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>それでも今もう一度選ぶなら、<strong>最初に中古UX250hのF SPORTとversion Lを掘ります。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>前席の居心地、乗り心地、扱いやすいサイズ感。<br>私が616万円のUXで気に入っていた部分は、中古になったから消えるわけではありません。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>だから面白いのは、199.6万円の最安車を買うことではなく、<strong>200万円台で「これは当たりじゃない？」と思える1台を探すこと。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>修復歴、走行距離、整備履歴、保証、欲しい装備、そして支払総額。<br>条件を見比べながら、自分にとっての最強UXを探してみてください。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>お宝UX、まだ普通に埋まっています。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><a href="https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY" rel="nofollow">ガリバーで中古のレクサスUXを探してみる</a><img border="0" width="1" height="1" src="https://www15.a8.net/0.gif?a8mat=4B65SD+8DUSHE+9QU+NVHCY" alt=""></p>
<!-- /wp:paragraph -->

'''
OLD_FOOT = r'''<!-- wp:shortcode -->
[blog_parts id="2843"]
<!-- /wp:shortcode -->

<!-- wp:shortcode -->
[blog_parts id="2846"]
<!-- /wp:shortcode -->'''
NEW_FOOT = r'''<!-- tsurikue-revenue-cta-dedup:20260917-ux-used -->'''

def sha(s): return hashlib.sha256((s or "").encode()).hexdigest()
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
                b=resp.read().decode(); return json.loads(b) if b else None
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
    c=raw(row,"content")
    if sha(c)!=EXPECTED_CURRENT_SHA256: raise RuntimeError(f"content changed: {sha(c)}")
    return c
def replace_once(s,old,new,label):
    if s.count(old)!=1: raise RuntimeError(f"{label}: expected 1 match, got {s.count(old)}")
    return s.replace(old,new,1)
def build(c):
    heads=list(re.finditer(r'<!-- wp:heading -->\s*<h2 class="wp-block-heading">(.*?)</h2>\s*<!-- /wp:heading -->',c,re.S))
    if len(heads)<3: raise RuntimeError("h2 structure changed")
    c=NEW_INTRO+NEW_SEC0+NEW_SEC1+c[heads[2].start():]
    c=replace_once(c,OLD_CTN,NEW_CTN,"ctn")
    c=replace_once(c,OLD_SUMMARY,NEW_SUMMARY,"summary")
    c=replace_once(c,OLD_FOOT,NEW_FOOT,"footer")
    required=["UX250h F SPORTが車両本体199.6万円","コスパ最強","完成度最強","安心最強",
      "200万円台で「これは当たりじゃない？」と思える1台","[blog_parts id=\"2184\"]",
      "https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY","2027年2月生産終了予定",
      "tsurikue-revenue-cta-dedup:20260917-ux-used"]
    for m in required:
        if m not in c: raise RuntimeError("missing target marker: "+m)
    if "[blog_parts id=\"2843\"]" in c or "[blog_parts id=\"2846\"]" in c:
        raise RuntimeError("duplicate footer parts remain")
    if sha(c)!=EXPECTED_TARGET_SHA256: raise RuntimeError(f"target hash mismatch: {sha(c)}")
    return c
def validate_saved(c,target):
    required=["UX250h F SPORTが車両本体199.6万円","支払総額</th>","コスパ最強","完成度最強","安心最強",
      "200万円台で「これは当たりじゃない？」と思える1台","[blog_parts id=\"2184\"]",
      "https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY","tsurikue-revenue-cta-dedup:20260917-ux-used"]
    missing=[m for m in required if m not in c]
    if missing: raise RuntimeError("saved markers missing: "+repr(missing))
    if "[blog_parts id=\"2843\"]" in c or "[blog_parts id=\"2846\"]" in c: raise RuntimeError("old footer remains")
    ratio=len(c)/max(1,len(target))
    if not 0.97<=ratio<=1.03: raise RuntimeError(f"saved length drift: {ratio:.4f}")
def report(d):
    REPORT.mkdir(parents=True,exist_ok=True)
    (REPORT/"result.json").write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")
    (REPORT/"summary.md").write_text("\n".join([
      "# UX used best rewrite","",f"- result: **{d['result']}**",f"- mode: **{d['mode']}**",
      f"- before_sha256: **{d.get('before','-')}**",f"- target_sha256: **{d.get('target','-')}**",
      f"- after_sha256: **{d.get('after','-')}**"]+([f"- error: {e}" for e in d.get("errors",[])]))+"\n",encoding="utf-8")
    print(json.dumps(d,ensure_ascii=False,indent=2))
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--mode",choices=["preflight","apply"],default="preflight"); a=ap.parse_args()
    row=get_post(); original=validate_current(row); before_ident=ident(row); target=build(original)
    if a.mode=="preflight":
        report({"result":"PREFLIGHT_OK_NO_WRITES","mode":a.mode,"before":sha(original),"target":sha(target),"after":"","errors":[]}); return 0
    errors=[]; wrote=False
    try:
        req("POST",f"/wp-json/wp/v2/posts/{POST_ID}",{"content":target}); wrote=True
        saved=get_post(); sc=raw(saved,"content"); validate_saved(sc,target)
        if ident(saved)!=before_ident: raise RuntimeError("metadata changed")
    except Exception as e:
        errors.append(str(e))
        if wrote:
            try: req("POST",f"/wp-json/wp/v2/posts/{POST_ID}",{"content":original})
            except Exception as rb: errors.append("rollback failed: "+str(rb))
        report({"result":"APPLY_FAILED_ROLLBACK_ATTEMPTED","mode":a.mode,"before":sha(original),"target":sha(target),"after":"","errors":errors}); return 3
    final=get_post(); fc=raw(final,"content")
    try: validate_saved(fc,target)
    except Exception as e: errors.append("final verify: "+str(e))
    if ident(final)!=before_ident: errors.append("final metadata mismatch")
    report({"result":"APPLIED_OK" if not errors else "APPLIED_BUT_VERIFY_FAILED","mode":a.mode,"before":sha(original),"target":sha(target),"after":sha(fc),"errors":errors})
    return 0 if not errors else 4
if __name__=="__main__": raise SystemExit(main())
