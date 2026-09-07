#!/usr/bin/env python3
import base64, json, os, re, urllib.request
SITE='https://tsurikue.com'; UA='tsurikue-verify-lexus-discount-mitsumori-20260907/1.0'
CTN_BANNER='[blog_parts id="2846"]'; CTN_BUTTON='[blog_parts id="2184"]'; GULLIVER='[blog_parts id="2843"]'
TOKEN=re.compile(r'<!--\s+/?wp:[\s\S]*?-->'); OPEN=re.compile(r'<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->'); CLOSE=re.compile(r'<!--\s+/wp:([\w\-/]+)\s+-->')
def auth():
    raw=f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode(); return 'Basic '+base64.b64encode(raw).decode()
def get(pid):
    req=urllib.request.Request(f'{SITE}/wp-json/wp/v2/posts/{pid}?context=edit',headers={'Authorization':auth(),'Accept':'application/json','User-Agent':UA})
    with urllib.request.urlopen(req,timeout=60) as r:return json.loads(r.read().decode())
def raw(row,key):
    v=row.get(key) or {}; return (v.get('raw') or v.get('rendered') or '') if isinstance(v,dict) else str(v)
def problems(text):
    stack=[]
    for m in TOKEN.finditer(text):
        t=m.group(0);o=OPEN.fullmatch(t);c=CLOSE.fullmatch(t)
        if o:
            if not o.group(2):stack.append(o.group(1))
        elif c:
            if not stack or stack[-1]!=c.group(1):return 1
            stack.pop()
    return len(stack)
def main():
    d=get(2962);dc=raw(d,'content')
    m=get(2240);mc=raw(m,'content')
    assert d['slug']=='lexus-ux-discount' and d['status']=='publish' and d['featured_media']==2231
    assert m['slug']=='ux-mitsumori' and m['status']=='publish' and m['featured_media']==2241
    assert '電話が少なくて快適でした' in dc
    assert 'まずは「今の車、いくらになる？」から。' in dc
    assert dc.count(GULLIVER)==1 and dc.count(CTN_BANNER)==0 and dc.count(CTN_BUTTON)==1 and problems(dc)==0
    assert '前の一括査定とは違って電話が少なく、快適でした' in mc
    assert '高く売りたい。でも、あの電話ラッシュはもういらない。' in mc
    assert mc.count(GULLIVER)==0 and mc.count(CTN_BANNER)==0 and mc.count(CTN_BUTTON)==1 and problems(mc)==0
    print('# Lexus discount + mitsumori post-apply verification')
    print('- result: **SUCCESS**')
    print('- wordpress_write_count: **0**')
    print('- lexus-ux-discount: **publish / featured 2231 / Gulliver 1 / CTN button 1 / phone note present / microcopy present / Gutenberg 0**')
    print('- ux-mitsumori: **publish / featured 2241 / CTN button 1 / comfort contrast present / microcopy present / Gutenberg 0**')
if __name__=='__main__':main()
