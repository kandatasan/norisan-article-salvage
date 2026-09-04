#!/usr/bin/env python3
from __future__ import annotations
import base64,json,os,re,urllib.parse,urllib.request

SITE='https://tsurikue.com'; BASE=SITE+'/wp-json/wp/v2'; POST_ID=3548
STEMS=['img_0021','img_0022','img_0024','img_0025','img_0027','img_0028','img_0029']
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()
H={'Authorization':AUTH,'Accept':'application/json','Content-Type':'application/json; charset=utf-8','User-Agent':'tsurikue-cadore-repair/1.0'}

def req(path,method='GET',payload=None):
    d=None if payload is None else json.dumps(payload,ensure_ascii=False).encode()
    r=urllib.request.Request(BASE+path,data=d,headers=H,method=method)
    with urllib.request.urlopen(r,timeout=60) as x:return json.loads(x.read().decode()),dict(x.headers)

def find_media():
    rows=[]
    for page in range(1,6):
        try:
            r,_=req('/media?'+urllib.parse.urlencode({'context':'edit','per_page':100,'page':page,'orderby':'date','order':'desc','_fields':'id,date,source_url,mime_type,slug,title'}))
            rows+=r
        except: break
    out={}
    for stem in STEMS:
        m=[x for x in rows if re.search(rf'/{stem}(?:-\d+)?\.(?:jpe?g|png|webp|mp4|mov)$',x.get('source_url',''),re.I)]
        if not m: raise RuntimeError('MEDIA_NOT_FOUND '+stem)
        # Prefer September 2026 upload and latest ID.
        sep=[x for x in m if x.get('date','').startswith('2026-09')]
        pick=sorted(sep or m,key=lambda x:int(x['id']))[-1]
        out[stem]=pick
    return out

def img_block(m,alt):
    return f'''<!-- wp:image {{"id":{m["id"]},"sizeSlug":"large","linkDestination":"none"}} -->
<figure class="wp-block-image size-large"><img src="{m["source_url"]}" alt="{alt}" class="wp-image-{m["id"]}"/></figure>
<!-- /wp:image -->'''

def video_block(m):
    return f'''<!-- wp:video {{"id":{m["id"]}}} -->
<figure class="wp-block-video"><video controls src="{m["source_url"]}"></video></figure>
<!-- /wp:video -->'''

def replace_first_image_after_intro(raw,newblock):
    pat=r'<!-- wp:image \{"id":1926[^>]*?-->.*?<!-- /wp:image -->'
    if re.search(pat,raw,re.S):
        return re.sub(pat,newblock,raw,count=1,flags=re.S)
    marker='<!-- wp:heading -->\n<h2 class="wp-block-heading">カドーレは動物との距離が近い</h2>'
    return raw.replace(marker,newblock+'\n\n'+marker,1)

def insert_after(raw,needle,block):
    if block in raw: return raw
    if needle not in raw: raise RuntimeError('MARKER_NOT_FOUND '+needle[:80])
    return raw.replace(needle,needle+'\n\n'+block,1)

def main():
    p,_=req(f'/posts/{POST_ID}?context=edit&_fields=id,status,content,featured_media,modified')
    if p['status']!='draft': raise RuntimeError('POST_NOT_DRAFT')
    raw=p['content']['raw']
    # Preserve user's manually added Fukutomi park image.
    if 'wp-image-3539' not in raw: raise RuntimeError('USER_FUKUTOMI_IMAGE_MISSING_BEFORE_UPDATE')
    m=find_media()

    raw=replace_first_image_after_intro(raw,img_block(m['img_0021'],'上ノ原牧場カドーレの外観'))

    h2_anim='<!-- wp:heading -->\n<h2 class="wp-block-heading">カドーレは動物との距離が近い</h2>\n<!-- /wp:heading -->'
    raw=insert_after(raw,h2_anim,img_block(m['img_0022'],'カドーレのもぐもぐ体験案内'))

    p_anim='<!-- wp:paragraph -->\n<p>牧場エリアでは牛をはじめ、動物たちを近くで見られます。</p>\n<!-- /wp:paragraph -->'
    raw=insert_after(raw,p_anim,img_block(m['img_0024'],'カドーレで牛を間近に見られる牧場エリア'))

    p_mogu='<!-- wp:paragraph -->\n<p>公式サイトでは、牛・ロバ・羊・ヤギ・うさぎへの<strong>「もぐもぐ体験」</strong>が案内されていて、エサは常時設置されています。</p>\n<!-- /wp:paragraph -->'
    raw=insert_after(raw,p_mogu,video_block(m['img_0025']))

    h2_g='<!-- wp:heading -->\n<h2 class="wp-block-heading">カドーレのジェラートは濃厚。でもしつこくない</h2>\n<!-- /wp:heading -->'
    raw=insert_after(raw,h2_g,img_block(m['img_0029'],'カドーレのジェラート売り場'))

    h2_s='<!-- wp:heading -->\n<h2 class="wp-block-heading">チーズ・ピザ・スイーツまである</h2>\n<!-- /wp:heading -->'
    raw=insert_after(raw,h2_s,img_block(m['img_0028'],'カドーレのチーズケーキ・スイーツ案内')+'\n\n'+img_block(m['img_0027'],'カドーレのスイーツ店舗'))

    req(f'/posts/{POST_ID}','POST',{'content':raw,'featured_media':int(m['img_0021']['id'])})
    v,_=req(f'/posts/{POST_ID}?context=edit&_fields=id,status,content,featured_media,modified')
    vr=v['content']['raw']
    checks={
        'draft':v['status']=='draft',
        'fukutomi_preserved':'wp-image-3539' in vr,
        'new_photos':all(f"wp-image-{m[s]['id']}" in vr for s in ['img_0021','img_0022','img_0024','img_0027','img_0028','img_0029']),
        'video':m['img_0025']['source_url'] in vr,
        'featured':v['featured_media']==int(m['img_0021']['id'])
    }
    if not all(checks.values()): raise RuntimeError('VERIFY_FAILED '+json.dumps(checks,ensure_ascii=False))
    print(json.dumps({'ok':True,'post_id':POST_ID,'modified':v['modified'],'media':{s:{'id':m[s]['id'],'date':m[s]['date'],'url':m[s]['source_url'],'mime':m[s].get('mime_type')} for s in STEMS},'checks':checks},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
