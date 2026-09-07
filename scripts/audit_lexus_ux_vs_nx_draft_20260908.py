#!/usr/bin/env python3
import base64, json, os, urllib.parse, urllib.request

SITE='https://tsurikue.com'
UA='tsurikue-ux-vs-nx-audit/1.0'
ISSUE=435


def auth():
    u=os.environ.get('TSURIKUE_WP_USER'); p=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
    if not u or not p: raise SystemExit('BLOCKED_MISSING_SECRETS')
    return 'Basic '+base64.b64encode(f'{u}:{p}'.encode()).decode()

def get(url,a):
    r=urllib.request.Request(url,headers={'Accept':'application/json','Authorization':a,'User-Agent':UA},method='GET')
    with urllib.request.urlopen(r,timeout=50) as x: return json.loads(x.read().decode()), dict(x.headers)

def q(path,params,a):
    return get(f"{SITE}/wp-json/wp/v2/{path}?{urllib.parse.urlencode(params, doseq=True)}",a)

def raw(row,key):
    v=row.get(key) or {}
    return (v.get('raw') or v.get('rendered') or '') if isinstance(v,dict) else str(v)

def main():
    a=auth(); out=[]
    out += ['# Audit: Lexus UX vs NX new draft (GET only)','- wordpress_write_count: **0**','']
    for slug in ['lexus-ux-vs-nx','lexus-ux-nx','ux-vs-nx','lexus-ux-nx-comparison']:
        rows,_=q('posts',{'context':'edit','status':'any','slug':slug,'per_page':20,'_fields':'id,slug,status,title,link'},a)
        out.append(f"- slug `{slug}` collisions: {[(r['id'],r['status'],raw(r,'title')) for r in rows]}")
    rows,_=q('posts',{'context':'edit','status':'any','search':'レクサスUX NX','per_page':50,'_fields':'id,slug,status,title,link'},a)
    out.append(f"- search `レクサスUX NX`: {[(r['id'],r['slug'],r['status'],raw(r,'title')) for r in rows]}")
    out.append('')

    slugs=['lexus-ux-review','ux300h','lexus-ux-size','lexus-ux-rear-seat','lexus-ux-cargo','lexus-ux-used','lexus-ux250h-used-vs-ux300h']
    for slug in slugs:
        rows,_=q('posts',{'context':'edit','status':'any','slug':slug,'per_page':5,'_fields':'id,slug,status,title,featured_media,categories,tags,content'},a)
        if not rows:
            out.append(f"## {slug}: NOT FOUND"); continue
        r=rows[0]
        out += [f"## {r['id']} {slug} — {raw(r,'title')}",f"- status: {r['status']} / featured_media: {r.get('featured_media')} / categories: {r.get('categories')} / tags: {r.get('tags')}"]
        c=raw(r,'content')
        mids=[]
        import re
        for m in re.findall(r'wp-image-(\d+)',c):
            i=int(m)
            if i not in mids: mids.append(i)
        out.append(f"- media ids in content: {mids[:20]}")
        out.append('')

    out.append('## Candidate media')
    for mid in [2197,2223,2231,2330,2244,2952,1624,1352]:
        try:
            row,_=get(f'{SITE}/wp-json/wp/v2/media/{mid}?context=edit&_fields=id,slug,status,title,caption,alt_text,source_url,media_details',a)
            md=row.get('media_details') or {}
            out.append(f"- {mid}: {md.get('width')}x{md.get('height')} slug=`{row.get('slug')}` title=`{raw(row,'title')}` alt=`{row.get('alt_text') or ''}` caption=`{raw(row,'caption')}` url={row.get('source_url')}")
        except Exception as e:
            out.append(f"- {mid}: ERROR {e}")

    out.append('')
    out.append('## Category/tag metadata')
    for typ,ids in [('categories',[10,11]),('tags',[36,37,42])]:
        for i in ids:
            try:
                r,_=get(f'{SITE}/wp-json/wp/v2/{typ}/{i}?context=edit&_fields=id,name,slug,parent,count',a)
                out.append(f"- {typ[:-1]} {i}: {r}")
            except Exception as e: out.append(f"- {typ[:-1]} {i}: ERROR {e}")

    print('\n'.join(out))

if __name__=='__main__': main()
