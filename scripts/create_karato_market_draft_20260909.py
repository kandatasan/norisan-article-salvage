#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, os, re, time, urllib.parse, urllib.request
from pathlib import Path

SITE='https://tsurikue.com'
UA='tsurikue-create-karato-market-20260909/1.0'
TITLE='唐戸市場で何食べる？おすすめは一本アナゴとマグロの脳天｜寿司・ふぐも紹介'
SLUG='karato-market'
CONTENT_PATH=Path('packages/karato-market/content.html')
FEATURED=1023
CATEGORY_SLUGS=['sightseeing-leisure']
TAG_SLUGS=['yamaguchi','road-trip']
EXPECTED_MEDIA={
  1023:'/wp-content/uploads/2026/05/img_2149.jpg',
  1003:'/wp-content/uploads/2026/05/img_2101.jpg',
  992:'/wp-content/uploads/2026/05/img_2074.jpg',
  979:'/wp-content/uploads/2026/05/img_2075.jpg',
  980:'/wp-content/uploads/2026/05/img_2076.jpg',
  982:'/wp-content/uploads/2026/05/img_2077.jpg',
  981:'/wp-content/uploads/2026/05/img_2079.jpg',
  1092:'/wp-content/uploads/2026/05/img_2320.jpg',
  1086:'/wp-content/uploads/2026/05/img_2321.jpg',
  1111:'/wp-content/uploads/2026/05/img_2322.jpg',
  1083:'/wp-content/uploads/2026/05/img_2324.jpg',
  1109:'/wp-content/uploads/2026/05/img_2325.jpg',
  969:'/wp-content/uploads/2026/05/img_2066.jpg',
  983:'/wp-content/uploads/2026/05/img_2078.jpg',
}
BODY_MEDIA=set(EXPECTED_MEDIA)-{FEATURED,982}
TOKEN=re.compile(r'<!--\s+/?wp:[\s\S]*?-->')
OPEN=re.compile(r'<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->')
CLOSE=re.compile(r'<!--\s+/wp:([\w\-/]+)\s+-->')
IMAGE_ID=re.compile(r'wp-image-(\d+)')


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
            with urllib.request.urlopen(r,timeout=timeout) as resp:
                return json.loads(resp.read().decode()),dict(resp.headers)
        except Exception as e:
            last=e
            if n<2: time.sleep(3*(n+1))
    raise last


def raw(row,key):
    v=row.get(key) or {}
    return (v.get('raw') or v.get('rendered') or '') if isinstance(v,dict) else str(v)


def gutenberg_problems(text):
    stack=[]
    for m in TOKEN.finditer(text):
        t=m.group(0); o=OPEN.fullmatch(t); c=CLOSE.fullmatch(t)
        if o:
            if not o.group(2): stack.append(o.group(1))
        elif c:
            if not stack or stack[-1]!=c.group(1): return 1
            stack.pop()
    return len(stack)


def count_published(endpoint):
    q=urllib.parse.urlencode({'status':'publish','per_page':1,'_fields':'id'})
    _,h=req(f'{SITE}/wp-json/wp/v2/{endpoint}?{q}',timeout=45)
    return int(h.get('X-WP-Total','0'))


def public_counts():
    p=count_published('posts'); g=count_published('pages')
    return {'published_posts':p,'published_pages':g,'published_total':p+g}


def resolve_term(endpoint,slug):
    q=urllib.parse.urlencode({'context':'edit','slug':slug,'per_page':10,'_fields':'id,slug,name'})
    rows,_=req(f'{SITE}/wp-json/wp/v2/{endpoint}?{q}',timeout=45)
    if len(rows)!=1 or rows[0].get('slug')!=slug:
        raise RuntimeError(f'term resolution failed endpoint={endpoint} slug={slug}: {rows}')
    return int(rows[0]['id'])


def validate_media():
    for mid,path in EXPECTED_MEDIA.items():
        q=urllib.parse.urlencode({'context':'edit','_fields':'id,status,source_url'})
        row,_=req(f'{SITE}/wp-json/wp/v2/media/{mid}?{q}',timeout=45)
        actual=urllib.parse.unquote(urllib.parse.urlparse(row.get('source_url') or '').path)
        if row.get('id')!=mid or actual.casefold()!=path.casefold():
            raise RuntimeError(f'media mismatch id={mid}: {actual} != {path}')


def find_existing():
    q=urllib.parse.urlencode({'context':'edit','slug':SLUG,'status':'any','per_page':10,'_fields':'id,slug,status,title,content,featured_media,categories,tags,excerpt'})
    rows,_=req(f'{SITE}/wp-json/wp/v2/posts?{q}',timeout=45)
    return rows


def main():
    content=CONTENT_PATH.read_text(encoding='utf-8').strip()+'\n'
    if '<h1' in content.lower(): raise RuntimeError('body h1 is forbidden')
    if gutenberg_problems(content)!=0: raise RuntimeError('Gutenberg block balance failed')
    for phrase in ['一本アナゴ','マグロの脳天','脳みそではありません','クエまで','巣って、溶けないのね','活きいき馬関街','海響館が目の前','/yamaguchi-drive/','/tsunoshima/','/hiroshima-oita-1night-2days-drive/']:
        if phrase not in content: raise RuntimeError(f'missing required phrase: {phrase}')
    if '😏' in content or '🔥' in content or '🤣' in content: raise RuntimeError('emoji in article body')
    used={int(x) for x in IMAGE_ID.findall(content)}
    if used!=BODY_MEDIA: raise RuntimeError(f'body media mismatch used={sorted(used)} expected={sorted(BODY_MEDIA)}')
    validate_media()
    categories=[resolve_term('categories',x) for x in CATEGORY_SLUGS]
    tags=[resolve_term('tags',x) for x in TAG_SLUGS]
    before=public_counts()
    existing=find_existing()
    action='CREATE'
    if existing:
        if len(existing)!=1: raise RuntimeError(f'multiple slug collisions: {len(existing)}')
        row=existing[0]
        same=(row.get('status')=='draft' and html.unescape(raw(row,'title'))==TITLE and raw(row,'content').strip()==content.strip() and int(row.get('featured_media') or 0)==FEATURED and sorted(row.get('categories') or [])==sorted(categories) and sorted(row.get('tags') or [])==sorted(tags))
        if not same: raise RuntimeError(f'slug already exists but differs: id={row.get("id")} status={row.get("status")}')
        created=row; action='ALREADY_UP_TO_DATE'
    else:
        payload={
          'title':TITLE,'slug':SLUG,'content':content,'status':'draft','featured_media':FEATURED,
          'categories':categories,'tags':tags,
          'excerpt':'唐戸市場で実際に食べておすすめしたいのは、丸ごと一本のアナゴとマグロの脳天。寿司・ふぐ・クエまで並ぶ市場の雰囲気、巣蜜つき蜂蜜ソフト、海響館とセットで回りやすい駐車場まで写真多めで紹介します。'
        }
        created,_=req(f'{SITE}/wp-json/wp/v2/posts',method='POST',payload=payload,timeout=90)
        if created.get('status')!='draft' or created.get('slug')!=SLUG:
            raise RuntimeError('create response validation failed')
    pid=int(created['id'])
    q=urllib.parse.urlencode({'context':'edit','_fields':'id,slug,status,link,title,content,featured_media,categories,tags,excerpt'})
    after,_=req(f'{SITE}/wp-json/wp/v2/posts/{pid}?{q}',timeout=60)
    after_counts=public_counts()
    if before!=after_counts: raise RuntimeError(f'published counts changed: {before} -> {after_counts}')
    if after.get('id')!=pid or after.get('slug')!=SLUG or after.get('status')!='draft': raise RuntimeError('post state mismatch')
    if html.unescape(raw(after,'title'))!=TITLE or raw(after,'content').strip()!=content.strip(): raise RuntimeError('title/content mismatch')
    if int(after.get('featured_media') or 0)!=FEATURED: raise RuntimeError('featured media mismatch')
    if sorted(after.get('categories') or [])!=sorted(categories) or sorted(after.get('tags') or [])!=sorted(tags): raise RuntimeError('taxonomy mismatch')
    report={
      'result':'SUCCESS','action':action,'post_id':pid,'slug':SLUG,'status':'draft','title':TITLE,
      'featured_media':FEATURED,'categories':categories,'tags':tags,'media_checked':len(EXPECTED_MEDIA),
      'body_images':len(BODY_MEDIA),'gutenberg_problems':0,
      'published_before':before,'published_after':after_counts,
      'content_sha256':hashlib.sha256(raw(after,'content').encode()).hexdigest(),
      'wordpress_write_count':1 if action=='CREATE' else 0,'publish_count':0,'media_upload_count':0
    }
    print('# New Karato Market draft creation')
    for k,v in report.items(): print(f'- {k}: **{v}**')

if __name__=='__main__': main()
