#!/usr/bin/env python3
import base64, json, os, re, urllib.request
SITE='https://tsurikue.com'; POST_ID=2881; UA='tsurikue-verify-lexus-ux-buyer-20260907/1.0'
GULLIVER='[blog_parts id="2843"]'; CTN_BANNER='[blog_parts id="2846"]'; CTN_BUTTON='[blog_parts id="2184"]'
MARKER='<!-- tsurikue-ctn-buyer-funnel:20260907 -->'
TOKEN=re.compile(r'<!--\s+/?wp:[\s\S]*?-->'); OPEN=re.compile(r'<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->'); CLOSE=re.compile(r'<!--\s+/wp:([\w\-/]+)\s+-->')
def auth():
    raw=f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode(); return 'Basic '+base64.b64encode(raw).decode()
def get():
    req=urllib.request.Request(f'{SITE}/wp-json/wp/v2/posts/{POST_ID}?context=edit',headers={'Authorization':auth(),'Accept':'application/json','User-Agent':UA})
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
    row=get(); c=raw(row,'content')
    assert row['id']==2881 and row['slug']=='lexus-ux-buyer' and row['status']=='publish' and row['featured_media']==2223
    assert MARKER in c
    assert '納車から約3か月ごろ' in c and 'ディーラーは約350万円' in c and '一括査定サービスでは500万円前後' in c
    assert '私のときは2社から連絡が来て、電話が少なくて快適でした' in c
    assert '買う車を決める前に、「今の車、いくらになる？」を見ておく。' in c
    assert c.count(GULLIVER)==1 and c.count(CTN_BANNER)==0 and c.count(CTN_BUTTON)==1 and problems(c)==0
    print('# lexus-ux-buyer post-apply verification')
    print('- result: **SUCCESS**')
    print('- wordpress_write_count: **0**')
    print('- status: **publish** / featured_media: **2223**')
    print('- Gulliver **1** / CTN banner **0** / CTN button **1**')
    print('- curiosity appraisal: **present** / phone note: **present** / buyer microcopy: **present**')
    print('- Gutenberg problems: **0**')
if __name__=='__main__':main()
