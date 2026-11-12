"""Insert two verified owner photos into published UX used-buying advice (one post only)."""
from __future__ import annotations
import hashlib
import html
import json
import re
from pathlib import Path

POST_ID = 2948
SLUG = "lexus-ux-used"
EXPECTED_TITLE = "レクサスUXの中古は狙い目？新車と比べて中古をおすすめしたい理由"
EXPECTED_CONTENT_SHA256 = "78c7e3defc4baa44034693511d35e303fbd4bf9659d2c5886709fb40767d0796"
MARKER = "<!-- tsurikue-ux-used-two-owner-photos:20261113 -->"
TARGET_SENTENCE = "また、UXは後席と荷室に余裕がある車ではありません。"
NEXT_HEADING = "中古で狙いたいグレードは？"

# These blocks are from existing WordPress article /ux-koukai/ (post 2517).
# The photo IDs, file URLs and alt text were confirmed again through authenticated
# read-only media API /media/2201, /media/2207 on 2026-11-13.
REAR_PHOTO = '''<!-- wp:image {"id":2201,"sizeSlug":"large","linkDestination":"none"} -->
<figure class="wp-block-image size-large"><img src="https://tsurikue.com/wp-content/uploads/2026/06/IMG_3504-1024x367.jpeg" alt="レクサスUXの後部座席の足元" class="wp-image-2201"/><figcaption class="wp-element-caption">UXの後席。前席との距離感はこんな感じ。</figcaption></figure>
<!-- /wp:image -->'''

LUGGAGE_PHOTO = '''<!-- wp:image {"id":2207,"sizeSlug":"large","linkDestination":"none"} -->
<figure class="wp-block-image size-large"><img src="https://tsurikue.com/wp-content/uploads/2026/06/IMG_2661-1-1024x769.jpeg" alt="レクサスUXの荷室に大きな段ボールを積んだ写真" class="wp-image-2207"/><figcaption class="wp-element-caption">大きな段ボールを載せた状態。荷室は高さにも注目。</figcaption></figure>
<!-- /wp:image -->'''

PARAGRAPH = re.compile(r'<!-- wp:paragraph(?: [^\n]*?)? -->\s*<p[^>]*>.*?</p>\s*<!-- /wp:paragraph -->',re.S)

def sha(text:str)->str: return hashlib.sha256(text.encode('utf-8')).hexdigest()

def linked_urls(text:str)->list[str]:
    return sorted(re.findall(r'<a\b[^>]*\bhref="([^"]+)"',text))

def photo_locations(body:str)->list[int]:
    return [body.find('wp-image-2201'),body.find('wp-image-2207')]

def transform(source:str)->str:
    if MARKER in source:
        if (source.count(MARKER)==1 and source.count('wp-image-2201')==1
            and source.count('wp-image-2207')==1 and source.count(TARGET_SENTENCE)==1):
            return source
        raise RuntimeError('Existing image marker or photos are damaged')
    if sha(source)!=EXPECTED_CONTENT_SHA256:
        raise RuntimeError("Source content changed; cannot safely insert owner photos")
    if source.count('wp-image-2201') or source.count('wp-image-2207'):
        raise RuntimeError("Target photos are already present without marker")
    if source.count(TARGET_SENTENCE)!=1:
        raise RuntimeError("Rear-seat and luggage paragraph moved")
    matches=[m for m in PARAGRAPH.finditer(source) if TARGET_SENTENCE in html.unescape(re.sub(r'<[^>]*>','',m.group(0)))]
    if len(matches)!=1:
        raise RuntimeError(f"Expected 1 UX drawback paragraph, found {len(matches)}")
    target=matches[0]
    suffix=source[target.end():]
    if not re.match(r'\s*<!-- wp:heading\b',suffix):
        raise RuntimeError("Paragraph no longer borders next heading; human review needed")
    if NEXT_HEADING not in suffix[:600]:
        raise RuntimeError("Expected next section heading moved")
    insert='\n\n'+MARKER+'\n'+REAR_PHOTO+'\n\n'+LUGGAGE_PHOTO
    changed=source[:target.end()]+insert+source[target.end():]
    if (source.count('<!-- wp:image')+2!=changed.count('<!-- wp:image')
        or source.count('<figure')+2!=changed.count('<figure')
        or source.count('<!-- wp:heading')!=changed.count('<!-- wp:heading')
        or source.count('<!-- wp:paragraph')!=changed.count('<!-- wp:paragraph')
        or linked_urls(source)!=linked_urls(changed)):
        raise RuntimeError("Non-image block or hyperlink unexpectedly changed")
    existing_ids=re.findall(r'wp-image-(\d+)',source)
    after_ids=re.findall(r'wp-image-(\d+)',changed)
    if sorted(after_ids)!=sorted(existing_ids+['2201','2207']):
        raise RuntimeError("Original images changed unexpectedly")
    if source.count('[blog_parts id="4521"]')!=changed.count('[blog_parts id="4521"]') or source.count('[blog_parts id="4505"]')!=changed.count('[blog_parts id="4505"]'):
        raise RuntimeError("CTN or Gulliver shortcode drift")
    locs=photo_locations(changed)
    if not (target.end()<locs[0]<locs[1]<changed.find(NEXT_HEADING)):
        raise RuntimeError("Photo positions are not in UX drawback section")
    return changed


def apply_photos(config_path:Path,cfg:dict,auth:str,api):
    if (cfg.get('post_id'),cfg.get('slug'),cfg.get('expected_content_sha256')) != (POST_ID,SLUG,EXPECTED_CONTENT_SHA256):
        raise RuntimeError('Editorial config guard mismatch')
    fetch_post,raw_field,public_counts,post_json,site_url=api
    before=fetch_post(POST_ID,auth)
    for key,value in [('id',POST_ID),('slug',SLUG),('status','publish'),('featured_media',1001),('author',1)]:
        if before.get(key)!=value: raise RuntimeError(f'WordPress post metadata changed: {key}')
    if html.unescape(raw_field(before,'title'))!=EXPECTED_TITLE: raise RuntimeError('Post title changed')
    original=raw_field(before,'content')
    updated=transform(original)
    counts_before=public_counts(auth)
    # Re-fetch immediately before write to protect concurrent edits.
    fresh=fetch_post(POST_ID,auth)
    for key in ['id','slug','status','featured_media','title','categories','author']:
        if fresh.get(key)!=before.get(key): raise RuntimeError(f'Concurrent metadata change: {key}')
    if raw_field(fresh,'content')!=original:
        raise RuntimeError('Concurrent WordPress edit: update aborted')
    action='ALREADY_PRESENT' if updated==original else 'UPDATE'
    if action=='UPDATE':
        response=post_json(site_url+'/wp-json/wp/v2/posts/'+str(POST_ID),auth,{'content':updated})
        if (response.get('id'),response.get('status'),response.get('featured_media'))!=(POST_ID,'publish',1001):
            raise RuntimeError('Saved WordPress status or image ID unexpected')
    after=fetch_post(POST_ID,auth)
    for key in ['id','slug','status','featured_media','title','categories','author']:
        if after.get(key)!=before.get(key): raise RuntimeError(f'Protected metadata changed after save: {key}')
    if raw_field(after,'content')!=updated:
        raise RuntimeError('WordPress did not persist expected two image blocks')
    totals_after=public_counts(auth)
    if totals_after!=counts_before:
        raise RuntimeError('Unexpected published post count change')
    data={'post_id':POST_ID,'slug':SLUG,'status':'publish','action':action,'writes':1 if action=='UPDATE' else 0,
          'content_sha256_before':sha(original),'content_sha256_after':sha(updated),
          'photo_ids':[2201,2207],'images_before':original.count('<!-- wp:image'),'images_after':updated.count('<!-- wp:image'),
          'anchor':TARGET_SENTENCE,'featured_media':1001,'published_count_before':counts_before,'published_count_after':totals_after}
    directory=Path('reports/ux-used-owner-photos-20261113');directory.mkdir(parents=True,exist_ok=True)
    (directory/'result.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (directory/'summary.md').write_text('## UX used: two verified owner photos\n\n'+json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('UX_USED_PHOTOS_RESULT',json.dumps(data,ensure_ascii=False),flush=True)
    return data
