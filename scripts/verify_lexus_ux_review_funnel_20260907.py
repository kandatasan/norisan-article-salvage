#!/usr/bin/env python3
import base64, json, os, re, urllib.request
SITE='https://tsurikue.com'; POST_ID=2870; UA='tsurikue-verify-lexus-ux-review-20260907/1.0'
GULLIVER='[blog_parts id="2843"]'; CTN_BANNER='[blog_parts id="2846"]'; CTN_BUTTON='[blog_parts id="2184"]'; MARKER='<!-- tsurikue-ctn-review-funnel:20260907 -->'
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
    assert row['id']==2870 and row['slug']=='lexus-ux-review' and row['status']=='publish' and row['featured_media']==2231
    assert MARKER in c and '私のときは2社から連絡が来て、電話が少なくて快適でした' in c
    assert c.count(GULLIVER)==1 and c.count(CTN_BANNER)==1 and c.count(CTN_BUTTON)==1 and problems(c)==0
    assert c.index(MARKER) < c.index(CTN_BANNER)
    print('# lexus-ux-review post-apply verification')
    print('- result: **SUCCESS**')
    print('- wordpress_write_count: **0**')
    print('- status: **publish** / featured_media: **2231**')
    print('- Gulliver **1** / CTN banner **1** / CTN button **1**')
    print('- phone note: **present before CTN banner** / Gutenberg problems: **0**')
if __name__=='__main__':main()
