#!/usr/bin/env python3
"""Second-pass conversational UX review: WP preflight on PR, guarded one-post edit on main."""
from __future__ import annotations
import base64,hashlib,json,os,re,urllib.parse,urllib.request
from pathlib import Path

SITE="https://tsurikue.com"
PID=2870
SLUG="lexus-ux-review"
SOURCE_SHA="cf5c34b037f9a52c3a44aa78370421882caff5a85c822d9f8513ece293ad9499"
OUT=Path("reports/ux-review-natural-rhythm-v2-20261110")
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
      p('レクサスUX250hに1年以上、1万km以上乗りました。<br>買ったのはF SPORTの特別仕様車「Emotional Explorer」。<br>オプション込みの支払総額は約616万円。<br><strong>高っ！</strong>'),
      p('後部座席は狭いし、荷室も大きくない。<br>それでも、買ってよかったと思っています。<br>運転しやすくて、乗り心地も気持ちいい。<br>何より、あのF SPORTの顔が好きだったんです。'),
      imgs[0],
      h2('1万km以上乗ってつけたレクサスUXの評価'),
      p('まずは、UX250hを10点満点で採点した結果から。'),
      tbl[0],
      p('この点数、自分でも分かりやすいなと思います。<br>乗り心地と操作性は10点なのに、利便性は6点。<br>運転していると気持ちいいけど、後席や荷室を使うとちょっと困る。<br>そういう車でした。'),
      h2('UXに乗っていて、特に好きだったところ'),
      h3('車幅1,840mm。でも小回りは利く'),
      p('私がUXを選んだ理由のひとつが、「小さめの高級SUV」だったこと。<br>とはいえ、車幅は1,840mm。<br>数字だけ見ると、そこまで小さくないんですよね。'),
      p('でも、最小回転半径は5.2m。<br>スーパーの駐車場でも、旅行先の知らない道でも、向きを変えやすかったです。<br>街中から高速道路まで、運転のしにくさを感じることはあまりありませんでした。'),
      h3('乗り心地は10点。静かさは8点'),
      p('乗り心地は本当に気に入っていました。<br>レクサスの上位車種と比べても、私には大きな差が分からないくらい。<br>1万km以上乗っても、ここは10点のままです。'),
      p('静粛性は8点。<br>路面によってロードノイズは入るけど、会話やBGMが邪魔になるほどではありませんでした。'),
      p('その後UX300hにも試乗しました。<br>確かに進化しているけど、250hが急に古い車に感じるほどではなかったです。<br>詳しい違いは'+link('ux300h','UX300hの試乗レビュー')+'で紹介しています。'),
      h3('F SPORTのデザインが、やっぱり好き'),
      p('私はF SPORTの顔が好きで、ホワイトノーヴァガラスフレークとブラックルーフの特別仕様車を選びました。<br>1万km以上乗っても飽きなかったんだから、よほど好みだったんでしょうね。'),
      imgs[1],
      h2('後席・荷室・価格。ここは気になった'),
      p('気になったのは、この3つです。'),
      lst(['<strong>後席：</strong>大人は座れるけど、ゆったりとは言えない','<strong>荷室：</strong>普段の買い物はいいけど、大きな荷物は苦手','<strong>価格：</strong>オプション込み約616万円。NXも候補に入る金額']),
      p('特に後席。<br>「レクサスのSUVだから後ろも広いだろう」と思って乗ると、あれ？となるかもしれません。<br>荷室も、2人の旅行なら使えましたが、大きな荷物を積むのは得意じゃなかったです。'),
      p('そして616万円。<br>ここまで出すならNXも気になります。<br>それでもUXを選んだのは、広さよりも、運転のしやすさや乗り心地、デザインが気に入っていたから。'),
      p('もっと細かい不満は'+link('ux-koukai','UXを616万円で買って感じた後悔と満足')+'で書いています。'),
      '<!-- tsurikue-internal-links:lexus-20260830:lexus-ux-review -->',
      '<p><!-- tsurikue-ctn-review-funnel:20260907 --></p>',
      h2('レクサスUXは、どんな人に向いている？'),
      p('私なら、こんな使い方をする人にすすめます。'),
      lst(['普段は1〜2人で乗ることが多い','街乗りもドライブも、運転を楽しみたい','後席や荷室の広さより、乗り心地やデザインを優先したい']),
      p('私はUXで山陰、角島、淡路島と、あちこち出かけました。<br>目的地だけじゃなくて、そこまで走る時間も楽しかったんです。'),
      p('逆に、大人4〜5人で遠出する機会が多いなら、後部座席と荷室は実車で確かめた方がいいです。<br>広さが必要なら、NXなどもう少し大きなSUVも見てみてください。'),
      imgs[2],
      h2('今から買うなら、私は中古のUX250hを探す'),
      p('私はUXを新車で買いました。<br>でも、今もう一度選ぶなら、まず中古のUX250hを探します。<br>616万円出した身としては、ちょっと複雑ですけどね。'),
      p('250hの乗り心地や運転のしやすさには十分満足していました。<br>UX300hにも試乗したけど、250hが急に古く感じるほどではなかったです。'),
      p('新しい装備や保証を優先するなら新車。<br>予算も考えて選ぶなら、中古の250hも面白いと思います。<br>詳しい選び方は'+link('lexus-ux-used','UX250hの中古車を選ぶポイント')+'にまとめました。'),
      p('それから、乗り換えなら今の車の売値も大事。<br>私のUXは最終的に427万円で売却しましたが、その前の査定では業者によって提示額が大きく違いました。<br>査定と売却の時期も含めた記録は'+link('ux-resale','UXの査定・売却記録')+'に残しています。'),
      p('ディーラー下取りとの比較が気になる人は、'+link('car-sell-high','車を売る方法の体験談')+'もどうぞ。'),
      h2('まとめ｜手放したけど、買ってよかった'),
      p('UXは、たくさん乗せたり積んだりするのが得意な車ではありません。<br>でも、私が気に入っていたのはそこじゃないんです。'),
      p('小回りが利くし、乗り心地もいい。<br>何よりF SPORTのデザインが好き。<br>最終的には手放しましたが、1万km以上乗った今でも、買ってよかったと思っています。')
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
    print("UX_REVIEW_V2_PREFLIGHT_OK",PID,sha(updated),flush=True)
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
        print("UX_REVIEW_V2_SAVED_VERIFIED",PID,flush=True)
    except Exception:
        try:
            if fetch(token)["content"]["raw"]==updated:
                request("/wp-json/wp/v2/posts/"+str(PID),token,{"content":original})
                print("UX_REVIEW_V2_ROLLED_BACK",PID,flush=True)
        except Exception:print("UX_REVIEW_V2_ROLLBACK_UNCERTAIN",PID,flush=True)
        raise
if __name__=="__main__":
    import sys
    main(sys.argv[1] if len(sys.argv)>1 else "check")
