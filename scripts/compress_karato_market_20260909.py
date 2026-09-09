#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, os, re, urllib.parse, urllib.request

SITE='https://tsurikue.com'
POST_ID=3633
SLUG='karato-market'
EXPECTED_SHA='3c5dd696ff9ea7f3c774ca0361ceaf7c0b192c69de9fd0bc49af9ab07ab52c16'
UA='tsurikue-compress-karato-20260909/1.0'
TOKEN=re.compile(r'<!--\s+/?wp:[\s\S]*?-->')
OPEN=re.compile(r'<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->')
CLOSE=re.compile(r'<!--\s+/wp:([\w\-/]+)\s+-->')


def auth():
    user=os.environ.get('TSURIKUE_WP_USER'); pw=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
    if not user or not pw:
        raise SystemExit('BLOCKED_MISSING_SECRETS')
    return 'Basic '+base64.b64encode(f'{user}:{pw}'.encode()).decode()


def req(url, method='GET', payload=None, timeout=60):
    headers={'Authorization':auth(),'Accept':'application/json','User-Agent':UA}
    data=None
    if payload is not None:
        data=json.dumps(payload,ensure_ascii=False).encode('utf-8')
        headers['Content-Type']='application/json; charset=utf-8'
    request=urllib.request.Request(url,data=data,headers=headers,method=method)
    with urllib.request.urlopen(request,timeout=timeout) as response:
        return json.loads(response.read().decode('utf-8')),dict(response.headers)


def raw(row,key):
    v=row.get(key) or {}
    if isinstance(v,dict):
        return v.get('raw') or v.get('rendered') or ''
    return str(v)


def count_published(endpoint):
    q=urllib.parse.urlencode({'status':'publish','per_page':1,'_fields':'id'})
    _,headers=req(f'{SITE}/wp-json/wp/v2/{endpoint}?{q}',timeout=45)
    return int(headers.get('X-WP-Total','0'))


def public_counts():
    posts=count_published('posts'); pages=count_published('pages')
    return {'posts':posts,'pages':pages,'total':posts+pages}


def gb_problems(text):
    stack=[]; bad=0
    for match in TOKEN.finditer(text):
        token=match.group(0); o=OPEN.fullmatch(token); c=CLOSE.fullmatch(token)
        if o:
            if not o.group(2):
                stack.append(o.group(1))
        elif c:
            if not stack or stack[-1]!=c.group(1):
                bad+=1
            else:
                stack.pop()
    return bad+len(stack)


def replace_once(text, old, new, label):
    n=text.count(old)
    if n!=1:
        raise RuntimeError(f'{label}: expected exactly 1 match, got {n}')
    return text.replace(old,new,1)


def compress(content):
    # 1) Intro: answer fast, then stop re-explaining the same recommendations before H2.
    old='''<!-- wp:paragraph -->
<p>「唐戸市場に行くけど、何を食べればいい？」<br>「寿司がいっぱいありすぎて、結局どれを選べばいい？」</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>私なら、まず<strong><span class="swl-marker mark_orange">一本アナゴとマグロの脳天</span></strong>を探します。<br>寿司がずらっと並ぶ景色を見た瞬間から、もう「どれ食べる？」が始まるんですよ。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>アナゴは丸ごと一本。食べ応えも味も最高。<br>マグロの脳天は脂たっぷりでトロトロなのに、赤身みたいにマグロの風味がしっかりあります。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>「脳天」という名前で一瞬ひるむかもしれませんが、脳みそではありません。頭の肉です。<br>名前に抵抗がなければ、ぜひ食べてほしい。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>しかも、唐戸市場は寿司だけじゃありません。<br>ふぐ、サザエ、アワビ、海鮮丼。売り場を歩くたびに次の海鮮が出てきて、つい立ち止まる。さらに<strong>高級魚のクエまで</strong>並んでいました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>魚好きなら、まだ一口も食べていないのに楽しい。</strong><br>「次は何が出てくる？」と売り場を歩くだけで、ちょっとした宝探しみたいでした。</p>
<!-- /wp:paragraph -->'''
    new='''<!-- wp:paragraph -->
<p>「唐戸市場に行くけど、何を食べればいい？」<br>「寿司がいっぱいありすぎて、結局どれを選べばいい？」</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>私なら、まず<strong><span class="swl-marker mark_orange">一本アナゴとマグロの脳天</span></strong>。<br>次に行っても、この2つは探します。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ただ、唐戸市場は決め打ちで行ってもすぐ崩れる。<br>売り場を歩くたびに<strong>「これも食べたい！」</strong>が増える。魚好きなら、食べる前からもう楽しい。</p>
<!-- /wp:paragraph -->'''
    content=replace_once(content,old,new,'intro compression')

    content=replace_once(content,
      '寿司がずらっと並ぶ売り場。<br>ここで目に入ったのがアナゴとマグロの脳天でした。',
      '手前に一本アナゴ。奥にはマグロの脳天。',
      'first sushi caption')

    # 2) Keep the user's H2/H3 voice; remove the sentence that explains what the next line already shows.
    content=replace_once(content,
      '<p><strong>一本が丸ごとドン。</strong><br>見た目のインパクトだけでは終わりません。</p>',
      '<p><strong>一本が丸ごとドン。</strong></p>',
      'anago overexplain')
    content=replace_once(content,
      '<p>しっかり食べ応えがあって、味も最高。<br>唐戸市場へ行くと寿司が多すぎて迷いますが、私は次に行っても絶対にアナゴを探します。</p>',
      '<p>しっかり食べ応えがあって、味も最高。<br>次に行っても、まずアナゴを探します。</p>',
      'anago close')

    # 3) Maguro nouten: one explanation, one taste reaction. Caption already identifies where it is in the photo.
    old='''<!-- wp:paragraph -->
<p>もうひとつ、ぜひ食べてほしいのが<strong>マグロの脳天</strong>です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>名前だけ見ると、ちょっと怖い。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>でも脳みそではなく、マグロの頭の部分の肉です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>食べると脂たっぷり、トロトロ。<br>なのに脂の甘さだけで終わらず、赤身みたいに<strong>「マグロを食べている」風味がグッと来る</strong>んです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>脂の甘さとマグロらしい味の両方が来る。<br>さっきのアナゴの写真で<strong>左上に写っているのが、このマグロの脳天</strong>です。名前に抵抗がなければ、これはぜひ試してほしい。</p>
<!-- /wp:paragraph -->'''
    new='''<!-- wp:paragraph -->
<p>もうひとつは<strong>マグロの脳天</strong>。<br>名前だけ見ると、ちょっと怖い。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>でも脳みそじゃありません。<strong>頭の肉です。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>脂たっぷりでトロトロ。<br>なのに赤身みたいに<strong>「マグロを食べてる！」という風味がグッと来る。</strong>名前に抵抗がなければ、これは食べてほしい。</p>
<!-- /wp:paragraph -->'''
    content=replace_once(content,old,new,'nouten compression')

    content=replace_once(content,
      '少しずつ選んだ寿司。<strong>左端がクエ</strong>です。超高級魚でも一貫なら「せっかくだし食べてみよう」ができる。',
      '<strong>左端がクエ。</strong>超高級魚も一貫なら手が出しやすい。こういうの、うれしい。',
      'kue caption')
    old='''<!-- wp:paragraph -->
<p>クエって、普通に食べようと思うとちょっと身構える超高級魚。<br>でも寿司で一貫なら話は別。<strong>「クエも食べてみるか！」ができる。</strong>こうやって少しずついろんな魚を冒険できるの、かなり楽しいです。</p>
<!-- /wp:paragraph -->

'''
    content=replace_once(content,old,'','remove repeated kue explanation')

    # 4) Market walk: let the photos carry obvious details; keep only reactions.
    content=replace_once(content,
      '<p>クエまで一貫で楽しんだら、今度は売り場をもう一周。<br><strong>「次は何がおる？」と見て回るのが面白い。</strong>最初の店で全部決めるの、たぶん無理です。</p>',
      '<p>寿司を確保しても、まだ終わりません。<br><strong>次は何がおる？</strong></p>',
      'market intro')
    content=replace_once(content,
      '市場の中をぶらぶら。店ごとに並んでいるものが違うので、つい足が止まります。',
      '市場の中をぶらぶら。つい足が止まる。',
      'market aisle caption')
    content=replace_once(content,
      '活サザエ。こういう売り場を見るだけでも市場に来た感じがします。',
      '活サザエ。',
      'sazae caption')
    content=replace_once(content,
      'ふぐ刺しや海鮮丼まで。下関へ来た感が一気に出てきます。',
      'ふぐ刺しに海鮮丼。まだ出る。',
      'fugu caption')
    old='''<!-- wp:paragraph -->
<p>寿司でクエまで食べたと思ったら、売り場には活魚、刺身、海鮮丼。<br><strong>見るたびに候補が増える。</strong>これ、うれしいけど困るやつです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>「まだ出てくるんかい。」</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>自分が全部買うわけじゃないのに、魚を見ているだけでテンションが上がる。<br>釣り好き・魚好きには危険な場所。<strong>財布的な意味で。</strong></p>
<!-- /wp:paragraph -->'''
    new='''<!-- wp:paragraph -->
<p>「まだ出てくるんかい。」<br>釣り好き・魚好きには危険な場所。<strong>財布的な意味で。</strong></p>
<!-- /wp:paragraph -->'''
    content=replace_once(content,old,new,'market repeated list')

    # 5) Eating outside: one image + one feeling is enough.
    content=replace_once(content,
      '<p>寿司を選んだら、外へ。<br><strong>ここから「買ったやつ全部広げる時間」。</strong>これがまた楽しい。</p>',
      '<p>寿司を選んだら、外へ。<br><strong>全部広げる時間。</strong></p>',
      'outside intro')
    content=replace_once(content,
      '寿司に海鮮、汁物まで。外で広げると一気に昼ごはん感が増します。',
      '買ったものを全部広げる。こういう昼ごはん、最高。',
      'outside caption')
    content=replace_once(content,
      '<p>アナゴ、脳天、クエ。気になったものを少しずつ集めて、その場で食べる。<br>一皿ずつ注文する店とは違う。<strong>自分で集めた海鮮オールスターを並べる感じ。</strong></p>',
      '<p>アナゴ、脳天、クエ。気になったものを少しずつ。<br><strong>自分で集めた海鮮オールスター。</strong></p>',
      'outside lineup')
    old='''<!-- wp:paragraph -->
<p>店に入ってメニューを一つ選ぶのとは違って、<br>「これも食べたい。あ、こっちも……」<br>と少しずつ増えていくのも唐戸市場の楽しさでした。</p>
<!-- /wp:paragraph -->

'''
    content=replace_once(content,old,'','remove repeated outside explanation')

    # 6) Honey soft serve: taste, then the weird thing that actually stayed in memory.
    old='''<!-- wp:paragraph -->
<p>海鮮をたっぷり食べたあとは、今度は甘いもの。<br>巣蜜がそのまま乗った蜂蜜ソフトを見つけました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>海鮮のあとに甘いもの。これは強い。<br>蜂蜜の甘さもしっかり。<strong>満足度、高い。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ただ、一番印象に残ったのは味とは別のところ。</p>
<!-- /wp:paragraph -->'''
    new='''<!-- wp:paragraph -->
<p>海鮮のあとは甘いもの。<br>巣蜜つき蜂蜜ソフト、めっちゃ美味しい。</p>
<!-- /wp:paragraph -->'''
    content=replace_once(content,old,new,'soft serve setup')
    content=replace_once(content,
      '<p>食べていると口の中に巣が残る。<br>なんというか、ロウソクみたい。</p>',
      '<p>巣を噛んでると、なんというかロウソクみたい。<br><strong>ここが一番記憶に残りました。</strong></p>',
      'honeycomb reaction')
    old='''<!-- wp:paragraph -->
<p>蜂蜜ソフトを食べに来て、最後に「巣ってこうなるんだ」と感心して終わるとは思いませんでした。</p>
<!-- /wp:paragraph -->

'''
    content=replace_once(content,old,'','remove honeycomb explanation')

    # 7) Fact sections stay useful, but trim the tour-guide voice.
    content=replace_once(content,
      '<p>唐戸市場で寿司や海鮮をたっぷり選びたいなら、週末・祝日に開かれる飲食イベント<strong>「活きいき馬関街」</strong>の開催日を確認してから行くのがおすすめです。</p>',
      '<p>この記事みたいに寿司や海鮮を選びたいなら、<strong>「活きいき馬関街」</strong>の開催日をチェック。</p>',
      'bakangai intro')
    content=replace_once(content,
      '<p>平日に唐戸市場へ行く場合も市場そのものはありますが、この記事の写真のような寿司・海鮮の飲食イベントを目的にするなら、金・土・日・祝を狙った方が分かりやすいです。</p>',
      '<p>月〜木も市場自体はあります。<br>ただ、この記事のような寿司売り場が目的なら開催日を見ておくと安心です。</p>',
      'bakangai weekday')

    # 8) Parking: recommendation -> observed queue -> why. No second explanation of the same route.
    old='''<!-- wp:paragraph -->
<p>車で行くなら、私は<strong>海響館側の駐車場</strong>をおすすめします。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>私たちが使ったのはこちらです。<br><a href="https://maps.app.goo.gl/wR2vtdajgw2kPA9o6?g_st=ic" target="_blank" rel="noopener">私たちが使った駐車場をGoogle Mapsで見る</a></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>もう一つ人気の駐車場はこちら。<br><a href="https://maps.app.goo.gl/SLQJDZufufpfnp5B9?g_st=ic" target="_blank" rel="noopener">訪問時に列ができていた駐車場をGoogle Mapsで見る</a></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>こちらは私たちが行った日はかなり並んでいました。<br>時期や時間帯が良すぎた可能性もあるので「いつも混む」とは言いませんが、列を見てから海響館側へ回るより、最初からそちらを使う方が私たちの遊び方には合っていました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>理由は、<strong>海響館が目の前だから。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>唐戸市場で海鮮を食べる。<br>そのまま海響館へ行く。<br>遊び終わったら車へ戻って、ササッと次の遊び場へ。</p>
<!-- /wp:paragraph -->'''
    new='''<!-- wp:paragraph -->
<p>車なら、私は<strong>海響館側の駐車場</strong>へ。<br><a href="https://maps.app.goo.gl/wR2vtdajgw2kPA9o6?g_st=ic" target="_blank" rel="noopener">私たちが使った駐車場をGoogle Mapsで見る</a></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>もう一つの人気駐車場は、訪問時かなり並んでいました。<br>いつもとは限りませんが、私は次も海響館側へ行きます。<br><a href="https://maps.app.goo.gl/SLQJDZufufnp5B9?g_st=ic" target="_blank" rel="noopener">訪問時に列ができていた駐車場をGoogle Mapsで見る</a></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>理由は<strong>海響館が目の前</strong>だから。<br>唐戸市場 → 海響館 → 車 → 次の遊び場。<strong>ササッと動ける。</strong></p>
<!-- /wp:paragraph -->'''
    content=replace_once(content,old,new,'parking compression')
    old='''<!-- wp:paragraph -->
<p><strong>食べた勢いのまま次の遊びへ。</strong><br>この流れ、かなり楽です。</p>
<!-- /wp:paragraph -->

'''
    content=replace_once(content,old,'','remove parking route repeat')

    # 9) Aquarium: the heading already tells the route. One punch line is enough.
    old='''<!-- wp:paragraph -->
<p>唐戸市場で腹いっぱいになったら、そのまま帰るのはもったいない。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>海響館はすぐ近く。<br>唐戸市場でお腹いっぱいになったら、そのまま水族館へ。<strong>食べたら遊ぶ。</strong>切り替えが早い。</p>
<!-- /wp:paragraph -->'''
    new='''<!-- wp:paragraph -->
<p>唐戸市場で腹いっぱいになったら、そのまま海響館へ。<br><strong>食べたら遊ぶ。</strong></p>
<!-- /wp:paragraph -->'''
    content=replace_once(content,old,new,'aquarium compression')
    content=replace_once(content,
      'このクジラは唐戸市場ではなく<strong>海響館で撮った写真</strong>です。市場からそのまま遊びに行ける距離感がうれしい。',
      '海響館で撮った大きなクジラ。',
      'whale caption')

    # 10) Summary: don't retell every section. End with the user's actual next-time behavior.
    old='''<!-- wp:paragraph -->
<p>唐戸市場は、寿司を食べる場所というより<strong>「何を食べよう！」と迷い始めた瞬間から楽しい市場</strong>でした。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>私なら、まず一本アナゴとマグロの脳天。<br>そして余裕があればクエも一貫。<strong>次に行っても、この辺から攻めます。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ふぐやサザエ、アワビを眺めて、クエみたいな高級魚も一貫ずつ試して、好きな寿司を抱えて外へ。<br>最後に巣蜜つき蜂蜜ソフトを食べて、「巣って溶けないのね」となる。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>そして海響館へ。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>食べて、驚いて、遊んで、ササッと次へ。</strong><br>車で下関を回るなら、唐戸市場を起点にこの流れで遊ぶの、おすすめです。</p>
<!-- /wp:paragraph -->'''
    new='''<!-- wp:paragraph -->
<p>次に行っても、私はまずアナゴと脳天を探します。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>あとは売り場で予定を崩されるだけ。<br><strong>たぶん、それが一番楽しい。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>食べたら海響館へ。<br><strong>食べて、遊んで、ササッと次へ。</strong></p>
<!-- /wp:paragraph -->'''
    content=replace_once(content,old,new,'summary compression')

    return content


def main():
    q=urllib.parse.urlencode({'context':'edit','_fields':'id,slug,status,title,content,modified'})
    row,_=req(f'{SITE}/wp-json/wp/v2/posts/{POST_ID}?{q}')
    current=raw(row,'content')
    current_sha=hashlib.sha256(current.encode()).hexdigest()
    if row.get('id')!=POST_ID or row.get('slug')!=SLUG:
        raise RuntimeError('post identity mismatch')
    if row.get('status')!='publish':
        raise RuntimeError(f"expected publish status, got {row.get('status')}")
    if current_sha!=EXPECTED_SHA:
        raise RuntimeError(f'current content changed; expected {EXPECTED_SHA}, got {current_sha}')
    before_gb=gb_problems(current)
    if before_gb!=0:
        raise RuntimeError(f'Gutenberg problems before edit: {before_gb}')

    new=compress(current)
    after_gb=gb_problems(new)
    if after_gb!=0:
        raise RuntimeError(f'Gutenberg problems after edit: {after_gb}')
    if new==current:
        raise RuntimeError('no changes produced')

    counts_before=public_counts()
    updated,_=req(f'{SITE}/wp-json/wp/v2/posts/{POST_ID}',method='POST',payload={'content':new})
    if updated.get('id')!=POST_ID or updated.get('status')!='publish':
        raise RuntimeError('update response identity/status mismatch')

    verify,_=req(f'{SITE}/wp-json/wp/v2/posts/{POST_ID}?{q}')
    verified=raw(verify,'content')
    if verify.get('status')!='publish' or verify.get('slug')!=SLUG:
        raise RuntimeError('verification identity/status mismatch')
    if gb_problems(verified)!=0:
        raise RuntimeError('Gutenberg problems after server roundtrip')
    counts_after=public_counts()
    if counts_after!=counts_before:
        raise RuntimeError(f'published counts changed unexpectedly: {counts_before} -> {counts_after}')

    print('# Karato Market compression pass')
    print('- result: **SUCCESS**')
    print('- post_id: **3633**')
    print('- slug: **karato-market**')
    print('- status: **publish**')
    print(f'- chars_before: **{len(current)}**')
    print(f'- chars_after: **{len(verified)}**')
    print(f'- cut_chars: **{len(current)-len(verified)}**')
    print(f'- gutenberg_problems_before: **{before_gb}**')
    print('- gutenberg_problems_after: **0**')
    print(f'- published_before: **{counts_before}**')
    print(f'- published_after: **{counts_after}**')
    print(f'- content_sha256: **{hashlib.sha256(verified.encode()).hexdigest()}**')

if __name__=='__main__':
    main()
