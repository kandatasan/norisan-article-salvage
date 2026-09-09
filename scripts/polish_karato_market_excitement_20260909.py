#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, os, re, urllib.parse, urllib.request

SITE='https://tsurikue.com'
UA='tsurikue-polish-karato-market-20260909/1.0'
POST_ID=3633
SLUG='karato-market'
EXPECTED_CURRENT_SHA='460725557536ec5baffb134ba818214a6dbdcdcfccabc29aa88bf7be3e99b2ea'
MARKER='<!-- karato-polish:20260909-excitement-v1 -->'


def auth():
    user=os.environ.get('TSURIKUE_WP_USER'); pw=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
    if not user or not pw: raise SystemExit('BLOCKED_MISSING_SECRETS')
    return 'Basic '+base64.b64encode(f'{user}:{pw}'.encode()).decode()


def req(url, method='GET', payload=None, timeout=60):
    headers={'Authorization':auth(),'Accept':'application/json','User-Agent':UA}; data=None
    if payload is not None:
        data=json.dumps(payload,ensure_ascii=False).encode(); headers['Content-Type']='application/json; charset=utf-8'
    r=urllib.request.Request(url,data=data,headers=headers,method=method)
    with urllib.request.urlopen(r,timeout=timeout) as resp:
        return json.loads(resp.read().decode()),dict(resp.headers)


def raw(row,key):
    v=row.get(key) or {}
    return (v.get('raw') or v.get('rendered') or '') if isinstance(v,dict) else str(v)


def count_published(endpoint):
    q=urllib.parse.urlencode({'status':'publish','per_page':1,'_fields':'id'})
    _,h=req(f'{SITE}/wp-json/wp/v2/{endpoint}?{q}',timeout=45)
    return int(h.get('X-WP-Total','0'))


def public_counts():
    p=count_published('posts'); g=count_published('pages')
    return {'published_posts':p,'published_pages':g,'published_total':p+g}


def replace_once(text, old, new, label):
    n=text.count(old)
    if n!=1: raise RuntimeError(f'{label}: expected exactly 1 match, got {n}')
    return text.replace(old,new,1)


def polish(content):
    content=MARKER+'\n'+content

    reps=[
      (
        '<p>私なら、まず<strong><span class="swl-marker mark_orange">一本アナゴとマグロの脳天</span></strong>をおすすめします。</p>',
        '<p>私なら、まず<strong><span class="swl-marker mark_orange">一本アナゴとマグロの脳天</span></strong>を探します。<br>寿司がずらっと並ぶ景色を見た瞬間から、もう「どれ食べる？」が始まるんですよ。</p>',
        'intro recommendation'),
      (
        '<p>唐戸市場は寿司だけじゃありません。<br>ふぐ、サザエ、アワビ、海鮮丼。売り場を歩いていると、高級魚のクエまで並んでいました。</p>',
        '<p>しかも、唐戸市場は寿司だけじゃありません。<br>ふぐ、サザエ、アワビ、海鮮丼。売り場を歩くたびに次の海鮮が出てきて、つい立ち止まる。さらに<strong>高級魚のクエまで</strong>並んでいました。</p>',
        'intro variety'),
      (
        '<p>魚好きなら、食べる前から楽しい市場です。</p>',
        '<p><strong>魚好きなら、まだ一口も食べていないのに楽しい。</strong><br>「次は何が出てくる？」と売り場を歩くだけで、ちょっとした宝探しみたいでした。</p>',
        'intro excitement'),
      (
        '<figure class="wp-block-image size-large"><img src="https://tsurikue.com/wp-content/uploads/2026/05/img_2101.jpg" alt="唐戸市場の大きなクジラのオブジェ" class="wp-image-1003"/><figcaption class="wp-element-caption">入って早々、でかい。市場というより観光スポット感もあります。</figcaption></figure>\n<!-- /wp:image -->\n\n',
        '',
        'remove misplaced whale image'),
      (
        '<p>まず食べてほしいのがアナゴ。</p>',
        '<p>まず目に飛び込んできたのがアナゴ。<br>寿司の列の中でも、あの長さは反則です。</p>',
        'anago lead'),
      (
        '<figure class="wp-block-image size-large"><img src="https://tsurikue.com/wp-content/uploads/2026/05/img_2322.jpg" alt="唐戸市場で買った一本アナゴとマグロなどの寿司" class="wp-image-1111"/><figcaption class="wp-element-caption">手前のアナゴがこの存在感。ほかの寿司と一緒に買って外で食べました。</figcaption></figure>',
        '<figure class="wp-block-image size-large"><img src="https://tsurikue.com/wp-content/uploads/2026/05/img_2322.jpg" alt="唐戸市場で買った一本アナゴとマグロの脳天などの寿司" class="wp-image-1111"/><figcaption class="wp-element-caption">手前が一本アナゴ。そして<strong>左上のマグロが脳天</strong>です。気になった寿司を一緒に買って外で食べました。</figcaption></figure>',
        'brain tuna photo caption'),
      (
        '<p>脂の甘さとマグロらしい味の両方が来る。<br>名前に抵抗がなければ、これは食べてみてほしい。</p>',
        '<p>脂の甘さとマグロらしい味の両方が来る。<br>さっきのアナゴの写真で<strong>左上に写っているのが、このマグロの脳天</strong>です。名前に抵抗がなければ、これはぜひ試してほしい。</p>',
        'brain tuna photo callout'),
      (
        '<figure class="wp-block-image size-large"><img src="https://tsurikue.com/wp-content/uploads/2026/05/img_2079.jpg" alt="唐戸市場で選んだ寿司" class="wp-image-981"/><figcaption class="wp-element-caption">気になるものを少しずつ選べるのが楽しい。</figcaption></figure>\n<!-- /wp:image -->',
        '<figure class="wp-block-image size-large"><img src="https://tsurikue.com/wp-content/uploads/2026/05/img_2079.jpg" alt="唐戸市場で少しずつ選んだ寿司と左端のクエ" class="wp-image-981"/><figcaption class="wp-element-caption">気になるものを少しずつ。<strong>左端は超高級魚のクエ</strong>です。こうやって一貫ずつなら、クエまで気軽に試せるのがうれしい。</figcaption></figure>\n<!-- /wp:image -->\n\n<!-- wp:paragraph -->\n<p>高級魚って一匹やコースで考えると身構えますが、寿司なら「クエも一個いってみよう」ができる。<br><strong>少しずついろんな魚を冒険できる</strong>のも、唐戸市場のワクワクするところでした。</p>\n<!-- /wp:paragraph -->',
        'kue photo caption'),
      (
        '<p>唐戸市場は、買うものを決めて一直線に歩くより、まず売り場を見て回るのが面白いです。</p>',
        '<p>唐戸市場は、買うものを決めて一直線に歩くより、<strong>まず一周して「何がおる？」と見て回るのが面白い</strong>です。<br>最初の店で全部決めるの、たぶん無理です。</p>',
        'market walk'),
      (
        '<p>活サザエが並んでいたり。</p>',
        '<p>活サザエがずらっと並んでいたり。</p>',
        'sazae excitement'),
      (
        '<p>アワビもいる。</p>',
        '<p>その隣を見れば、アワビもいる。</p>',
        'awabi excitement'),
      (
        '<p>ふぐ刺しや海鮮丼もある。</p>',
        '<p>さらに、ふぐ刺しや海鮮丼まである。<br>「寿司だけのつもりだったのに」がどんどん崩れていきます。</p>',
        'fugu excitement'),
      (
        '<p>そして、売り場には<strong>高級魚のクエまで。</strong></p>',
        '<p>そして、売り場には<strong>高級魚のクエまで。</strong><br>さっきの寿司写真の左端がそのクエです。</p>',
        'kue callout'),
      (
        '<p>寿司を選んだら、外へ。</p>',
        '<p>寿司を選んだら、今度は外へ。<br>ここから「買ったやつ全部広げる時間」です。</p>',
        'outside lead'),
      (
        '<p>好きな寿司をあれこれ買って、その場で食べる。</p>',
        '<p>好きな寿司をあれこれ買って、その場で食べる。<br>一皿ずつ注文する店とは違って、<strong>自分で集めた海鮮オールスターを並べる感じ</strong>が楽しい。</p>',
        'outside feast'),
      (
        '<p>海のすぐそばなので、天気がいい日は外で食べるのも気持ちいいです。</p>',
        '<p>しかも海のすぐそば。<br>天気がいい日に海を見ながら食べると、ただの昼ごはんより一段テンションが上がります。</p>',
        'seaside excitement'),
      (
        '<p>海鮮をたっぷり食べたあとは、巣蜜つきの蜂蜜ソフト。</p>',
        '<p>海鮮をたっぷり食べたあとは、今度は甘いもの。<br>巣蜜がそのまま乗った蜂蜜ソフトを見つけました。</p>',
        'softcream lead'),
      (
        '<p>これも美味しい。満足度も高かったです。</p>',
        '<p>海鮮のあとに甘いもの。これは強い。<br>蜂蜜の甘さもあって、満足度はかなり高かったです。</p>',
        'softcream excitement'),
      (
        '<p>唐戸市場で食べる。<br>そのまま海響館へ行く。<br>遊び終わったら車へ戻って、ササッと次の遊び場へ。</p>',
        '<p>唐戸市場で海鮮を食べる。<br>そのまま海響館へ行く。<br>遊び終わったら車へ戻って、ササッと次の遊び場へ。</p>',
        'route wording'),
      (
        '<p>これが楽でした。</p>',
        '<p><strong>食べた勢いのまま次の遊びへ行ける。</strong><br>この流れがかなり楽でした。</p>',
        'route excitement'),
      (
        '<p>海響館はすぐ近く。<br>私たちも唐戸市場で食べたあと、そのまま海響館へ行ってしっかり遊びました。</p>',
        '<p>海響館はすぐ近く。<br>私たちも唐戸市場で食べたあと、そのまま海響館へ。お腹いっぱいの次は水族館です。</p>\n<!-- /wp:paragraph -->\n\n<!-- wp:image {"id":1003,"sizeSlug":"large","linkDestination":"none"} -->\n<figure class="wp-block-image size-large"><img src="https://tsurikue.com/wp-content/uploads/2026/05/img_2101.jpg" alt="海響館で撮った大きなクジラ" class="wp-image-1003"/><figcaption class="wp-element-caption">このクジラは唐戸市場ではなく<strong>海響館で撮った写真</strong>です。市場からそのまま遊びに行ける距離感がうれしい。</figcaption></figure>\n<!-- /wp:image -->',
        'move whale to aquarium'),
      (
        '<p>さらに車で山口を遊ぶなら、角島までつなげても楽しい。</p>',
        '<p>ここで終わりでも十分満足ですが、車ならまだ先へ行けます。<br>さらに山口を遊ぶなら、角島までつなげるのも楽しい。</p>',
        'drive onward'),
      (
        '<p>唐戸市場は、寿司を食べる場所というより<strong>「何を食べよう」と迷うところから楽しい市場</strong>でした。</p>',
        '<p>唐戸市場は、寿司を食べる場所というより<strong>「何を食べよう！」と迷い始めた瞬間から楽しい市場</strong>でした。</p>',
        'summary excitement'),
      (
        '<p>私なら、一本アナゴとマグロの脳天。<br>この2つはまた食べたいです。</p>',
        '<p>私なら、まず一本アナゴとマグロの脳天。<br>そして余裕があればクエも一貫。<strong>次に行っても、この辺から攻めます。</strong></p>',
        'summary picks'),
      (
        '<p>ふぐやサザエ、アワビ、クエまで眺めて、好きな寿司を買って外で食べる。<br>最後に巣蜜つき蜂蜜ソフトを食べて、「巣って溶けないのね」となる。</p>',
        '<p>ふぐやサザエ、アワビを眺めて、クエみたいな高級魚も一貫ずつ試して、好きな寿司を抱えて外へ。<br>最後に巣蜜つき蜂蜜ソフトを食べて、「巣って溶けないのね」となる。</p>',
        'summary journey'),
      (
        '<p><strong>食べて、遊んで、ササッと次へ。</strong><br>車で下関を回るなら、この流れおすすめです。</p>',
        '<p><strong>食べて、驚いて、遊んで、ササッと次へ。</strong><br>車で下関を回るなら、唐戸市場を起点にこの流れで遊ぶの、おすすめです。</p>',
        'summary finish'),
    ]
    for old,new,label in reps:
        content=replace_once(content,old,new,label)
    return content


def main():
    q=urllib.parse.urlencode({'context':'edit','_fields':'id,slug,status,title,content,featured_media,categories,tags'})
    before,_=req(f'{SITE}/wp-json/wp/v2/posts/{POST_ID}?{q}',timeout=60)
    if before.get('id')!=POST_ID or before.get('slug')!=SLUG or before.get('status')!='draft':
        raise RuntimeError('target identity/status mismatch')
    current=raw(before,'content')
    if MARKER in current:
        action='ALREADY_UP_TO_DATE'; updated=current
    else:
        current_sha=hashlib.sha256(current.encode()).hexdigest()
        if current_sha!=EXPECTED_CURRENT_SHA:
            raise RuntimeError(f'current content sha mismatch: {current_sha}')
        updated=polish(current)
        if updated.count('wp-image-1003')!=1: raise RuntimeError('whale image count mismatch')
        if '唐戸市場の大きなクジラ' in updated: raise RuntimeError('stale whale caption remains')
        for phrase in ['左上のマグロが脳天','左端は超高級魚のクエ','少しずついろんな魚を冒険できる','海響館で撮った写真','食べて、驚いて、遊んで']:
            if phrase not in updated: raise RuntimeError(f'missing polished phrase: {phrase}')
        before_counts=public_counts()
        payload={'content':updated,'status':'draft'}
        out,_=req(f'{SITE}/wp-json/wp/v2/posts/{POST_ID}',method='POST',payload=payload,timeout=90)
        if out.get('id')!=POST_ID or out.get('slug')!=SLUG or out.get('status')!='draft': raise RuntimeError('update response mismatch')
        after_counts=public_counts()
        if before_counts!=after_counts: raise RuntimeError(f'published counts changed: {before_counts} -> {after_counts}')
        action='UPDATE'
    after,_=req(f'{SITE}/wp-json/wp/v2/posts/{POST_ID}?{q}',timeout=60)
    final=raw(after,'content')
    if after.get('status')!='draft' or after.get('slug')!=SLUG or MARKER not in final: raise RuntimeError('post-update verification failed')
    if final.count('wp-image-1003')!=1 or '唐戸市場の大きなクジラ' in final: raise RuntimeError('whale image placement verification failed')
    report={
      'result':'SUCCESS','action':action,'post_id':POST_ID,'slug':SLUG,'status':'draft',
      'whale_image_context':'海響館','brain_tuna_photo_callout':'left-upper','kue_photo_callout':'left-edge',
      'public_counts_now':public_counts(),'publish_count':0,
      'content_sha256':hashlib.sha256(final.encode()).hexdigest()
    }
    print('# Karato Market excitement polish')
    for k,v in report.items(): print(f'- {k}: **{v}**')

if __name__=='__main__': main()
