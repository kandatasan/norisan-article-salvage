#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, os, urllib.parse, urllib.request

SITE='https://tsurikue.com'
MEDIA_ID=3177
EXPECTED_PATH='/wp-content/uploads/2026/09/img_2419.jpg'
USER=os.environ['TSURIKUE_WP_USER']
APP=os.environ['TSURIKUE_WP_APP_PASSWORD']
AUTH='Basic '+base64.b64encode(f'{USER}:{APP}'.encode()).decode()
H={'Authorization':AUTH,'Accept':'application/json','User-Agent':'tsurikue-outing-hero-media-audit/1.1'}


def get(path, params=None):
    if params:
        path += '?' + urllib.parse.urlencode(params)
    req=urllib.request.Request(SITE+path,headers=H,method='GET')
    with urllib.request.urlopen(req,timeout=60) as r:
        return json.loads(r.read().decode()),dict(r.headers)

media,_=get(f'/wp-json/wp/v2/media/{MEDIA_ID}',{
    'context':'edit','_fields':'id,date,slug,source_url,mime_type,media_details,title'
})
source=urllib.parse.urlparse(media.get('source_url') or '').path
details=media.get('media_details') or {}
if int(media.get('id') or 0)!=MEDIA_ID or source.casefold()!=EXPECTED_PATH.casefold():
    raise RuntimeError('DOLPHIN_MEDIA_MISMATCH '+json.dumps({'id':media.get('id'),'path':source},ensure_ascii=False))
if not str(media.get('mime_type') or '').startswith('image/'):
    raise RuntimeError('DOLPHIN_MEDIA_NOT_IMAGE')

page3154,_=get('/wp-json/wp/v2/pages/3154',{'context':'edit','_fields':'id,slug,status,title,content,link'})
raw=(page3154.get('content') or {}).get('raw') or ''
if page3154.get('id')!=3154 or page3154.get('slug')!='odekake' or page3154.get('status')!='publish':
    raise RuntimeError('OUTING_PAGE_IDENTITY_MISMATCH')
print(json.dumps({
    'mode':'READ_ONLY',
    'dolphin_media':{
        'id':MEDIA_ID,'source_url':media.get('source_url'),'path':source,
        'mime_type':media.get('mime_type'),'width':details.get('width'),'height':details.get('height'),
        'slug':media.get('slug'),'title':media.get('title')
    },
    'outing_page':{
        'id':page3154.get('id'),'slug':page3154.get('slug'),'status':page3154.get('status'),'link':page3154.get('link'),
        'content_sha256':hashlib.sha256(raw.encode()).hexdigest()
    },
    'current_hero_4588':'img_4588.jpg' in raw,
    'current_hero_2419':'img_2419.jpg' in raw,
    'wordpress_write_count':0
},ensure_ascii=False,indent=2))
