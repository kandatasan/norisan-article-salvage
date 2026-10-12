#!/usr/bin/env python3
"""Six small subtractive edits to UX owner article; read-only PR / guarded WP push."""
import os,sys,json,re,base64,hashlib,urllib.request,urllib.parse
PID=2517
SLUG="ux-koukai"
SITE="https://tsurikue.com"
EXPECTED="39c8b8a5ca0b20440ff4c7dbadd0ffc770ce3c190b1daa8032fa4239deb095b3"
P=re.compile(r'<!-- wp:paragraph(?:\s+\{[^\n]*\})? -->\s*<p(?:\s[^>]*)?>.*?</p>\s*<!-- /wp:paragraph -->',re.S)
H=re.compile(r'<!-- wp:heading(?:\s+\{[^\n]*\})? -->\s*<h([23])\b[^>]*>(.*?)</h\1>\s*<!-- /wp:heading -->',re.S)

def digest(x):return hashlib.sha256(x.encode('utf-8')).hexdigest()
def para(s,needle):
    found=[m for m in P.finditer(s) if needle in m.group()]
    if len(found)!=1:raise RuntimeError(f"paragraph '{needle[:38]}' count {len(found)} != 1")
    return found[0]
def remove(s,needle):
    m=para(s,needle)
    return s[:m.start()]+s[m.end():]
def change(s,needle,html):
    m=para(s,needle);original=m.group()
    pm=re.search(r'<p(?:\s[^>]*)?>.*?</p>',original,re.S)
    if pm is None:raise RuntimeError('Missing p tag')
    replacement=original[:pm.start()]+'<p>'+html+'</p>'+original[pm.end():]
    return s[:m.start()]+replacement+s[m.end():]
def relocate(s,url,last_paragraph):
    m=para(s,'href="'+url+'"')
    link=m.group()
    s=s[:m.start()]+s[m.end():]
    anchor=para(s,last_paragraph)
    return s[:anchor.end()]+'\n\n'+link+s[anchor.end():]
def remove_section(s,heading,next_heading):
    start=[m for m in H.finditer(s) if m.group(2)==heading]
    finish=[m for m in H.finditer(s) if m.group(2)==next_heading]
    if len(start)!=1 or len(finish)!=1 or finish[0].start()<=start[0].end():
        raise RuntimeError('Unexpected heading layout')
    piece=s[start[0].start():finish[0].start()]
    if re.search(r'wp:image|wp:video|wp:gallery|<a\b|\[blog_parts',piece,re.I):
        raise RuntimeError('Proposed used-car section contains media or links; stop')
    return s[:start[0].start()]+s[finish[0].start():]

def transform(old):
    s=old
    # 1: Fender arch complaint, keep the unique observation and Lexus expectation.
    s=change(s,'走りにも安全性にも関係ありません。',
        '走りにも安全性にも関係ない、細かい話です。<br>でも一度気になると、洗車するたびに目が行く。<br>レクサスだからこそ、ここもきれいに仕上げてほしかったです。')
    for x in ('でも、細かい。','洗車のたびに目が行きました。','UX全体のデザインは好きです。'):
        s=remove(s,x)
    # 2: Let the timeline earn its own single humorous punchline.
    s=remove(s,'約1年待って納車。その約半年後にUX300h。いや、タイミング悪すぎるって')
    s=remove(s,'でも、約1年待ってようやく納車されたあとに、走りや装備が進化したUX300hが出ると')
    s=change(s,'新車でUXを検討している人は、年次改良や新型情報のタイミングも確認した方がいいです。',
        '新車を検討するなら、年次改良や新型情報のタイミングは確認しておきたいところです。')
    # 3: Used UX merits are already in the intro and conclusion. Keep actual 250h comparison and a single Gulliver outlet.
    s=remove_section(s,'200〜300万円台なら、UXの弱点がかなり許せる',
                     'UX250hも、急に古くてダメな車になったわけじゃない')
    s=remove(s,'中古UXを探すなら、ネットに出ている車だけで決めるのはちょっともったいないです。')
    # 4: Owner couple's conclusion should follow the Niyodo Gorge photo, not another spec list.
    s=remove(s,'1〜2人なら後席をほとんど使わない。')
    # 6: Remove generic keyword-heavy interior preamble and self-conscious summary.
    for x in ('UXの内装については、「レクサスUX 内装 しょぼい」',
              '私の感想としては、UXの内装全体がしょぼいというより',
              'これが、実際に所有して感じた一番近い表現です。'):
        s=remove(s,x)
    s=change(s,'まず、前席まわりは良かったです。',
        '前席まわりは良かったです。<br>ハンドル、シート、スイッチ類、運転席から見える景色には、レクサスらしいしっかり感がありました。')
    # 5: Link follows the real-life observation, no new URLs.
    s=relocate(s,'https://tsurikue.com/lexus-ux-rear-seat/',
               '後席ドアの内装も、前席と比べると少しあっさりしています。')
    s=relocate(s,'https://tsurikue.com/lexus-ux-cargo/',
               'ただ、キャンプ用品、大きなクーラーボックス')
    s=relocate(s,'https://tsurikue.com/lexus-ux-interior/',
               '試乗するときは、運転席だけで判断しない方がいいです。')
    for pattern in (r'wp-image-\d+',r'<img\b[^>]*src="([^"]+)"',
                    r'\[blog_parts id="(\d+)"\]',r'<a\b[^>]*href="([^"]+)"'):
        if sorted(re.findall(pattern,s,re.S|re.I))!=sorted(re.findall(pattern,old,re.S|re.I)):
            raise RuntimeError('Image/affiliate/link changed: '+pattern)
    before=[m.group(2) for m in H.finditer(old)]
    after=[m.group(2) for m in H.finditer(s)]
    before.remove('200〜300万円台なら、UXの弱点がかなり許せる')
    if before!=after:raise RuntimeError('Unexpected heading change')
    if old.count('<!-- wp:')-old.count('<!-- /wp:')!=s.count('<!-- wp:')-s.count('<!-- /wp:'):
        raise RuntimeError('Gutenberg block balance changed')
    for phrase in ('荷室でテトリスが始まります。','いや、タイミング悪すぎるって',
                   '文句はある。でも私はUXが好きだった','半額近いじゃん。',
                   '高知県の仁淀川・水晶淵','狭い山道を抜けた先で出会えたのが、この景色です。',
                   'レクサスUXの後部座席レビュー','レクサスUXの内装レビュー'):
        if phrase not in s:raise RuntimeError('Original owner evidence lost: '+phrase)
    if s.count('いや、タイミング悪すぎるって')!=1:
        raise RuntimeError('Repeated timing punchline remains')
    if len(s)>=len(old):raise RuntimeError('Edit must be subtractive')
    print('EDITORIAL_CHANGES',json.dumps({
        'post_id':PID,'before_chars':len(old),'after_chars':len(s),
        'removed_chars':len(old)-len(s),
        'wp_images':len(re.findall(r'wp-image-\d+',s)),
        'affiliate_parts':re.findall(r'\[blog_parts id="(\d+)"\]',s),
        'link_count':len(re.findall(r'<a\b[^>]*href="',s)),
        'h3_removed':'200〜300万円台なら、UXの弱点がかなり許せる'
    },ensure_ascii=False),flush=True)
    return s

def req(path,auth,data=None):
    headers={'Authorization':auth,'Accept':'application/json','User-Agent':'tsurikue-ux-polish/1.0'}
    if data is not None:headers['Content-Type']='application/json; charset=utf-8'
    r=urllib.request.Request(SITE+path,headers=headers,method='POST' if data is not None else 'GET',
        data=json.dumps(data,ensure_ascii=False).encode() if data is not None else None)
    with urllib.request.urlopen(r,timeout=60) as f:return json.load(f)
def get(auth):
    q=urllib.parse.urlencode({'context':'edit','_fields':'id,slug,status,title,content,featured_media,author,categories'})
    return req(f'/wp-json/wp/v2/posts/{PID}?{q}',auth)

def main(mode):
    u=os.getenv('TSURIKUE_WP_USER');p=os.getenv('TSURIKUE_WP_APP_PASSWORD')
    if not u or not p:raise RuntimeError('WP credentials missing')
    auth='Basic '+base64.b64encode((u+':'+p).encode()).decode()
    post=get(auth)
    if (post['id'],post['slug'],post['status'])!=(PID,SLUG,'publish'):
        raise RuntimeError('Wrong WordPress post identity')
    old=post['content']['raw']
    if digest(old)!=EXPECTED:
        raise RuntimeError(f'Human edit since audit; safely blocked: {digest(old)}')
    new=transform(old)
    print('PREFLIGHT_OK',PID,SLUG,digest(old),digest(new),flush=True)
    if mode=='check':return
    current=get(auth)
    if digest(current['content']['raw'])!=EXPECTED:
        raise RuntimeError('Concurrent human edit: no write')
    attempted=False
    try:
        attempted=True
        req(f'/wp-json/wp/v2/posts/{PID}',auth,{'content':new})
        saved=get(auth)
        for f in ('id','slug','status','title','featured_media','author','categories'):
            if saved[f]!=post[f]:raise RuntimeError(f'Protected post field modified: {f}')
        if saved['content']['raw']!=new:raise RuntimeError('WordPress raw body mismatch')
        if ('荷室でテトリスが始まります' not in saved['content'].get('rendered','') or
            '洗車するたびに目が行く' not in saved['content'].get('rendered','')):
            raise RuntimeError('WordPress rendered content mismatch')
        print('LIVE_WORDPRESS_VERIFIED',PID,SLUG,'status=publish',
              'after_sha256='+digest(new),flush=True)
    except Exception:
        if attempted:
            try:
                latest=get(auth)
                if digest(latest['content']['raw'])==digest(new):
                    req(f'/wp-json/wp/v2/posts/{PID}',auth,{'content':old})
                    print('CONDITIONAL_ROLLBACK_OK',PID,flush=True)
                else:print('ROLLBACK_SKIPPED_EXTERNAL_EDIT',PID,flush=True)
            except Exception as e:print('ROLLBACK_FAILED',str(e),flush=True)
        raise
if __name__=='__main__':
    mode=sys.argv[1] if len(sys.argv)>1 else 'check'
    if mode not in ('check','apply'):raise SystemExit('Expected check/apply')
    main(mode)
