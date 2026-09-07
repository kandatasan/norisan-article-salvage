#!/usr/bin/env python3
import base64, html, json, os, re, time, urllib.parse, urllib.request

SITE='https://tsurikue.com'; UA='tsurikue-verify-ux-vs-nx-20260908/1.0'
TITLE='レクサスUXとNXどっち？元UXオーナーがサイズ・価格・使い勝手を比較'; SLUG='lexus-ux-vs-nx'; FEATURED=2197
G='[blog_parts id="2843"]'; B='[blog_parts id="2846"]'; C='[blog_parts id="2184"]'
TOKEN=re.compile(r'<!--\s+/?wp:[\s\S]*?-->'); OPEN=re.compile(r'<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->'); CLOSE=re.compile(r'<!--\s+/wp:([\w\-/]+)\s+-->')

def auth():
    u=os.environ.get('TSURIKUE_WP_USER'); p=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
    if not u or not p: raise SystemExit('BLOCKED_MISSING_SECRETS')
    return 'Basic '+base64.b64encode(f'{u}:{p}'.encode()).decode()

def get(url,timeout=60):
    last=None
    for n in range(3):
        try:
            r=urllib.request.Request(url,headers={'Authorization':auth(),'Accept':'application/json','User-Agent':UA},method='GET')
            with urllib.request.urlopen(r,timeout=timeout) as x: return json.loads(x.read().decode()),dict(x.headers)
        except Exception as e:
            last=e
            if n<2: time.sleep(3*(n+1))
    raise last

def raw(row,key):
    v=row.get(key) or {}; return (v.get('raw') or v.get('rendered') or '') if isinstance(v,dict) else str(v)

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

def published_count():
    q=urllib.parse.urlencode({'status':'publish','per_page':1,'_fields':'id'})
    _,h=get(f'{SITE}/wp-json/wp/v2/posts?{q}',45); return int(h.get('X-WP-Total','0'))

def main():
    q=urllib.parse.urlencode({'context':'edit','slug':SLUG,'status':'any','per_page':5,'_fields':'id,slug,status,title,content,featured_media,categories,tags,link'})
    rows,_=get(f'{SITE}/wp-json/wp/v2/posts?{q}',60)
    assert len(rows)==1, rows
    r=rows[0]; c=raw(r,'content')
    checks={
      'status_draft':r.get('status')=='draft',
      'title':html.unescape(raw(r,'title'))==TITLE,
      'featured':int(r.get('featured_media') or 0)==FEATURED,
      'categories':sorted(r.get('categories') or [])==[10,11],
      'tags':sorted(r.get('tags') or [])==[36,37,42],
      'gutenberg':problems(c)==0,
      'gulliver':c.count(G)==1,
      'ctn_banner':c.count(B)==1,
      'ctn_button':c.count(C)==1,
      'ux_photo':'wp-image-2223' in c,
      'ux300h_photo':'wp-image-2330' in c,
      'production_end':'2027年2月' in c,
      'price_gap':'約106万5,000円' in c,
      'nx_driven':'NXも実際に運転したことがあります' in c,
      'ux_conclusion':'普段1〜2人で乗るならUX' in c,
      'nx_conclusion':'3人以上での移動や荷物の多さまで考えるならNX' in c,
      'review_link':'https://tsurikue.com/lexus-ux-review/' in c,
      'size_link':'https://tsurikue.com/lexus-ux-size/' in c,
      'rear_link':'https://tsurikue.com/lexus-ux-rear-seat/' in c,
      'cargo_link':'https://tsurikue.com/lexus-ux-cargo/' in c,
      'model_link':'https://tsurikue.com/lexus-ux-model-change/' in c,
      'new_compare_link':'https://tsurikue.com/lexus-ux250h-used-vs-ux300h/' in c,
      'ctn_two_companies':'カーセブンとネクステージの2社' in c,
      'ctn_phone':'電話が少なく快適' in c,
    }
    bad=[k for k,v in checks.items() if not v]
    if bad: raise RuntimeError(f'failed checks: {bad}')
    print('# New Lexus UX vs NX draft verification')
    print('- result: **SUCCESS**')
    print('- wordpress_write_count: **0**')
    print(f"- post_id: **{r['id']}**")
    print('- status: **draft**')
    print(f'- all checks passed: **{len(checks)}/{len(checks)}**')
    print('- Gutenberg problems: **0**')
    print('- CTA counts: Gulliver **1** / CTN banner **1** / CTN button **1**')
    print('- WordPress media: featured **2197** + body **2223, 2330**')
    print(f'- published_posts: **{published_count()}**')

if __name__=='__main__': main()
