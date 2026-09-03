#!/usr/bin/env python3
from __future__ import annotations
import base64, html, json, os, re, urllib.parse, urllib.request

SITE='https://tsurikue.com'
BASE=SITE+'/wp-json/wp/v2'
PAGE_SLUG='odekake'
PAGE_TITLE='おでかけ'
TAG_NAME='ちょっと遠くへ'
MARK='<!-- tq-outing-far-tag-link:v1 -->'
LINK_CLASS='tq-far-tag-link'
USER_AGENT='tsurikue-outing-far-tag-link/1.0'


def auth_header():
    u=os.environ['TSURIKUE_WP_USER']; p=os.environ['TSURIKUE_WP_APP_PASSWORD']
    return 'Basic '+base64.b64encode(f'{u}:{p}'.encode()).decode()


def req(path,method='GET',payload=None):
    headers={'Authorization':auth_header(),'Accept':'application/json','User-Agent':USER_AGENT}
    data=None
    if payload is not None:
        data=json.dumps(payload,ensure_ascii=False).encode('utf-8')
        headers['Content-Type']='application/json; charset=utf-8'
    r=urllib.request.Request(BASE+path,data=data,headers=headers,method=method)
    with urllib.request.urlopen(r,timeout=60) as x:
        return json.loads(x.read().decode()),dict(x.headers)


def clean(v):
    if isinstance(v,dict): v=v.get('raw') or v.get('rendered') or ''
    return html.unescape(re.sub(r'<[^>]+>','',v or '')).strip()


def published_counts():
    out={}
    for ep in ('posts','pages'):
        _,h=req(f'/{ep}?status=publish&per_page=1&_fields=id')
        out[ep]=int(h.get('X-WP-Total','0'))
    return out


def exact_live_page():
    q=urllib.parse.urlencode({'context':'edit','slug':PAGE_SLUG,'status':'publish','per_page':10,'_fields':'id,slug,status,title,content,link'})
    rows,_=req('/pages?'+q)
    if len(rows)!=1: raise RuntimeError(f'LIVE_PAGE_MATCHES={len(rows)}')
    row=rows[0]
    if clean(row.get('title'))!=PAGE_TITLE: raise RuntimeError('LIVE_PAGE_TITLE_MISMATCH')
    return row


def exact_far_tag():
    q=urllib.parse.urlencode({'context':'edit','search':TAG_NAME,'per_page':100,'hide_empty':False,'_fields':'id,name,slug,count'})
    rows,_=req('/tags?'+q)
    rows=[r for r in rows if clean(r.get('name'))==TAG_NAME]
    if len(rows)!=1: raise RuntimeError(f'FAR_TAG_MATCHES={len(rows)}')
    return rows[0]


def patch_content(raw,tag_slug):
    tag_url=f'{SITE}/tag/{tag_slug}/'
    if MARK in raw:
        if tag_url not in raw or LINK_CLASS not in raw: raise RuntimeError('MARKER_PRESENT_BUT_LINK_INVALID')
        return raw,tag_url,False
    if raw.count('tq-accordion-far')<2: raise RuntimeError('FAR_ACCORDION_NOT_FOUND')
    details=re.search(r'(<details class="wp-block-details tq-accordion tq-accordion-far">.*?</details><!-- /wp:details -->)',raw,re.S)
    if not details: raise RuntimeError('FAR_DETAILS_BLOCK_NOT_FOUND')
    block=details.group(1)
    close='</details><!-- /wp:details -->'
    link=(f'\n{MARK}\n<!-- wp:paragraph {{"className":"{LINK_CLASS}"}} -->'
          f'<p class="{LINK_CLASS}"><a href="{tag_url}">「ちょっと遠くへ」の記事を全部見る →</a></p>'
          '<!-- /wp:paragraph -->\n')
    if close not in block: raise RuntimeError('FAR_CLOSE_NOT_FOUND')
    newblock=block.replace(close,link+close,1)
    patched=raw[:details.start()]+newblock+raw[details.end():]
    if patched.count(MARK)!=1 or patched.count(tag_url)!=1: raise RuntimeError('PATCH_VALIDATION_FAILED')
    return patched,tag_url,True


def verify_public(tag_url):
    with urllib.request.urlopen(SITE+'/odekake/?tq_far_tag_link=1',timeout=60) as r:
        page=r.read().decode('utf-8','ignore')
    if tag_url not in page or '「ちょっと遠くへ」の記事を全部見る' not in page:
        raise RuntimeError('PUBLIC_ODEKAKE_LINK_NOT_RENDERED')
    with urllib.request.urlopen(tag_url,timeout=60) as r:
        if getattr(r,'status',200)!=200: raise RuntimeError('TAG_ARCHIVE_NOT_200')


def main():
    before=published_counts(); page=exact_live_page(); tag=exact_far_tag()
    raw=(page.get('content') or {}).get('raw') or ''
    patched,tag_url,changed=patch_content(raw,tag['slug'])
    writes=0
    if changed:
        req(f"/pages/{page['id']}",method='POST',payload={'content':patched}); writes=1
    after=exact_live_page(); after_raw=(after.get('content') or {}).get('raw') or ''
    if after_raw.count(MARK)!=1 or tag_url not in after_raw or after.get('status')!='publish':
        raise RuntimeError('POSTWRITE_VERIFICATION_FAILED')
    after_counts=published_counts()
    if after_counts!=before: raise RuntimeError(f'PUBLIC_COUNTS_CHANGED {before} -> {after_counts}')
    verify_public(tag_url)
    report={'ok':True,'action':'ADD_OUTING_FAR_TAG_ARCHIVE_LINK','page_id':page['id'],'page_slug':PAGE_SLUG,'tag_id':tag['id'],'tag_slug':tag['slug'],'tag_count':tag.get('count'),'tag_url':tag_url,'wordpress_write_count':writes,'public_before':before,'public_after':after_counts}
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
