#!/usr/bin/env python3
"""Transfer owner's 15 web-optimized photos from integrity-checked Git blobs to WordPress draft 4138.

PR check = no writes, main apply = media upload + content-only edit. Existing editor changes block update.
Git blobs are not committed to repo tree; source JPEGs were staged as ZIP chunks with SHA checks.
"""
import base64, hashlib, html, io, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request, zipfile
from pathlib import Path

SITE='https://tsurikue.com'; REPO='kandatasan/norisan-article-salvage'
PID=4138; SLUG='sakaiminato-station-sightseeing'
MANIFEST=Path('assets/manifest/sakaiminato-photos15-20261013.json')
REVISION=Path('content/revisions/sakaiminato-station-20261013-info-tables.json')
SLOT=re.compile(r'<!-- TSURIKUE_IMAGE:([^|<>]+)\|([^|<>]+)\|([^<>]+) -->')

def sha(x):return hashlib.sha256(x).hexdigest()
def request(url,headers=None,body=None,method='GET',tries=4):
    req=urllib.request.Request(url,data=body,method=method,headers=headers or {})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req,timeout=70) as response:
                raw=response.read()
                return json.loads(raw),dict(response.headers)
        except (urllib.error.URLError,TimeoutError) as ex:
            # IMPORTANT: never blindly repeat an uncertain POST (might have succeeded).
            if method!='GET' or attempt==tries-1:raise
            print('RETRY_GET_TRANSIENT',str(ex)[:160],attempt+1,flush=True)
            time.sleep(2*(attempt+1))
        except urllib.error.HTTPError as ex:
            if method!='GET' or ex.code not in (429,502,503,504) or attempt==tries-1:raise
            print('RETRY_GET_HTTP',ex.code,attempt+1,flush=True)
            time.sleep(2*(attempt+1))


def github_zip():
    manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
    token=os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    if not token:raise RuntimeError('Missing GitHub read token')
    header={'Accept':'application/vnd.github+json','Authorization':'Bearer '+token,
            'X-GitHub-Api-Version':'2022-11-28','User-Agent':'tsurikue-media-uploader'}
    buf=io.BytesIO()
    for p in manifest['parts']:
        url=f'https://api.github.com/repos/{REPO}/git/blobs/{p["blob_sha"]}'
        obj,_=request(url,headers=header)
        if obj.get('encoding')!='base64':raise RuntimeError('Git object not base64')
        chunk=base64.b64decode(''.join(obj['content'].split()),validate=True)
        if len(chunk)!=p['length'] or sha(chunk)!=p['sha256']:
            raise RuntimeError('Git image archive chunk checksum mismatch')
        buf.write(chunk)
    data=buf.getvalue()
    if len(data)!=manifest['bundle_bytes'] or sha(data)!=manifest['bundle_sha256']:
        raise RuntimeError('Assembled photo archive checksum mismatch')
    print('PHOTO_ARCHIVE_CHECKED',len(data),len(manifest['parts']),flush=True)
    with zipfile.ZipFile(io.BytesIO(data)) as arc:
        blobs={n:arc.read(n) for n in arc.namelist() if n.endswith('.jpeg')}
    if len(blobs)!=15:raise RuntimeError(f'Expected exactly 15 user photos; found {len(blobs)}')
    for n,data in blobs.items():
        if not data.startswith(b'\xff\xd8') or not data.endswith(b'\xff\xd9'):
            raise RuntimeError('Malformed JPEG '+n)
    return blobs


def wp_headers():
    user=os.getenv('TSURIKUE_WP_USER');password=os.getenv('TSURIKUE_WP_APP_PASSWORD')
    if not user or not password:raise RuntimeError('WordPress secrets missing')
    token=base64.b64encode((user+':'+password).encode()).decode()
    return {'Authorization':'Basic '+token,'Accept':'application/json',
            'User-Agent':'tsurikue-sakaiminato-owner-photo-uploader/1.0'}

def wp_get(path,headers):
    obj,_=request(SITE+path,headers)
    return obj

def wp_post(path,headers,body,content_type='application/json; charset=utf-8',extra_headers=None):
    hs=dict(headers);hs['Content-Type']=content_type
    if extra_headers:hs.update(extra_headers)
    return request(SITE+path,headers=hs,method='POST',body=body,tries=1)[0]

def fetch_post(headers):
    q=urllib.parse.urlencode({'context':'edit','_fields':'id,slug,status,title,categories,author,featured_media,content'})
    return wp_get('/wp-json/wp/v2/posts/'+str(PID)+'?'+q,headers)

def validate_live(post,doc,expected_raw):
    if (post['id'],post['slug'],post['status'])!=(PID,SLUG,'draft'):
        raise RuntimeError('Wrong post identity; do not change other posts')
    if post['title']['raw']!=doc['title'] or post['categories']!=[7]:
        raise RuntimeError('Title/category mismatch')
    if post['content']['raw']!=expected_raw:
        raise RuntimeError('Draft was edited by someone since last saved revision: abort to avoid overwrite')

def media_lookup(headers,index):
    prefix=f'tsurikue-sakaiminato-4138-{index:02d}'
    q=urllib.parse.urlencode({'context':'edit','search':prefix,'per_page':100,'_fields':'id,source_url,slug,mime_type,alt_text'})
    rows=wp_get('/wp-json/wp/v2/media?'+q,headers)
    matches=[]
    for row in rows:
        filename=urllib.parse.unquote(urllib.parse.urlsplit(row.get('source_url','')).path.rsplit('/',1)[-1])
        if filename==prefix+'.jpg' and row.get('mime_type')=='image/jpeg':matches.append(row)
    if len(matches)>1:raise RuntimeError('Ambiguous media for '+prefix)
    return matches[0] if matches else None

def upload_image(headers,index,filename,bytes_,alt,caption):
    uploaded_name=f'tsurikue-sakaiminato-4138-{index:02d}.jpg'
    existing=media_lookup(headers,index)
    if existing:
        data=existing
        print('REUSE_EXISTING_WP_MEDIA',index,data['id'],flush=True)
    else:
        try:
            data=wp_post('/wp-json/wp/v2/media',headers,bytes_,content_type='image/jpeg',
                 extra_headers={'Content-Disposition':'attachment; filename="'+uploaded_name+'"'})
        except Exception as e:
            # POST may have completed despite timeout: lookup before stopping.
            data=media_lookup(headers,index)
            if data is None:raise RuntimeError(f'Media upload #{index} failed, no draft edit performed: {str(e)}')
        print('UPLOADED_WP_MEDIA',index,data['id'],filename,flush=True)
    url=data['source_url']
    if urllib.parse.urlsplit(url).hostname!='tsurikue.com' or '/wp-content/uploads/' not in url:
        raise RuntimeError('Uploaded media has unexpected origin '+url[:250])
    # Give the WordPress media a meaningful and accessible description.
    m=wp_post('/wp-json/wp/v2/media/'+str(data['id']),headers,
        json.dumps({'alt_text':alt,'caption':caption},ensure_ascii=False).encode())
    if m['id']!=data['id'] or m.get('alt_text')!=alt:
        raise RuntimeError('Uploaded media metadata could not be verified')
    return {'id':data['id'],'url':url}

def build_body(old,slots,medias):
    pairs=[];out=old
    for i,(filename,alt,caption) in enumerate(slots,1):
        media=medias[filename]
        mid=media['id']; src=html.escape(media['url'],quote=True)
        elt=(f'<!-- wp:image {{"id":{mid},"sizeSlug":"full","linkDestination":"none"}} -->\n'
             f'<figure class="wp-block-image size-full"><img src="{src}" alt="{html.escape(alt,quote=True)}" class="wp-image-{mid}"/>'
             f'<figcaption class="wp-element-caption">{html.escape(caption)}</figcaption></figure>\n'
             f'<!-- /wp:image -->')
        needle=f'<!-- TSURIKUE_IMAGE:{filename}|{alt}|{caption} -->'
        if out.count(needle)!=1:raise RuntimeError('Image slot missing/duplicate '+filename)
        out=out.replace(needle,elt,1)
        pairs.append((filename,mid))
    if SLOT.findall(out):raise RuntimeError('Image slots remain')
    if len(re.findall(r'wp-image-\d+',out))!=15:raise RuntimeError('Wrong number of embedded WP images')
    if out.count('<!-- wp:table')!=2 or '金運' not in out or '摩尼車' not in out:
        raise RuntimeError('Draft informational tables or firsthand stories altered')
    if out.count('<!-- wp:image')!=15 or out.count('<!-- /wp:image -->')!=15:
        raise RuntimeError('Gutenberg image blocks unbalanced')
    return out,pairs

def main(mode):
    doc=json.loads(REVISION.read_text(encoding='utf-8'))
    if doc['status']!='draft' or doc['slug']!=SLUG:
        raise RuntimeError('Unexpected revision metadata')
    original='\n\n'.join(doc['blocks'])
    slots=SLOT.findall(original)
    if len(slots)!=15 or [f for f,_,_ in slots]!=doc['images_expected']:
        raise RuntimeError('Photograph captions, source manifest or ordering mismatch')
    photo_zip=github_zip()
    if sorted(photo_zip)!=sorted(doc['images_expected']):
        raise RuntimeError('Archive does not match exact approved photo slots')
    headers=wp_headers()
    live=fetch_post(headers)
    validate_live(live,doc,original)
    print('WP_READONLY_PHOTO_PREFLIGHT_OK',json.dumps({
       'post_id':PID,'status':live['status'],'photo_count':len(slots),
       'article_raw_sha256':sha(original.encode()),'source':'user-supplied optimized photo archive'
    }),flush=True)
    if mode=='check':return
    medias={}
    for i,(filename,alt,caption) in enumerate(slots,1):
        medias[filename]=upload_image(headers,i,filename,photo_zip[filename],alt,caption)
    new,pairs=build_body(original,slots,medias)
    current=fetch_post(headers)
    validate_live(current,doc,original)
    # If all 15 uploads worked, update post CONTENT only. No status or other post metadata touched.
    wp_post('/wp-json/wp/v2/posts/'+str(PID),headers,
        json.dumps({'content':new},ensure_ascii=False).encode())
    saved=fetch_post(headers)
    for field in ('id','slug','status','title','categories','author','featured_media'):
        if saved[field]!=live[field]:raise RuntimeError('Protected post field changed: '+field)
    if saved['content']['raw']!=new:raise RuntimeError('Saved WordPress content differs from approved replacement')
    if len(re.findall(r'wp-image-\d+',saved['content']['raw']))!=15:
        raise RuntimeError('WordPress raw photo count mismatch')
    if saved['content']['rendered'].count('<img')<15:
        raise RuntimeError('WordPress image blocks were not rendered')
    print('FINAL_SAKAIMINATO_IMAGES_VERIFIED',json.dumps({
        'post_id':PID,'slug':SLUG,'status':saved['status'],
        'images':[{'source_filename':n,'wp_media_id':mid} for n,mid in pairs],
        'article_raw_sha256':sha(new.encode()),
        'edit_url':SITE+'/wp-admin/post.php?post=4138&action=edit'
    },ensure_ascii=False),flush=True)

if __name__=='__main__':
    mode=sys.argv[1] if len(sys.argv)>1 else 'check'
    if mode not in ('check','apply'):raise SystemExit('usage: check|apply')
    main(mode)
