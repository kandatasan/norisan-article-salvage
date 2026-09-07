#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, os, re, urllib.request

SITE='https://tsurikue.com'
UA='tsurikue-optimize-lexus-discount-mitsumori-20260907/1.0'
CTN_BANNER='[blog_parts id="2846"]'
CTN_BUTTON='[blog_parts id="2184"]'
GULLIVER='[blog_parts id="2843"]'
TOKEN=re.compile(r'<!--\s+/?wp:[\s\S]*?-->')
OPEN=re.compile(r'<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->')
CLOSE=re.compile(r'<!--\s+/wp:([\w\-/]+)\s+-->')

TARGETS={
  2962:{
    'slug':'lexus-ux-discount',
    'title':'レクサスUXは値引きできる？値引き0円だった実体験と安く買う方法',
    'featured':2231,
    'sha':'f52e42e5f4f418aa7cfc672b3bd30a56ae2832f5dca7402b71bf380bcba49bb3',
    'gulliver':1,'ctn_banner':0,'ctn_button':1,
  },
  2240:{
    'slug':'ux-mitsumori',
    'title':'レクサスUXの見積もり公開｜総額616万円で選んだ特別仕様車とオプション',
    'featured':2241,
    'sha':'69b576dc7c08046d86eb861b3e805c797b927b95c2540adb2a50285699376fec',
    'gulliver':0,'ctn_banner':0,'ctn_button':1,
  },
}

DISC_OLD='''<p>その後、UX自体を手放したときにはCTN車一括査定を利用しました。<br>私のときに連絡が来たのはカーセブンとネクステージの2社で、最終的にはカーセブンへ427万円で売却しています。</p>'''
DISC_NEW='''<p>その後、UX自体を手放したときにはCTN車一括査定を利用しました。<br>CTNは最大15社で査定し、やり取りするのは高額査定の上位3社だけ。<br><strong>私のときに連絡が来たのはカーセブンとネクステージの2社で、電話が少なくて快適でした。</strong><br>最終的にはカーセブンへ427万円で売却しています。</p>'''
DISC_MICRO='''<!-- tsurikue-ctn-discount-microcopy:20260907 -->
<!-- wp:paragraph -->
<p><strong>まずは「今の車、いくらになる？」から。</strong></p>
<!-- /wp:paragraph -->'''

MITSU_OLD='''<p>私のときに連絡が来たのは、カーセブンとネクステージの2社です。<br>どちらにも実際のUXを見てもらい、最終的にはカーセブンへ427万円で売却しました。</p>'''
MITSU_NEW='''<p>私のときに連絡が来たのは、カーセブンとネクステージの2社です。<br><strong>前の一括査定とは違って電話が少なく、快適でした。</strong><br>どちらにも実際のUXを見てもらい、最終的にはカーセブンへ427万円で売却しました。</p>'''
MITSU_MICRO='''<!-- tsurikue-ctn-mitsumori-microcopy:20260907 -->
<!-- wp:paragraph -->
<p><strong>高く売りたい。でも、あの電話ラッシュはもういらない。</strong></p>
<!-- /wp:paragraph -->'''

def auth():
    raw=f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()
    return 'Basic '+base64.b64encode(raw).decode()

def req(url,method='GET',payload=None):
    headers={'Authorization':auth(),'Accept':'application/json','User-Agent':UA}
    data=None
    if payload is not None:
        data=json.dumps(payload,ensure_ascii=False).encode('utf-8')
        headers['Content-Type']='application/json; charset=utf-8'
    r=urllib.request.Request(url,data=data,headers=headers,method=method)
    with urllib.request.urlopen(r,timeout=60) as resp:
        return json.loads(resp.read().decode('utf-8')),dict(resp.headers)

def get(pid): return req(f'{SITE}/wp-json/wp/v2/posts/{pid}?context=edit')[0]

def raw(row,key):
    v=row.get(key) or {}
    return (v.get('raw') or v.get('rendered') or '') if isinstance(v,dict) else str(v)

def public_count():
    _,h=req(f'{SITE}/wp-json/wp/v2/posts?status=publish&per_page=1&_fields=id')
    return int(h.get('X-WP-Total',0))

def problems(text):
    stack=[]
    for m in TOKEN.finditer(text):
        t=m.group(0);o=OPEN.fullmatch(t);c=CLOSE.fullmatch(t)
        if o:
            if not o.group(2): stack.append(o.group(1))
        elif c:
            if not stack or stack[-1]!=c.group(1): return 1
            stack.pop()
    return len(stack)

def check_identity(row,cfg):
    assert row['slug']==cfg['slug'] and row['status']=='publish'
    assert raw(row,'title')==cfg['title'] and row['featured_media']==cfg['featured']

def insert_before_button(content,micro):
    assert content.count(CTN_BUTTON)==1
    pos=content.index(CTN_BUTTON)
    start=content.rfind('<!-- wp:shortcode -->',0,pos)
    assert start>=0
    return content[:start]+micro+'\n\n'+content[start:]

def prepare_discount(c):
    assert c.count(DISC_OLD)==1
    assert 'tsurikue-ctn-discount-microcopy:20260907' not in c
    fixed=c.replace(DISC_OLD,DISC_NEW,1)
    fixed=insert_before_button(fixed,DISC_MICRO)
    return fixed

def prepare_mitsumori(c):
    assert c.count(MITSU_OLD)==1
    assert 'tsurikue-ctn-mitsumori-microcopy:20260907' not in c
    fixed=c.replace(MITSU_OLD,MITSU_NEW,1)
    fixed=insert_before_button(fixed,MITSU_MICRO)
    return fixed

def main():
    before_public=public_count()
    rows={}; before={}; fixed={}
    for pid,cfg in TARGETS.items():
        row=get(pid); check_identity(row,cfg); c=raw(row,'content')
        assert hashlib.sha256(c.encode('utf-8')).hexdigest()==cfg['sha']
        assert problems(c)==0
        assert c.count(GULLIVER)==cfg['gulliver']
        assert c.count(CTN_BANNER)==cfg['ctn_banner']
        assert c.count(CTN_BUTTON)==cfg['ctn_button']
        rows[pid]=row; before[pid]=c
    fixed[2962]=prepare_discount(before[2962])
    fixed[2240]=prepare_mitsumori(before[2240])
    for pid,cfg in TARGETS.items():
        c=fixed[pid]
        assert problems(c)==0
        assert c.count(GULLIVER)==cfg['gulliver']
        assert c.count(CTN_BANNER)==cfg['ctn_banner']
        assert c.count(CTN_BUTTON)==cfg['ctn_button']
    assert '電話が少なくて快適でした' in fixed[2962]
    assert 'まずは「今の車、いくらになる？」から。' in fixed[2962]
    assert '前の一括査定とは違って電話が少なく、快適でした' in fixed[2240]
    assert '高く売りたい。でも、あの電話ラッシュはもういらない。' in fixed[2240]

    writes=0
    for pid in (2962,2240):
        req(f'{SITE}/wp-json/wp/v2/posts/{pid}',method='POST',payload={'content':fixed[pid]}); writes+=1

    for pid,cfg in TARGETS.items():
        row=get(pid); check_identity(row,cfg); c=raw(row,'content')
        assert c==fixed[pid] and problems(c)==0
        assert c.count(GULLIVER)==cfg['gulliver']
        assert c.count(CTN_BANNER)==cfg['ctn_banner']
        assert c.count(CTN_BUTTON)==cfg['ctn_button']
    after_public=public_count(); assert after_public==before_public
    print('# Lexus discount + mitsumori CTN polish')
    print('- result: **SUCCESS**')
    print(f'- WordPress writes: **{writes}** (content only)')
    print(f'- public posts: **{before_public} → {after_public}**')
    print('- lexus-ux-discount: **publish / featured 2231 / Gulliver 1 / CTN button 1 / Gutenberg 0**')
    print('- ux-mitsumori: **publish / featured 2241 / Gulliver 0 / CTN button 1 / Gutenberg 0**')
    print('- added: **firsthand low-phone-volume note + article-specific microcopy only**')

if __name__=='__main__': main()
