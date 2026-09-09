#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, os, re, urllib.parse, urllib.request

SITE='https://tsurikue.com'
UA='tsurikue-fix-karato-market-flow-20260909/1.0'
POST_ID=3633
SLUG='karato-market'
EXPECTED_CURRENT_SHA='b1999df3814eb3d13492c1eceb41c3071c210d5c4bcea147066ab88db2b6657d'
MARKER='<!-- karato-fix:20260909-flow-v2 -->'
TOKEN=re.compile(r'<!--\s+/?wp:[\s\S]*?-->')
OPEN=re.compile(r'<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->')
CLOSE=re.compile(r'<!--\s+/wp:([\w\-/]+)\s+-->')


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


def gb_problems(text):
    stack=[]; bad=0
    for m in TOKEN.finditer(text):
        t=m.group(0); o=OPEN.fullmatch(t); c=CLOSE.fullmatch(t)
        if o:
            if not o.group(2): stack.append(o.group(1))
        elif c:
            if not stack or stack[-1]!=c.group(1): bad+=1
            else: stack.pop()
    return bad+len(stack)


def replace_once(text, old, new, label):
    n=text.count(old)
    if n!=1: raise RuntimeError(f'{label}: expected exactly 1 match, got {n}')
    return text.replace(old,new,1)


def fix(content):
    if MARKER in content: raise RuntimeError('v2 marker already present')
    content=MARKER+'\n'+content

    # v1 removed the whale figure and closing block comment, but left the opening image block marker.
    # That malformed Gutenberg block can make following blocks render strangely in the editor.
    dangling='<!-- wp:image {"id":1003,"sizeSlug":"large","linkDestination":"none"} -->\n\n<!-- wp:heading -->'
    content=replace_once(content,dangling,'<!-- wp:heading -->','remove dangling whale block opener')

    # Clean any accidental center alignment metadata if WordPress inserted it while recovering invalid blocks.
    content=content.replace(' class="has-text-align-center"','')
    content=content.replace(' class="has-text-align-center wp-element-caption"',' class="wp-element-caption"')
    content=content.replace(' style="text-align:center"','')
    content=content.replace(' style="text-align: center"','')
    content=content.replace('<!-- wp:paragraph {"align":"center"} -->','<!-- wp:paragraph -->')

    reps=[
      (
        '<p>まず目に飛び込んできたのがアナゴ。<br>寿司の列の中でも、あの長さは反則です。</p>',
        '<p>まず目に飛び込んできたのがアナゴ。<br>寿司の列の中でも、あの長さは反則。<strong>「これ一本いく！」</strong>と、かなり早い段階で決まりました。</p>',
        'anago tempo'),
      (
        '<p><strong>一本が丸ごとドン。</strong><br>見た瞬間から「でかっ」となるんですが、見た目だけでは終わりません。</p>',
        '<p><strong>一本が丸ごとドン。</strong><br>見た瞬間から「でかっ」。しかも、見た目のインパクトだけでは終わりません。</p>',
        'anago punch'),
      (
        '<p>食べると脂がたっぷりでトロトロ。<br>それなのに、ただ脂が旨いだけではなく、赤身みたいに<strong>「マグロを食べている」風味がしっかりある</strong>んです。</p>',
        '<p>食べると脂たっぷり、トロトロ。<br>なのに脂の甘さだけで終わらず、赤身みたいに<strong>「マグロを食べている」風味がグッと来る</strong>んです。</p>',
        'brain tuna tempo'),
      (
        '<figure class="wp-block-image size-large"><img src="https://tsurikue.com/wp-content/uploads/2026/05/img_2079.jpg" alt="唐戸市場で少しずつ選んだ寿司と左端のクエ" class="wp-image-981"/><figcaption class="wp-element-caption">気になるものを少しずつ。<strong>左端は超高級魚のクエ</strong>です。こうやって一貫ずつなら、クエまで気軽に試せるのがうれしい。</figcaption></figure>',
        '<figure class="wp-block-image size-large"><img src="https://tsurikue.com/wp-content/uploads/2026/05/img_2079.jpg" alt="唐戸市場で少しずつ選んだ寿司と左端のクエ" class="wp-image-981"/><figcaption class="wp-element-caption">少しずつ選んだ寿司。<strong>左端がクエ</strong>です。超高級魚でも一貫なら「せっかくだし食べてみよう」ができる。</figcaption></figure>',
        'kue caption'),
      (
        '<p>高級魚って一匹やコースで考えると身構えますが、寿司なら「クエも一個いってみよう」ができる。<br><strong>少しずついろんな魚を冒険できる</strong>のも、唐戸市場のワクワクするところでした。</p>',
        '<p>クエって、普通に食べようと思うとちょっと身構える超高級魚。<br>でも寿司で一貫なら話は別。<strong>「クエも食べてみるか！」ができる。</strong>こうやって少しずついろんな魚を冒険できるの、かなり楽しいです。</p>',
        'kue eaten context'),
      (
        '<h2 class="wp-block-heading">寿司だけじゃない。ふぐ・サザエ・アワビ、クエまで並ぶ</h2>',
        '<h2 class="wp-block-heading">寿司だけじゃない。売り場は魚の宝探し</h2>',
        'market heading'),
      (
        '<p>唐戸市場は、買うものを決めて一直線に歩くより、<strong>まず一周して「何がおる？」と見て回るのが面白い</strong>です。<br>最初の店で全部決めるの、たぶん無理です。</p>',
        '<p>クエまで一貫で楽しんだら、今度は売り場をもう一周。<br><strong>「次は何がおる？」と見て回るのが面白い。</strong>最初の店で全部決めるの、たぶん無理です。</p>',
        'market transition'),
      (
        '<p>活サザエがずらっと並んでいたり。</p>',
        '<p>まず活サザエ。ずらっ。</p>',
        'sazae tempo'),
      (
        '<p>その隣を見れば、アワビもいる。</p>',
        '<p>その隣にはアワビ。まだ出てくる。</p>',
        'awabi tempo'),
      (
        '<p>さらに、ふぐ刺しや海鮮丼まである。<br>「寿司だけのつもりだったのに」がどんどん崩れていきます。</p>',
        '<p>さらに、ふぐ刺しや海鮮丼まで。<br>「寿司だけのつもりだったのに」が、ここで完全に崩れます。</p>',
        'fugu tempo'),
      (
        '<p>そして、売り場には<strong>高級魚のクエまで。</strong><br>さっきの寿司写真の左端がそのクエです。</p>',
        '<p>寿司でクエまで食べたと思ったら、売り場には活魚、刺身、海鮮丼。<br><strong>見るたびに候補が増える。</strong>これ、うれしいけど困るやつです。</p>',
        'remove repeated kue discovery'),
      (
        '<p>「クエまで売っとるんかい。」</p>',
        '<p>「まだ出てくるんかい。」</p>',
        'market reaction'),
      (
        '<p>自分が全部買うわけじゃないのに、魚を見ているだけでテンションが上がる。<br>釣り好き・魚好きには危険な場所です。財布的な意味で。</p>',
        '<p>自分が全部買うわけじゃないのに、魚を見ているだけでテンションが上がる。<br>釣り好き・魚好きには危険な場所。<strong>財布的な意味で。</strong></p>',
        'wallet punch'),
      (
        '<p>寿司を選んだら、今度は外へ。<br>ここから「買ったやつ全部広げる時間」です。</p>',
        '<p>寿司を選んだら、外へ。<br><strong>ここから「買ったやつ全部広げる時間」。</strong>これがまた楽しい。</p>',
        'outside tempo'),
      (
        '<p>好きな寿司をあれこれ買って、その場で食べる。<br>一皿ずつ注文する店とは違って、<strong>自分で集めた海鮮オールスターを並べる感じ</strong>が楽しい。</p>',
        '<p>アナゴ、脳天、クエ。気になったものを少しずつ集めて、その場で食べる。<br>一皿ずつ注文する店とは違う。<strong>自分で集めた海鮮オールスターを並べる感じ。</strong></p>',
        'outside lineup'),
      (
        '<p>しかも海のすぐそば。<br>天気がいい日に海を見ながら食べると、ただの昼ごはんより一段テンションが上がります。</p>',
        '<p>しかも海のすぐそば。<br>天気がいい日に海を見ながら食べる。<strong>そりゃテンションも上がる。</strong></p>',
        'seaside tempo'),
      (
        '<p>海鮮のあとに甘いもの。これは強い。<br>蜂蜜の甘さもあって、満足度はかなり高かったです。</p>',
        '<p>海鮮のあとに甘いもの。これは強い。<br>蜂蜜の甘さもしっかり。<strong>満足度、高い。</strong></p>',
        'softcream tempo'),
      (
        '<p><strong>食べた勢いのまま次の遊びへ行ける。</strong><br>この流れがかなり楽でした。</p>',
        '<p><strong>食べた勢いのまま次の遊びへ。</strong><br>この流れ、かなり楽です。</p>',
        'route tempo'),
      (
        '<p>海響館はすぐ近く。<br>私たちも唐戸市場で食べたあと、そのまま海響館へ。お腹いっぱいの次は水族館です。</p>',
        '<p>海響館はすぐ近く。<br>唐戸市場でお腹いっぱいになったら、そのまま水族館へ。<strong>食べたら遊ぶ。</strong>切り替えが早い。</p>',
        'aquarium tempo'),
      (
        '<p>ここで終わりでも十分満足ですが、車ならまだ先へ行けます。<br>さらに山口を遊ぶなら、角島までつなげるのも楽しい。</p>',
        '<p>海響館で遊んでも、車ならまだ先へ行けます。<br><strong>次、どこ行く？</strong> 角島までつなげるのも楽しい。</p>',
        'drive tempo'),
    ]
    for old,new,label in reps:
        content=replace_once(content,old,new,label)
    return content


def main():
    q=urllib.parse.urlencode({'context':'edit','_fields':'id,slug,status,title,content,featured_media,categories,tags'})
    row,_=req(f'{SITE}/wp-json/wp/v2/posts/{POST_ID}?{q}',timeout=60)
    if int(row.get('id') or 0)!=POST_ID or row.get('slug')!=SLUG or row.get('status')!='draft':
        raise RuntimeError('post identity/status mismatch')
    current=raw(row,'content')
    current_sha=hashlib.sha256(current.encode()).hexdigest()
    if current_sha!=EXPECTED_CURRENT_SHA:
        raise RuntimeError(f'current content SHA changed: {current_sha}')
    before_gb=gb_problems(current)
    before_counts=public_counts()
    new=fix(current)
    after_gb_local=gb_problems(new)
    if after_gb_local!=0: raise RuntimeError(f'Gutenberg block balance failed after fix: {after_gb_local}')
    if 'has-text-align-center' in new or 'text-align:center' in new or 'text-align: center' in new:
        raise RuntimeError('center alignment marker remains')
    for phrase in ['左端がクエ','超高級魚でも一貫','一本が丸ごとドン','脂たっぷり、トロトロ','売り場は魚の宝探し','食べたら遊ぶ']:
        if phrase not in new: raise RuntimeError(f'missing required phrase: {phrase}')
    updated,_=req(f'{SITE}/wp-json/wp/v2/posts/{POST_ID}',method='POST',payload={'content':new},timeout=90)
    if updated.get('status')!='draft': raise RuntimeError('draft status changed after update')
    check,_=req(f'{SITE}/wp-json/wp/v2/posts/{POST_ID}?{q}',timeout=60)
    saved=raw(check,'content')
    if saved.strip()!=new.strip(): raise RuntimeError('saved content mismatch')
    after_counts=public_counts()
    if before_counts!=after_counts: raise RuntimeError(f'published counts changed: {before_counts} -> {after_counts}')
    report={
      'result':'SUCCESS','action':'UPDATE','post_id':POST_ID,'slug':SLUG,'status':'draft',
      'gutenberg_problems_before':before_gb,'gutenberg_problems_after':gb_problems(saved),
      'center_alignment_markers_after':0,'kue_context':'eaten-early-no-repeat','tone':'more-contrast',
      'published_before':before_counts,'published_after':after_counts,'publish_count':0,
      'content_sha256':hashlib.sha256(saved.encode()).hexdigest()
    }
    print('# Karato Market flow/tone fix')
    for k,v in report.items(): print(f'- {k}: **{v}**')

if __name__=='__main__': main()
