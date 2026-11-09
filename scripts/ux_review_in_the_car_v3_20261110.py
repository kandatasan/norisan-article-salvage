#!/usr/bin/env python3
"""Second-pass conversational UX review: WP preflight on PR, guarded one-post edit on main."""
from __future__ import annotations
import base64,hashlib,json,os,re,urllib.parse,urllib.request
from pathlib import Path

SITE="https://tsurikue.com"
PID=2870
SLUG="lexus-ux-review"
SOURCE_SHA="6d53f5fe818658f4695c3abbb1202f06daf18abce38a6aa353a2cdf41f8b6c05"
OUT=Path("reports/ux-review-in-the-car-v3-20261110")
META=("id","slug","status","title","featured_media","categories","author")
def sha(s):return hashlib.sha256(s.encode("utf-8")).hexdigest()
def p(s):return '<!-- wp:paragraph -->\n<p>'+s+'</p>\n<!-- /wp:paragraph -->'
def h2(s):return '<!-- wp:heading -->\n<h2 class="wp-block-heading">'+s+'</h2>\n<!-- /wp:heading -->'
def h3(s):return '<!-- wp:heading {"level":3} -->\n<h3 class="wp-block-heading">'+s+'</h3>\n<!-- /wp:heading -->'
def link(slug,s):return '<a href="https://tsurikue.com/'+slug+'/">'+s+'</a>'
def lst(rows):return '<!-- wp:list {"className":"wp-block-list"} -->\n<ul class="wp-block-list">'+'\n'.join('<!-- wp:list-item -->\n<li>'+x+'</li>\n<!-- /wp:list-item -->' for x in rows)+'</ul>\n<!-- /wp:list -->'

def transform(src):
    if sha(src)!=SOURCE_SHA:raise RuntimeError("SOURCE_CONTENT_CHANGED_NO_WRITE")
    start=src.index('<!-- wp:paragraph -->')
    anchor='<p><!-- tq-lexus-related-cards:v1:lexus-ux-review --></p>'
    if src.count(anchor)!=1:raise RuntimeError("RELATED_CARDS_ANCHOR_CHANGED")
    end=src.index(anchor)
    head,footer=src[:start],src[end:]
    imgs=re.findall(r'<!-- wp:image.*?<!-- /wp:image -->',src,re.S)
    tbl=re.findall(r'<!-- wp:table.*?<!-- /wp:table -->',src,re.S)
    if len(imgs)!=3 or len(tbl)!=1:raise RuntimeError("ORIGINAL_IMAGES_OR_TABLE_CHANGED")
    core=[
      p('車幅1,840mmのレクサスUX。<br>数字だけ見ると小さくないのに、駐車場で向きを変えると、これが意外と扱いやすい。<br>ああ、やっぱり運転しやすい。この感覚が好きなんです。'),
      p('乗っているのはUX250h F SPORT、特別仕様車「Emotional Explorer」。1年以上、1万km以上を一緒に走りました。<br>オプション込みで約616万円。<br><strong>高っ！</strong><br>なのに、走り出すとやっぱり気持ちいい。後席と荷室には文句もあるけど、F SPORTの顔を見ると、また好きになる。'),
      imgs[0],
      h2('1万km以上乗ってつけたレクサスUXの評価'),
      p('まずは、UX250hを10点満点で採点した結果から。'),
      tbl[0],
      p('乗り心地10点。操作性も10点。<br>ところが利便性は6点です。<br>運転しているときは文句なし。でも、後ろに人を乗せる、荷物を積む。そうなると話が変わる。<br>ああ、惜しい。'),
      h2('UXに乗っていて、特に好きだったところ'),
      h3('車幅1,840mm。でも小回りは利く'),
      p('欲しかったのは、大きすぎない高級SUV。<br>ところがUXの車幅は1,840mmあります。<br>あれ、意外と幅はあるな。'),
      p('でも、ハンドルを切ると最小回転半径5.2mが効いてくる。<br>スーパーの駐車場も、旅行先の知らない道も、思ったより扱いやすいんです。<br>街中を走って、高速道路へ出る。どっちも気持ちいい。<br>これこれ。私が欲しかったのは、この運転のしやすさ。'),
      h3('乗り心地は10点。静かさは8点'),
      p('街中でも高速でも、乗り心地がいい。<br>レクサスの上位車種と比べても、私には大きな差が分からないくらいです。<br>1万km以上走っても、この気持ちよさは変わらない。だから10点。'),
      p('静かさは8点。<br>路面によってはロードノイズが入るので満点とはいきません。<br>ただ、会話もBGMも楽しめる。このくらいなら私は気になりません。'),
      p('あとでUX300hにも試乗しました。<br>確かに進化してる。でも、250hから乗り換えないと物足りないかといえば、私はそうでもない。<br>詳しい違いは'+link('ux300h','UX300hの試乗レビュー')+'で紹介しています。'),
      h3('F SPORTのデザインが、やっぱり好き'),
      p('F SPORTのこの顔、やっぱりかっこいい。<br>ホワイトノーヴァガラスフレークにブラックルーフ。この組み合わせが好きで、特別仕様車を選びました。<br>走行距離が1万kmを超えても、見飽きないんですよね。'),
      imgs[1],
      h2('後席・荷室・価格。ここは気になった'),
      p('気になったのは、この3つです。'),
      lst(['<strong>後席：</strong>大人は座れるけど、ゆったりとは言えない','<strong>荷室：</strong>普段の買い物はいいけど、大きな荷物は苦手','<strong>価格：</strong>オプション込み約616万円。NXも候補に入る金額']),
      p('後席は、大人が座れないわけじゃない。<br>でも、ゆったりくつろげる広さではありません。3人以上で長距離となると、さすがに気になります。<br>それに荷室。日常の買い物や2人旅ならいいんですが、段ボールみたいな大きい荷物を載せるときが厄介。向きを変えて、また変えて。荷室でテトリスです。'),
      p('しかも総額約616万円。<br>ここまで出すと、NXも買えるんじゃないかと気になります。<br>広さだけで選ぶなら、そっちの方がいいかもしれない。でも、私が乗りたいのはこのUXなんですよ。'),
      p('もっと細かい不満は'+link('ux-koukai','UXを616万円で買って感じた後悔と満足')+'で書いています。'),
      '<!-- tsurikue-internal-links:lexus-20260830:lexus-ux-review -->',
      '<p><!-- tsurikue-ctn-review-funnel:20260907 --></p>',
      h2('レクサスUXは、どんな人に向いている？'),
      p('私なら、こんな使い方をする人にすすめます。'),
      lst(['普段は1〜2人で乗ることが多い','街乗りもドライブも、運転を楽しみたい','後席や荷室の広さより、乗り心地やデザインを優先したい']),
      p('山陰、角島、淡路島。UXであちこち走りました。<br>目的地へ向かう道も楽しい。高速を走る時間も好き。<br>「着いたら楽しい」じゃなくて、乗っている間から楽しいんです。'),
      p('ただ、後席と荷室の狭さだけはごまかせません。<br>大人4〜5人で遠出するなら、実車で後席と荷室を確認してほしいです。広さ優先ならNXなども見比べた方がいいと思います。'),
      imgs[2],
      h2('今から買うなら、私は中古のUX250hを探す'),
      p('そんなUXを今から買い直すなら、私は中古のUX250hから探します。<br>新車に616万円払った本人が言うんだから、なんとも複雑ですけど。'),
      p('だって250hでも、乗り心地も運転のしやすさも十分に好きなんです。<br>UX300hも良くなっているけど、だからといって250hが急に残念な車になるわけじゃありません。'),
      p('新しい装備や保証を優先するなら新車。<br>予算も考えて選ぶなら、中古の250hも面白いと思います。<br>詳しい選び方は'+link('lexus-ux-used','UX250hの中古車を選ぶポイント')+'にまとめました。'),
      p('それから、乗り換えなら今の車の売値も大事。<br>私のUXは最終的に427万円で売却しましたが、その前の査定では業者によって提示額が大きく違いました。<br>査定と売却の時期も含めた記録は'+link('ux-resale','UXの査定・売却記録')+'に残しています。'),
      p('ディーラー下取りとの比較が気になる人は、'+link('car-sell-high','車を売る方法の体験談')+'もどうぞ。'),
      h2('まとめ｜手放したけど、買ってよかった'),
      p('後席は狭い。段ボールを積むときにはテトリス。<br>なのに運転席にいると、やっぱりこの車いいなと思う。'),
      p('小回りが利く。乗り心地がいい。そして、F SPORTの顔が好き。<br>最終的には手放しましたが、今も「買ってよかった」と思えるのは、この気持ちよさが残っているからです。'),
    ]
    dst=head+'\n\n'.join(core)+'\n\n'+footer
    if re.findall(r'<!-- wp:image.*?<!-- /wp:image -->',dst,re.S)!=imgs:raise RuntimeError("IMAGE_MARKUP_CHANGED")
    if re.findall(r'<!-- wp:table.*?<!-- /wp:table -->',dst,re.S)!=tbl:raise RuntimeError("RATING_TABLE_CHANGED")
    if not dst.endswith(footer):raise RuntimeError("FOOTER_CHANGED")
    if dst.count('<!-- wp:')!=dst.count('<!-- /wp:'):raise RuntimeError("GUTENBERG_BLOCK_BALANCE")
    for tok in ('<!-- tsurikue-internal-links:lexus-20260830:lexus-ux-review -->','<!-- tsurikue-ctn-review-funnel:20260907 -->'):
        if src.count(tok)!=dst.count(tok):raise RuntimeError("DYNAMIC_INTEGRATION_MARKER_CHANGED")
    for pattern in (r'\[blog_parts[^\]]+\]',r'https://px\.a8\.net/[^" ]+'):
        if re.findall(pattern,src)!=re.findall(pattern,dst):raise RuntimeError("AFFILIATE_MARKUP_CHANGED")
    urls=lambda body:set(re.findall(r'href="(https://tsurikue\.com/[^"]+)"',body))
    if not urls(src).issubset(urls(dst)):raise RuntimeError("EXISTING_INTERNAL_LINK_LOST")
    if dst.count('<br>')<25:raise RuntimeError("SOFT_BREAKS_MISSING")
    if dst==src:raise RuntimeError("NO_CHANGE")
    if sha(dst)!="aaefac05cc0c1930660f2730135b8f370ce6ebdf87aa282441498f768b51b431":raise RuntimeError("DRAFT_HASH_MISMATCH")
    return dst

def auth():
    u=os.environ.get("TSURIKUE_WP_USER");pw=os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not u or not pw:raise RuntimeError("MISSING_WP_CREDENTIALS")
    return "Basic "+base64.b64encode((u+":"+pw).encode()).decode()
def request(path,token,payload=None):
    headers={"Authorization":token,"Accept":"application/json","User-Agent":"tsurikue-ux-review-natural-rhythm/20261110"}
    if payload is not None:headers["Content-Type"]="application/json; charset=utf-8"
    req=urllib.request.Request(SITE+path,headers=headers,method="POST" if payload is not None else "GET",
        data=json.dumps(payload,ensure_ascii=False).encode() if payload is not None else None)
    with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)
def fetch(token):
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,featured_media,categories,author,content"})
    return request("/wp-json/wp/v2/posts/"+str(PID)+"?"+q,token)
def main(mode):
    if mode not in ("check","apply"):raise RuntimeError("EXPECTED_CHECK_OR_APPLY")
    token=auth();before=fetch(token)
    if (before["id"],before["slug"],before["status"])!=(PID,SLUG,"publish"):
        raise RuntimeError("TARGET_ID_SLUG_STATUS_CHANGED")
    original=before["content"]["raw"];updated=transform(original)
    OUT.mkdir(parents=True,exist_ok=True)
    record={"stage":"PREFLIGHT_OK","post_id":PID,"slug":SLUG,"status":before["status"],
        "old_sha":sha(original),"new_sha":sha(updated),"old_chars":len(original),"new_chars":len(updated),
        "paragraph_blocks_before":original.count('<!-- wp:paragraph -->'),
        "paragraph_blocks_after":updated.count('<!-- wp:paragraph -->'),
        "soft_breaks_before":original.count('<br>'),"soft_breaks_after":updated.count('<br>')}
    (OUT/"preflight.json").write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n")
    print("UX_REVIEW_V3_PREFLIGHT_OK",PID,sha(updated),flush=True)
    if mode=="check":return
    latest=fetch(token)
    if sha(latest["content"]["raw"])!=sha(original) or any(latest[k]!=before[k] for k in META):
        raise RuntimeError("CONCURRENT_EDIT_NO_WRITE")
    try:
        request("/wp-json/wp/v2/posts/"+str(PID),token,{"content":updated})
        saved=fetch(token)
        if saved["content"]["raw"]!=updated or any(saved[k]!=before[k] for k in META):
            raise RuntimeError("SAVED_WP_BODY_OR_META_MISMATCH")
        if "1万km以上乗ってつけたレクサスUXの評価" not in saved["content"]["rendered"]:
            raise RuntimeError("RENDERED_HEADING_MISSING")
        record["stage"]="SAVED_VERIFIED"
        (OUT/"result.json").write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n")
        print("UX_REVIEW_V3_SAVED_VERIFIED",PID,flush=True)
    except Exception:
        try:
            if fetch(token)["content"]["raw"]==updated:
                request("/wp-json/wp/v2/posts/"+str(PID),token,{"content":original})
                print("UX_REVIEW_V3_ROLLED_BACK",PID,flush=True)
        except Exception:print("UX_REVIEW_V3_ROLLBACK_UNCERTAIN",PID,flush=True)
        raise
if __name__=="__main__":
    import sys
    main(sys.argv[1] if len(sys.argv)>1 else "check")
