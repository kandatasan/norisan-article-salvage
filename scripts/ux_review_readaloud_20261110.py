#!/usr/bin/env python3
"""Rewrite only the public UX review using its verified Gutenberg source.

PR: WordPress authenticated read-only preflight.
Main push: guarded content-only publish with readback and rollback.
Source: user-provided WordPress export dated 2026-11-09, post 2870.
"""
import base64, hashlib, json, os, re, urllib.request, urllib.parse
from pathlib import Path

SITE="https://tsurikue.com"
PID=2870
SLUG="lexus-ux-review"
BASE_SHA="108be32ec4b3545f35a30f62784dba1c3ebd1f4e2f97fbe9471e56118b56557a"
OUT=Path("reports/ux-review-readaloud-20261110")
FIELDS=("id","slug","status","title","featured_media","categories","author")
def sha(s): return hashlib.sha256(s.encode("utf-8")).hexdigest()
def para(t): return '<!-- wp:paragraph -->\n<p>'+t+'</p>\n<!-- /wp:paragraph -->'
def h2(t): return '<!-- wp:heading -->\n<h2 class="wp-block-heading">'+t+'</h2>\n<!-- /wp:heading -->'
def h3(t): return '<!-- wp:heading {"level":3} -->\n<h3 class="wp-block-heading">'+t+'</h3>\n<!-- /wp:heading -->'
def link(slug,t): return '<a href="https://tsurikue.com/'+slug+'/">'+t+'</a>'
def items(rows):
    return '<!-- wp:list {"className":"wp-block-list"} -->\n<ul class="wp-block-list">' + '\n'.join(
        '<!-- wp:list-item -->\n<li>'+x+'</li>\n<!-- /wp:list-item -->' for x in rows
    ) + '</ul>\n<!-- /wp:list -->'

def transform(original):
    # Fail closed if any article edit happened after the user's export.
    if sha(original)!=BASE_SHA: raise RuntimeError("LIVE_CONTENT_DIFFERS_FROM_20261109_EXPORT_NO_WRITE")
    st=original.index('<!-- wp:paragraph -->')
    marker='<p><!-- tq-lexus-related-cards:v1:lexus-ux-review --></p>'
    if original.count(marker)!=1: raise RuntimeError("RELATED_CARDS_ANCHOR_CHANGED")
    ed=original.index(marker)
    header,footer=original[:st],original[ed:]
    imgs=re.findall(r'<!-- wp:image.*?<!-- /wp:image -->',original,re.S)
    tbl=re.findall(r'<!-- wp:table.*?<!-- /wp:table -->',original,re.S)
    if len(imgs)!=3 or len(tbl)!=1:raise RuntimeError("PHOTO_TABLE_BASELINE_CHANGED")
    core=[
      para('レクサスUXって、実際に乗るとどうなのか。<br>1年以上、1万km以上乗った元オーナーの感想は、<strong>「買ってよかった。でも、誰にでもすすめられる車ではない」</strong>です。'),
      para('私が買ったのは、UX250h F SPORTの特別仕様車「Emotional Explorer」。オプションや諸費用を含めて約616万円でした。'),
      para('高っ！'),
      para('それでも満足していたのは、運転の気持ちよさと、毎回見ても飽きなかったデザイン。<br>一方で、後席や荷室には割り切りが必要でした。良かったところも不満も、乗っていたときの感覚で振り返ります。'),
      imgs[0],
      h2('1万km以上乗ったレクサスUXの総合評価'),
      para('UX250hを10点満点で採点すると、こうなりました。'),
      tbl[0],
      para('乗り心地と操作性は10点。利便性は6点。<br>運転している時間は大好きだけど、人や荷物をたくさん乗せるのは得意じゃない。私にとってのUXは、そんな車でした。'),
      h2('乗っていて気に入った3つのところ'),
      h3('小回りが利いて、知らない道でも扱いやすい'),
      para('UXを選んだ理由のひとつは、<strong>「小さめの高級SUV」</strong>だったこと。<br>車幅は1,840mmあるので、数字だけ見れば決して細くありません。それでも最小回転半径5.2mのおかげで、駐車場や旅行先の道でも向きを変えやすかったです。'),
      para('街中を走っても、高速道路へ出ても、運転しにくいと感じることは少なかった。アクセルを踏んだときの加速も好みでした。'),
      h3('乗り心地は10点。静かさは8点'),
      para('乗り心地は特に気に入っていました。レクサスの上位車種と比べても、私には大きな差を感じないほど心地よく、1万km以上乗っても評価は10点のまま。'),
      para('静粛性は8点です。<br>路面によってロードノイズは入るけれど、会話やBGMの邪魔になるほどではありませんでした。ここは10点満点とはいかなかったものの、不満を感じるほどでもなかったです。'),
      para('後にUX300hにも試乗しました。進化は感じたものの、乗り慣れた250hが急に古く感じるほどではありませんでした。違いは'+link('ux300h','UX300hの試乗レビュー')+'で詳しく書いています。'),
      h3('やっぱりF SPORTの顔が好き'),
      para('そして、見た目。<br>私はF SPORTの顔が好きで、ホワイトノーヴァガラスフレークとブラックルーフの特別仕様車を選びました。1万km以上走っても、飽きなかったデザインです。'),
      imgs[1],
      h2('後席・荷室・価格は、正直気になった'),
      para('乗っていて不満だったのは、この3つ。'),
      items(['後部座席は、大人が座れるけれど広くはない','荷室は普段使いなら十分でも、大きな荷物には弱い','オプション込み約616万円。装備を選ぶとNXも気になる価格になる']),
      para('特に後部座席は、「レクサスのSUVだから後ろもゆったり」と思って乗ると、想像よりコンパクトに感じるはず。<br>荷室も買い物や2人での旅行には使えましたが、大きな荷物を頻繁に積む人にはおすすめしにくいです。'),
      para('そして約616万円という金額。<br>「その値段ならNXも見えてくるよね」と思うのは、私も同じです。広さを買う車というより、<strong>扱いやすさや乗り心地、好きなデザインにお金を払う車</strong>だと感じました。'),
      para('荷室や後席、細かい不満については'+link('ux-koukai','616万円で買って感じたUXの後悔と満足')+'にまとめています。'),
      '<!-- tsurikue-internal-links:lexus-20260830:lexus-ux-review -->',
      '<p><!-- tsurikue-ctn-review-funnel:20260907 --></p>',
      h2('レクサスUXが合うのは、こんな使い方'),
      para('1万km以上乗って感じたのは、<strong>普段1〜2人で乗って、ドライブも楽しみたい人</strong>には相性がいいということ。'),
      items(['街乗りから高速まで、運転そのものを楽しみたい','大きすぎるSUVはいらないけれど、質感や乗り心地にはこだわりたい','F SPORTをはじめ、UXのデザインが気に入っている']),
      para('私はUXで山陰、角島、淡路島などへ出かけました。<br>目的地だけでなく、そこまで運転していく時間も楽しめた車です。'),
      para('逆に、大人4〜5人で遠出することが多いなら、後席と荷室は必ず実車で確かめたいところ。広さを優先する人は、NXなど一回り大きいSUVと比べた方が納得して選べると思います。'),
      imgs[2],
      h2('今から私がUXを買うなら？'),
      para('私は新車で買いましたが、今もう一度選ぶなら、まず中古のUX250hを探します。'),
      para('UX250hでも走りと乗り心地には十分満足していましたし、試乗したUX300hにも「250hとは別物だ」と思うほどの差は感じませんでした。<br>新車の装備や保証が必要ならUX300h。一方で予算とのバランスを考えるなら、中古のUX250hも魅力的です。'),
      para('中古の選び方は'+link('lexus-ux-used','UX250hの中古車を選ぶポイント')+'で詳しく紹介しています。'),
      para('それから、乗り換えで忘れたくないのが今の車の売値。<br>私はUXを最終的に427万円で手放しましたが、それ以前の査定では提示額に大きな差がありました。時期の違う査定額を混ぜずに、'+link('ux-resale','UXの査定から売却までの記録')+'に残しています。'),
      para('乗り換え費用を考えるなら、'+link('car-sell-high','ディーラー下取りと買取査定を比べた体験談')+'も参考にどうぞ。'),
      h2('まとめ｜広さは割り切る。でも、乗っていた時間が好きだった'),
      para('運転していて気持ちいい。見た目も好き。<br>反対に、後ろに人を乗せたり、大きな荷物を積んだりする場面では弱さが出る。UXは長所と短所がはっきりしたSUVでした。'),
      para('私は最終的にUXを手放しました。<br>それでも、山陰や角島まで走った時間を思い出すと、<strong>買ってよかった</strong>という気持ちは変わりません。'),
    ]
    new=header+'\n\n'.join(core)+'\n\n'+footer
    if [x for x in re.findall(r'<!-- wp:image.*?<!-- /wp:image -->',new,re.S)]!=imgs: raise RuntimeError("IMAGES_CHANGED")
    if re.findall(r'<!-- wp:table.*?<!-- /wp:table -->',new,re.S)!=tbl: raise RuntimeError("RATING_TABLE_CHANGED")
    if footer not in new or not new.endswith(footer):raise RuntimeError("RELATED_SECTION_CHANGED")
    if new.count('<!-- wp:')!=new.count('<!-- /wp:'):raise RuntimeError("BLOCKS_UNBALANCED")
    if sorted(set(re.findall(r'href="(https://tsurikue.com/[^"]+)"',original))) != sorted(set(re.findall(r'href="(https://tsurikue.com/[^"]+)"',original))&set(re.findall(r'href="(https://tsurikue.com/[^"]+)"',new))):
        raise RuntimeError("EXISTING_INTERNAL_LINK_LOST")
    for tag in ('<!-- tsurikue-internal-links:lexus-20260830:lexus-ux-review -->','<!-- tsurikue-ctn-review-funnel:20260907 -->'):
        if original.count(tag)!=new.count(tag):raise RuntimeError("CONTEXT_MARKER_CHANGED")
    for pat in (r'\[blog_parts[^\]]+\]',r'https://px\.a8\.net/[^" ]+'):
        if re.findall(pat,original)!=re.findall(pat,new):raise RuntimeError("AFFILIATE_MARKUP_CHANGED")
    return new

def api(path,auth,payload=None):
    headers={"Authorization":auth,"Accept":"application/json","User-Agent":"tsurikue-ux-review-readaloud/20261110"}
    if payload is not None:headers["Content-Type"]="application/json; charset=utf-8"
    request=urllib.request.Request(SITE+path,headers=headers,method="POST" if payload is not None else "GET",
      data=json.dumps(payload,ensure_ascii=False).encode("utf-8") if payload is not None else None)
    with urllib.request.urlopen(request,timeout=60) as r:return json.load(r)
def getpost(auth):
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,featured_media,categories,author,content"})
    return api("/wp-json/wp/v2/posts/"+str(PID)+"?"+q,auth)
def main(mode):
    if mode not in ("check","apply"):raise RuntimeError("MODE_CHECK_OR_APPLY_REQUIRED")
    user,pw=os.environ.get("TSURIKUE_WP_USER"),os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not pw:raise RuntimeError("WP_SECRETS_MISSING")
    token="Basic "+base64.b64encode((user+":"+pw).encode()).decode()
    before=getpost(token)
    if (before["id"],before["slug"],before["status"])!=(PID,SLUG,"publish"):raise RuntimeError("WP_POST_IDENTITY_STATUS_CHANGED")
    old=before["content"]["raw"]
    revised=transform(old)
    OUT.mkdir(parents=True,exist_ok=True)
    record={"stage":"PREFLIGHT_OK","post_id":PID,"slug":SLUG,"status":before["status"],
            "old_sha256":sha(old),"new_sha256":sha(revised),"old_chars":len(old),"new_chars":len(revised),
            "media_ids":re.findall(r'class="wp-image-([0-9]+)"',old),
            "changed":"content only"}
    (OUT/"preflight.json").write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n")
    print("UX_REVIEW_PREFLIGHT_OK",PID,sha(old),sha(revised),flush=True)
    if mode=="check":return
    before2=getpost(token)
    if sha(before2["content"]["raw"])!=sha(old) or any(before2[k]!=before[k] for k in FIELDS):
        raise RuntimeError("CONCURRENT_EDIT_STOP_NO_WRITE")
    try:
        api("/wp-json/wp/v2/posts/"+str(PID),token,{"content":revised})
        after=getpost(token)
        if after["content"]["raw"]!=revised or any(after[k]!=before[k] for k in FIELDS):
            raise RuntimeError("SAVED_CONTENT_OR_POST_META_MISMATCH")
        if "1万km以上乗ったレクサスUXの総合評価" not in after["content"]["rendered"]:
            raise RuntimeError("RENDERED_HEADING_MISSING")
        record["stage"]="PUBLISHED_SAVED_VERIFIED"
        (OUT/"result.json").write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n")
        print("UX_REVIEW_PUBLISHED_AND_VERIFIED",PID,flush=True)
    except Exception:
        try:
            latest=getpost(token)
            if latest["content"]["raw"]==revised:
                api("/wp-json/wp/v2/posts/"+str(PID),token,{"content":old})
                print("UX_REVIEW_ROLLED_BACK",PID,flush=True)
        except Exception:print("UX_REVIEW_ROLLBACK_CHECK_FAILED",PID,flush=True)
        raise

if __name__=="__main__":
    import sys
    main(sys.argv[1] if len(sys.argv)>1 else "check")
