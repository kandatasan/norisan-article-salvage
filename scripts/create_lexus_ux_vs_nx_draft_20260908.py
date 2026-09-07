#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, os, re, time, urllib.parse, urllib.request
from pathlib import Path

SITE='https://tsurikue.com'
UA='tsurikue-create-ux-vs-nx-20260908/1.0'
TITLE='レクサスUXとNXどっち？元UXオーナーがサイズ・価格・使い勝手を比較'
SLUG='lexus-ux-vs-nx'
CONTENT_PATH=Path('packages/lexus-ux-vs-nx/content.html')
FEATURED=2197
CATEGORIES=[10,11]
TAGS=[36,37,42]
EXPECTED_MEDIA={
  2197:'/wp-content/uploads/2026/06/IMG_3929.jpeg',
  2223:'/wp-content/uploads/2026/06/IMG_1250.jpeg',
  2330:'/wp-content/uploads/2026/06/IMG_3607.jpeg',
}
G='[blog_parts id="2843"]'; B='[blog_parts id="2846"]'; C='[blog_parts id="2184"]'
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
    last=None
    for n in range(3):
        try:
            r=urllib.request.Request(url,data=data,headers=headers,method=method)
            with urllib.request.urlopen(r,timeout=timeout) as resp: return json.loads(resp.read().decode()),dict(resp.headers)
        except Exception as e:
            last=e
            if n<2: time.sleep(3*(n+1))
    raise last

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

def published_count():
    q=urllib.parse.urlencode({'status':'publish','per_page':1,'_fields':'id'})
    _,h=req(f'{SITE}/wp-json/wp/v2/posts?{q}',timeout=45)
    return int(h.get('X-WP-Total','0'))

def validate_media():
    for mid,path in EXPECTED_MEDIA.items():
        q=urllib.parse.urlencode({'context':'edit','_fields':'id,status,source_url'})
        row,_=req(f'{SITE}/wp-json/wp/v2/media/{mid}?{q}',timeout=45)
        actual=urllib.parse.unquote(urllib.parse.urlparse(row.get('source_url') or '').path)
        assert row.get('id')==mid and actual.casefold()==path.casefold(), (mid,actual,path)

def find_existing():
    q=urllib.parse.urlencode({'context':'edit','slug':SLUG,'status':'any','per_page':10,'_fields':'id,slug,status,title,content,featured_media,categories,tags'})
    rows,_=req(f'{SITE}/wp-json/wp/v2/posts?{q}',timeout=45)
    return rows

def main():
    content=CONTENT_PATH.read_text(encoding='utf-8').strip()+'\n'
    assert '<h1' not in content.lower()
    assert problems(content)==0
    assert content.count(G)==1 and content.count(B)==1 and content.count(C)==1
    assert '2027年2月' in content and '約106万5,000円' in content and 'NXも実際に運転したことがあります' in content
    for mid in [2223,2330]: assert f'wp-image-{mid}' in content
    validate_media()
    before=published_count(); existing=find_existing(); action='CREATE'
    if existing:
        assert len(existing)==1
        row=existing[0]
        same=(row.get('status')=='draft' and html.unescape(raw(row,'title'))==TITLE and raw(row,'content').strip()==content.strip() and int(row.get('featured_media') or 0)==FEATURED and sorted(row.get('categories') or [])==sorted(CATEGORIES) and sorted(row.get('tags') or [])==sorted(TAGS))
        if not same: raise RuntimeError(f'slug already exists but differs: id={row.get("id")} status={row.get("status")}')
        created=row; action='ALREADY_UP_TO_DATE'
    else:
        payload={
          'title':TITLE,'slug':SLUG,'content':content,'status':'draft','featured_media':FEATURED,
          'categories':CATEGORIES,'tags':TAGS,
          'excerpt':'レクサスUXとNXはどっちが合う？UXを1万km以上所有しNXも運転した筆者が、サイズ・価格・後席・荷室・取り回しを比較。1〜2人ならUX、家族や荷物まで考えるならNXという選び方を実体験から解説します。'
        }
        created,_=req(f'{SITE}/wp-json/wp/v2/posts',method='POST',payload=payload,timeout=90)
        assert created.get('status')=='draft' and created.get('slug')==SLUG
    pid=int(created['id'])
    q=urllib.parse.urlencode({'context':'edit','_fields':'id,slug,status,link,title,content,featured_media,categories,tags,excerpt'})
    after,_=req(f'{SITE}/wp-json/wp/v2/posts/{pid}?{q}',timeout=60); after_pub=published_count()
    assert before==after_pub
    assert after.get('id')==pid and after.get('slug')==SLUG and after.get('status')=='draft'
    assert html.unescape(raw(after,'title'))==TITLE and raw(after,'content').strip()==content.strip()
    assert int(after.get('featured_media') or 0)==FEATURED
    assert sorted(after.get('categories') or [])==sorted(CATEGORIES) and sorted(after.get('tags') or [])==sorted(TAGS)
    assert problems(raw(after,'content'))==0
    assert raw(after,'content').count(G)==1 and raw(after,'content').count(B)==1 and raw(after,'content').count(C)==1
    report={'result':'SUCCESS','action':action,'post_id':pid,'slug':SLUG,'status':'draft','title':TITLE,'featured_media':FEATURED,'categories':CATEGORIES,'tags':TAGS,'media_checked':len(EXPECTED_MEDIA),'gulliver_banner':1,'ctn_banner':1,'ctn_button':1,'gutenberg_problems':0,'published_posts_before':before,'published_posts_after':after_pub,'content_sha256':hashlib.sha256(raw(after,'content').encode()).hexdigest(),'wordpress_write_count':1 if action=='CREATE' else 0,'publish_count':0}
    print('# New Lexus UX vs NX draft creation')
    for k,v in report.items(): print(f'- {k}: **{v}**' if not isinstance(v,list) else f'- {k}: {v}')

if __name__=='__main__': main()
