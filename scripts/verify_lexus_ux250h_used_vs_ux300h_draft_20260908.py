#!/usr/bin/env python3
from __future__ import annotations
import base64, html, json, os, re, time, urllib.parse, urllib.request

SITE='https://tsurikue.com'; UA='tsurikue-verify-ux250h-used-vs-ux300h-20260908/1.0'
TITLE='レクサスUX250h中古とUX300h新車はどっち？元オーナーが今買うなら中古を選ぶ理由'; SLUG='lexus-ux250h-used-vs-ux300h'
G='[blog_parts id="2843"]'; B='[blog_parts id="2846"]'; C='[blog_parts id="2184"]'
TOKEN=re.compile(r'<!--\s+/?wp:[\s\S]*?-->'); OPEN=re.compile(r'<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->'); CLOSE=re.compile(r'<!--\s+/wp:([\w\-/]+)\s+-->')


def auth():
    raw=f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode(); return 'Basic '+base64.b64encode(raw).decode()

def get(url,timeout=60):
    last=None
    for n in range(3):
        try:
            req=urllib.request.Request(url,headers={'Authorization':auth(),'Accept':'application/json','User-Agent':UA})
            with urllib.request.urlopen(req,timeout=timeout) as r:return json.loads(r.read().decode()),dict(r.headers)
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

def main():
    q=urllib.parse.urlencode({'context':'edit','slug':SLUG,'status':'draft','per_page':10,'_fields':'id,slug,status,link,title,content,featured_media,categories,tags'})
    rows,_=get(f'{SITE}/wp-json/wp/v2/posts?{q}')
    assert len(rows)==1
    row=rows[0]; c=raw(row,'content')
    checks={
      'identity': row.get('slug')==SLUG and row.get('status')=='draft' and html.unescape(raw(row,'title'))==TITLE,
      'featured': int(row.get('featured_media') or 0)==2330,
      'categories': sorted(row.get('categories') or [])==[10,11],
      'tags': sorted(row.get('tags') or [])==[36,37],
      'gutenberg': problems(c)==0,
      'no_h1_in_body': '<h1' not in c.lower(),
      'gulliver_1': c.count(G)==1,
      'ctn_banner_1': c.count(B)==1,
      'ctn_button_1': c.count(C)==1,
      'production_end_fact': '2027年2月' in c and '生産終了予定' in c,
      'new_price_fact': '521万円〜575万7,000円' in c and '534万1,000円' in c,
      'used_price_fact': '199.6万円〜' in c,
      'firsthand_300h': '走りに大きな違いは感じなかった。少し静かになった' in c,
      'appraisal_timing': '約3か月・約5,000km' in c and '約5か月' not in c,
      'ctn_two_companies': 'カーセブンとネクステージの2社' in c,
      'ctn_sale_427': '427万円で売却' in c,
      'media_250h': 'wp-image-2223' in c,
      'media_300h': 'wp-image-2330' in c,
      'media_250h_early': 'wp-image-1352' in c,
      'media_250h_late': 'wp-image-2952' in c,
      'media_300h_interior': 'wp-image-1624' in c,
      'internal_used': 'https://tsurikue.com/lexus-ux-used/' in c,
      'internal_model_change': 'https://tsurikue.com/lexus-ux-model-change/' in c,
      'internal_ux300h': 'https://tsurikue.com/ux300h/' in c,
    }
    failed=[k for k,v in checks.items() if not v]
    assert not failed, failed
    print('# New UX250h used vs UX300h draft verification')
    print('- result: **SUCCESS**')
    print('- wordpress_write_count: **0**')
    print(f'- post_id: **{row.get("id")}**')
    print('- status: **draft**')
    print('- all checks passed: **%d/%d**' % (len(checks),len(checks)))
    print('- Gutenberg problems: **0**')
    print('- CTA counts: Gulliver **1** / CTN banner **1** / CTN button **1**')
    print('- media reused from WordPress: **5**')

if __name__=='__main__': main()
