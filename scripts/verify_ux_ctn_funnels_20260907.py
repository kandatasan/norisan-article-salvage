#!/usr/bin/env python3
import base64, json, os, re, urllib.request

SITE = 'https://tsurikue.com'
UA = 'tsurikue-verify-ux-ctn-funnels-20260907/1.0'
CTN_BANNER='[blog_parts id="2846"]'
CTN_BUTTON='[blog_parts id="2184"]'
TOKEN=re.compile(r'<!--\s+/?wp:[\s\S]*?-->')
OPEN=re.compile(r'<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->')
CLOSE=re.compile(r'<!--\s+/wp:([\w\-/]+)\s+-->')

def auth():
    raw=f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()
    return 'Basic '+base64.b64encode(raw).decode()

def get(pid):
    req=urllib.request.Request(f'{SITE}/wp-json/wp/v2/posts/{pid}?context=edit',headers={'Authorization':auth(),'Accept':'application/json','User-Agent':UA})
    with urllib.request.urlopen(req,timeout=60) as r:
        return json.loads(r.read().decode())

def raw(row,key):
    v=row.get(key) or {}
    return (v.get('raw') or v.get('rendered') or '') if isinstance(v,dict) else str(v)

def problems(text):
    stack=[]
    for m in TOKEN.finditer(text):
        t=m.group(0); o=OPEN.fullmatch(t); c=CLOSE.fullmatch(t)
        if o:
            if not o.group(2): stack.append(o.group(1))
        elif c:
            if not stack or stack[-1]!=c.group(1): return 1
            stack.pop()
    return len(stack)

def main():
    k=get(2517); r=get(2222)
    kc=raw(k,'content'); rc=raw(r,'content')
    assert k['status']=='publish' and k['slug']=='ux-koukai' and k['featured_media']==2208
    assert r['status']=='publish' and r['slug']=='ux-resale' and r['featured_media']==2223
    assert '約5か月' not in kc
    assert '約3か月ごろ' in kc
    assert '電話が少なくて快適でした' in kc
    assert kc.count(CTN_BANNER)==1 and kc.count(CTN_BUTTON)==2
    assert '電話が少なくて、私はかなり快適でした' in rc
    assert rc.count(CTN_BANNER)==2 and rc.count(CTN_BUTTON)==1
    assert problems(kc)==0 and problems(rc)==0
    print('# UX CTN final verification')
    print('- result: **SUCCESS**')
    print('- wordpress_write_count: **0**')
    print('- ux-koukai: **publish** / 約3か月ごろ / phone note **present** / banners **1** / buttons **2** / Gutenberg **0**')
    print('- ux-resale: **publish** / phone note **present** / banners **2** / buttons **1** / Gutenberg **0**')

if __name__=='__main__':
    main()
