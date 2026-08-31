import base64,json,os,re,pathlib,urllib.request,time
BASE='https://tsurikue.com/wp-json/wp/v2'
MEDIA_ID=3177
HERE=pathlib.Path(__file__).resolve().parents[2]
SOURCE=HERE/'category-hubs/outing/content.html'
user=os.environ['TSURIKUE_WP_USER']; pw=os.environ['TSURIKUE_WP_APP_PASSWORD']
token=base64.b64encode(f'{user}:{pw}'.encode()).decode()
H={'Authorization':'Basic '+token,'Accept':'application/json','Content-Type':'application/json; charset=utf-8','User-Agent':'tsurikue-dolphin-hero/1.3'}

def req(path):
    last=None
    for n in range(3):
        try:
            r=urllib.request.Request(BASE+path,headers=H)
            with urllib.request.urlopen(r,timeout=35) as x:
                return json.loads(x.read().decode())
        except Exception as e:
            last=e
            if n<2: time.sleep(4*(n+1))
    raise last

media=req(f'/media/{MEDIA_ID}?context=edit&_fields=id,slug,source_url,media_details,title')
if media.get('id')!=MEDIA_ID: raise SystemExit('DOLPHIN_MEDIA_ID_MISMATCH')
url=media.get('source_url') or ''
if not url: raise SystemExit('DOLPHIN_MEDIA_URL_MISSING')
mid=MEDIA_ID
s=SOURCE.read_text(encoding='utf-8')

# Find the first Gutenberg Cover block and require it to be the outing hero.
start=s.find('<!-- wp:cover')
if start<0: raise SystemExit('HERO_COVER_START_NOT_FOUND')
open_end=s.find('-->',start)
end=s.find('<!-- /wp:cover -->',open_end)
if open_end<0 or end<0: raise SystemExit('HERO_COVER_RANGE_NOT_FOUND')
opening=s[start:open_end+3]
if 'tq-out-hero' not in opening: raise SystemExit('FIRST_COVER_IS_NOT_OUTING_HERO')

# Update Cover block attributes without depending on their order.
new_opening,n_url=re.subn(r'"url":"[^"]+"',f'"url":"{url}"',opening,count=1)
new_opening,n_id=re.subn(r'"id":\d+',f'"id":{mid}',new_opening,count=1)
if n_url!=1 or n_id!=1: raise SystemExit(f'HERO_COVER_ATTR_PATCH_FAILED url={n_url} id={n_id}')
s=s[:start]+new_opening+s[open_end+3:]
# Recalculate range after opening-comment replacement.
open_end=s.find('-->',start); end=s.find('<!-- /wp:cover -->',open_end)
chunk=s[start:end]

# Update the actual cover image tag.
img_match=re.search(r'<img[^>]*class="[^"]*wp-block-cover__image-background[^"]*"[^>]*>',chunk)
if not img_match: raise SystemExit('HERO_IMG_TAG_NOT_FOUND')
tag=img_match.group(0)
tag,n_class=re.subn(r'wp-image-\d+',f'wp-image-{mid}',tag,count=1)
tag,n_src=re.subn(r'src="[^"]+"',f'src="{url}"',tag,count=1)
if n_src!=1: raise SystemExit('HERO_IMG_SRC_PATCH_FAILED')
if n_class==0:
    tag=tag.replace('wp-block-cover__image-background',f'wp-block-cover__image-background wp-image-{mid}',1)
chunk=chunk[:img_match.start()]+tag+chunk[img_match.end():]
s=s[:start]+chunk+s[end:]

# Keep the CSS fallback background in sync with the Cover image.
s,n_css_url=re.subn(r"(\.tq-out-hero\{[^\n]*?url\(')[^']+('\)[^\n]*?\})",lambda m:m.group(1)+url+m.group(2),s,count=1)
if n_css_url!=1: raise SystemExit('HERO_CSS_FALLBACK_PATCH_FAILED')

# Make the image brighter than the first dark-hero test while preserving white text contrast.
new='linear-gradient(90deg,rgba(6,18,24,.50) 0%,rgba(8,22,26,.38) 58%,rgba(9,23,27,.28) 100%)'
gradients=[
 'linear-gradient(90deg,rgba(8,22,28,.74) 0%,rgba(11,28,31,.60) 58%,rgba(14,29,31,.50) 100%)',
 'linear-gradient(90deg,rgba(7,20,26,.56) 0%,rgba(9,24,28,.43) 58%,rgba(10,25,29,.34) 100%)'
]
changed=False
for old in gradients:
    if old in s:
        s=s.replace(old,new,1); changed=True; break
if not changed and new not in s: raise SystemExit('DARK_HERO_GRADIENT_NOT_FOUND')

SOURCE.write_text(s,encoding='utf-8')
print(json.dumps({'media_id':mid,'source_url':url,'slug':media.get('slug'),'overlay':'bright-v2','cover_attr':True,'img_tag':True,'css_fallback':True},ensure_ascii=False))
