"""Guarded, additive photo and road-trip insertions to existing English Travel posts.
Only modifies post content; refuses stale/mismatched identities or photos.
"""
from __future__ import annotations
import hashlib
import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse, unquote

SITE = 'https://tsurikue.com'
MARKER = 'tsurikue-en-refresh-20261113'

def digest(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

def heading_block(content, heading):
    pat = re.compile(r'<!-- wp:heading(?: [^\n]*?)? -->\s*<h([23])\b[^>]*>\s*' + re.escape(heading) + r'\s*</h\1>\s*<!-- /wp:heading -->', re.S)
    hits = list(pat.finditer(content))
    if len(hits) != 1:
        raise RuntimeError(f'Expected one unique heading {heading!r}; found {len(hits)}')
    return hits[0]

def render_image(photo):
    id_ = int(photo['id'])
    path = photo['path']
    if not path.startswith('/wp-content/uploads/') or not re.search(r'\.(?:jpg|jpeg|png|webp)$', path, re.I):
        raise RuntimeError(f'Invalid trusted image path: {path}')
    alt = html.escape(photo['alt'], quote=True)
    img = f'<img src="{SITE}{html.escape(path, quote=True)}" alt="{alt}" class="wp-image-{id_}"/>'
    caption = photo.get('caption', '').strip()
    if caption:
        img += '<figcaption class="wp-element-caption">' + html.escape(caption) + '</figcaption>'
    return f'<!-- wp:image {{"id":{id_},"sizeSlug":"large","linkDestination":"none"}} -->\n<figure class="wp-block-image size-large">{img}</figure>\n<!-- /wp:image -->'

def build_updated(current, target):
    if MARKER in current:
        raise RuntimeError(f'Existing {MARKER} marker; not a fresh source')
    result = current
    for photo in target.get('photos', []):
        id_ = int(photo['id'])
        if f'wp-image-{id_}' in result:
            raise RuntimeError(f'Photo {id_} already in source')
        pos = photo['position']
        if pos not in ('after', 'before'):
            raise RuntimeError('Photo position must be before or after')
        match = heading_block(result, photo['heading'])
        loc = match.end() if pos == 'after' else match.start()
        tag = f'<!-- {MARKER}:photo:{id_} -->'
        block = f'\n\n{tag}\n{render_image(photo)}\n\n'
        result = result[:loc] + block + result[loc:]
    section = target.get('section')
    if section:
        match = heading_block(result, section['before_heading'])
        snippet = section['html'].strip()
        if 'https://www.discovercars.com/?a_aid=tsurikue' in current:
            raise RuntimeError('Refusing second rental CTA in target article')
        if snippet.count('https://www.discovercars.com/?a_aid=tsurikue') != 1:
            raise RuntimeError('Exactly one affiliate link required in new section')
        if 'rel="sponsored nofollow noopener"' not in snippet or 'This is an affiliate link.' not in snippet:
            raise RuntimeError('Affiliate terms and disclosure missing')
        result = result[:match.start()] + '\n\n<!-- '+MARKER+':section -->\n' + snippet + '\n\n' + result[match.start():]
    return result

def clean_base(path):
    base = unquote(urlparse(path).path).rsplit('/', 1)[-1].lower()
    return re.sub(r'-\d+x\d+(?=\.(?:jpg|jpeg|png|webp)$)', '', base)

def apply_refresh(config_path, cfg, auth, helpers):
    fetch_post, raw_field, public_counts, post_json, get_json = helpers
    if cfg.get('operation') != 'refresh_english_travel_20261113':
        raise RuntimeError('Wrong editorial operation')
    targets = cfg['targets']
    if len({int(x['id']) for x in targets}) != len(targets):
        raise RuntimeError('Duplicate target ID')
    published_before = public_counts(auth)
    planned = []
    # Preflight every article and every original WordPress media ID BEFORE writing any content.
    for target in targets:
        pid = int(target['id'])
        row = fetch_post(pid, auth)
        if (int(row.get('id') or 0),row.get('slug'),row.get('status')) != (pid,target['slug'],target['status']):
            raise RuntimeError(f'Post identity/status drift: {pid}')
        if 49 not in [int(x) for x in (row.get('categories') or [])]:
            raise RuntimeError(f'Not English Travel category: {pid}')
        if int(row.get('featured_media') or 0) != int(target['featured_media']):
            raise RuntimeError(f'Featured image drift: {pid}')
        if html.unescape(raw_field(row,'title')) != target['title']:
            raise RuntimeError(f'Title drift: {pid}')
        current = raw_field(row,'content')
        if MARKER in current:
            expected_photos = [f'{MARKER}:photo:{p["id"]}' for p in target.get('photos', [])]
            expected_sec = [MARKER+':section'] if target.get('section') else []
            if all(current.count(x)==1 for x in expected_photos+expected_sec):
                planned.append(dict(target=target,row=row,current=current,updated=current,action='ALREADY_PRESENT'))
                continue
            raise RuntimeError(f'Incomplete prior application marker: {pid}')
        if digest(current) != target['expected_sha256']:
            raise RuntimeError(f'Live content drift: {pid}; refuse overwrite')
        for photo in target.get('photos', []):
            mid = int(photo['id'])
            media,_ = get_json(f'{SITE}/wp-json/wp/v2/media/{mid}?context=edit&_fields=id,source_url',auth)
            if int(media.get('id') or 0)!=mid or clean_base(media.get('source_url',''))!=clean_base(photo['path']):
                raise RuntimeError(f'Media mismatch: target={pid}, photo={mid}')
        updated = build_updated(current,target)
        if updated==current:raise RuntimeError(f'No edits applied: {pid}')
        planned.append(dict(target=target,row=row,current=current,updated=updated,action='UPDATE'))
    written=[]
    try:
        for item in planned:
            target=item['target']; pid=int(target['id'])
            if item['action']=='UPDATE':
                fresh = fetch_post(pid,auth)
                if raw_field(fresh,'content')!=item['current'] or any(fresh.get(k)!=item['row'].get(k) for k in ('slug','status','title','categories','featured_media')):
                    raise RuntimeError(f'Concurrent WordPress change: {pid}')
                res=post_json(f'{SITE}/wp-json/wp/v2/posts/{pid}',auth,{'content':item['updated']})
                written.append(item)
                if (int(res.get('id') or 0),res.get('slug'),res.get('status'))!=(pid,target['slug'],target['status']):
                    raise RuntimeError(f'WP update response drift: {pid}')
            after=fetch_post(pid,auth)
            if raw_field(after,'content')!=item['updated'] or any(after.get(k)!=item['row'].get(k) for k in ('slug','status','title','categories','featured_media')):
                raise RuntimeError(f'WP readback differs: {pid}')
        if public_counts(auth)!=published_before:
            raise RuntimeError('Published post/page totals changed')
        report={'action':'ENGLISH_TRAVEL_REFRESH','posts':[{'id':int(x['target']['id']),'slug':x['target']['slug'],'status':x['target']['status'],'action':x['action'],'old_sha256':digest(x['current']),'new_sha256':digest(x['updated']),'photo_ids':[int(p['id']) for p in x['target'].get('photos',[])]} for x in planned], 'published_before':published_before,'published_after':public_counts(auth),'writes':len(written)}
        path=Path('reports/english-travel-refresh-20261113');path.mkdir(parents=True,exist_ok=True)
        (path/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        (path/'summary.md').write_text('# English travel refresh 2026-11-13\n\n'+'\n'.join(f'- {p["slug"]}: {p["action"]} / {len(p["photo_ids"])} photos / {p["status"]}' for p in report['posts'])+'\n')
        print('ENGLISH_TRAVEL_REFRESH_OK',json.dumps(report,ensure_ascii=False),flush=True)
        return report
    except Exception:
        for item in reversed(written):
            try:
                pid=int(item['target']['id']); live=fetch_post(pid,auth)
                if raw_field(live,'content')==item['updated'] and all(live.get(k)==item['row'].get(k) for k in ('slug','status','title','categories','featured_media')):
                    post_json(f'{SITE}/wp-json/wp/v2/posts/{pid}',auth,{'content':item['current']})
                    print('ENGLISH_TRAVEL_REFRESH_ROLLBACK',pid,flush=True)
                else:
                    print('ENGLISH_TRAVEL_REFRESH_ROLLBACK_SKIPPED_DRIFT',pid,flush=True)
            except Exception as error:
                print('ENGLISH_TRAVEL_REFRESH_ROLLBACK_FAILED',item['target']['id'],repr(error),flush=True)
        raise
