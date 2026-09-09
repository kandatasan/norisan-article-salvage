#!/usr/bin/env python3
from __future__ import annotations
import base64, html, json, os, re, urllib.parse, urllib.request
from pathlib import Path

SITE='https://tsurikue.com'
UA='tsurikue-verify-karato-market-20260909/1.0'
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
  981:'/wp-content/uploads/2026/05/img_2079.jpg',
  1092:'/wp-content/uploads/2026/05/img_2320.jpg',
  1086:'/wp-content/uploads/2026/05/img_2321.jpg',
  1111:'/wp-content/uploads/2026/05/img_2322.jpg',
  1083:'/wp-content/uploads/2026/05/img_2324.jpg',
  1109:'/wp-content/uploads/2026/05/img_2325.jpg',
  969:'/wp-content/uploads/2026/05/img_2066.jpg',
  983:'/wp-content/uploads/2026/05/img_2078.jpg',
}
BODY_MEDIA=set(EXPECTED_MEDIA)-{FEATURED}
TOKEN=re.compile(r'<!--\s+/?wp:[\s\S]*?-->')
OPEN=re.compile(r'<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->')
CLOSE=re.compile(r'<!--\s+/wp:([\w\-/]+)\s+-->')
IMAGE_ID=re.compile(r'wp-image-(\d+)')


def auth():
    user=os.environ.get('TSURIKUE_WP_USER'); pw=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
    if not user or not pw: raise SystemExit('BLOCKED_MISSING_SECRETS')
    return 'Basic '+base64.b64encode(f'{user}:{pw}'.encode()).decode()


def get(url, timeout=60):
    req=urllib.request.Request(url,headers={'Authorization':auth(),'Accept':'application/json','User-Agent':UA},method='GET')
    with urllib.request.urlopen(req,timeout=timeout) as resp:
        return json.loads(resp.read().decode()),dict(resp.headers)


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


def resolve(endpoint,slug):
    q=urllib.parse.urlencode({'context':'edit','slug':slug,'per_page':10,'_fields':'id,slug,name'})
    rows,_=get(f'{SITE}/wp-json/wp/v2/{endpoint}?{q}',45)
    if len(rows)!=1: raise RuntimeError(f'term lookup failed: {endpoint}/{slug}')
    return int(rows[0]['id'])


def count_published(endpoint):
    q=urllib.parse.urlencode({'status':'publish','per_page':1,'_fields':'id'})
    _,h=get(f'{SITE}/wp-json/wp/v2/{endpoint}?{q}',45)
    return int(h.get('X-WP-Total','0'))


def main():
    expected=CONTENT_PATH.read_text(encoding='utf-8').strip()
    q=urllib.parse.urlencode({'context':'edit','slug':SLUG,'status':'any','per_page':10,'_fields':'id,slug,status,link,title,content,featured_media,categories,tags,excerpt'})
    rows,_=get(f'{SITE}/wp-json/wp/v2/posts?{q}',60)
    if len(rows)!=1: raise RuntimeError(f'expected exactly one slug match, got {len(rows)}')
    row=rows[0]; content=raw(row,'content').strip()
    categories=[resolve('categories',x) for x in CATEGORY_SLUGS]
    tags=[resolve('tags',x) for x in TAG_SLUGS]
    if row.get('status')!='draft' or row.get('slug')!=SLUG: raise RuntimeError('draft identity mismatch')
    if html.unescape(raw(row,'title'))!=TITLE: raise RuntimeError('title mismatch')
    if content!=expected: raise RuntimeError('content differs from package')
    if int(row.get('featured_media') or 0)!=FEATURED: raise RuntimeError('featured mismatch')
    if sorted(row.get('categories') or [])!=sorted(categories) or sorted(row.get('tags') or [])!=sorted(tags): raise RuntimeError('taxonomy mismatch')
    if '<h1' in content.lower() or gutenberg_problems(content)!=0: raise RuntimeError('body structure failed')
    used={int(x) for x in IMAGE_ID.findall(content)}
    if used!=BODY_MEDIA: raise RuntimeError(f'body media mismatch: {sorted(used)}')
    for mid,path in EXPECTED_MEDIA.items():
        mq=urllib.parse.urlencode({'context':'edit','_fields':'id,status,source_url'})
        media,_=get(f'{SITE}/wp-json/wp/v2/media/{mid}?{mq}',45)
        actual=urllib.parse.unquote(urllib.parse.urlparse(media.get('source_url') or '').path)
        if media.get('id')!=mid or actual.casefold()!=path.casefold(): raise RuntimeError(f'media mismatch: {mid}')
    required_links=['https://tsurikue.com/yamaguchi-drive/','https://tsurikue.com/tsunoshima/','https://tsurikue.com/hiroshima-oita-1night-2days-drive/','https://www.karatoichiba.com/calendars/','https://www.karatoichiba.com/bakangai/','https://www.kaikyokan.com/access.php','https://maps.app.goo.gl/wR2vtdajgw2kPA9o6?g_st=ic','https://maps.app.goo.gl/SLQJDZufufpfnp5B9?g_st=ic']
    for link in required_links:
        if link not in content: raise RuntimeError(f'missing link: {link}')
    report={
      'result':'VERIFIED','post_id':int(row['id']),'slug':SLUG,'status':'draft','title':TITLE,
      'featured_media':FEATURED,'category_ids':categories,'tag_ids':tags,
      'media_checked':len(EXPECTED_MEDIA),'body_images':len(BODY_MEDIA),'gutenberg_problems':0,
      'internal_links':3,'official_info_links':3,'google_maps_links':2,
      'published_posts_now':count_published('posts'),'published_pages_now':count_published('pages'),
      'wordpress_write_count':0,'publish_count':0,'media_upload_count':0
    }
    print('# Karato Market authenticated GET verification')
    for k,v in report.items(): print(f'- {k}: **{v}**')

if __name__=='__main__': main()
