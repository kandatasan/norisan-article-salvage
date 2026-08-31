import base64,json,os,re,pathlib,urllib.request,time
BASE='https://tsurikue.com/wp-json/wp/v2'
MEDIA_ID=3177
HERE=pathlib.Path(__file__).resolve().parents[2]
SOURCE=HERE/'category-hubs/outing/content.html'
user=os.environ['TSURIKUE_WP_USER']; pw=os.environ['TSURIKUE_WP_APP_PASSWORD']
token=base64.b64encode(f'{user}:{pw}'.encode()).decode()
H={'Authorization':'Basic '+token,'Accept':'application/json','Content-Type':'application/json; charset=utf-8','User-Agent':'tsurikue-dolphin-hero/1.2'}

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

# Replace only the Gutenberg Cover image. Hero text remains ordinary editable blocks.
pat=r'(<!-- wp:cover \{"url":")[^"]+("[^\n]*?"id":)\d+(,"dimRatio":0,"overlayColor":"black","minHeight":520,"minHeightUnit":"px","className":"tq-out-hero")'
if not re.search(pat,s): raise SystemExit('HERO_COVER_BLOCK_NOT_FOUND')
s=re.sub(pat,lambda m:m.group(1)+url+m.group(2)+str(mid)+m.group(3),s,count=1)
start=s.find('<!-- wp:cover '); end=s.find('<!-- /wp:cover -->',start)
if start<0 or end<0: raise SystemExit('HERO_COVER_RANGE_NOT_FOUND')
chunk=s[start:end]
imgpat=r'(<img class="wp-block-cover__image-background wp-image-)\d+(" alt="" src=")[^"]+(" data-object-fit="cover"/>)'
if not re.search(imgpat,chunk): raise SystemExit('HERO_IMG_NOT_FOUND')
chunk=re.sub(imgpat,lambda m:m.group(1)+str(mid)+m.group(2)+url+m.group(3),chunk,count=1)
s=s[:start]+chunk+s[end:]

# Make the photo brighter than the first dark-hero test while preserving white-copy contrast.
old='linear-gradient(90deg,rgba(8,22,28,.74) 0%,rgba(11,28,31,.60) 58%,rgba(14,29,31,.50) 100%)'
new='linear-gradient(90deg,rgba(6,18,24,.50) 0%,rgba(8,22,26,.38) 58%,rgba(9,23,27,.28) 100%)'
if old in s:
    s=s.replace(old,new,1)
elif 'linear-gradient(90deg,rgba(7,20,26,.56)' in s:
    s=re.sub(r'linear-gradient\(90deg,rgba\(7,20,26,\.56\) 0%,rgba\(9,24,28,\.43\) 58%,rgba\(10,25,29,\.34\) 100%\)',new,s,count=1)
else:
    raise SystemExit('DARK_HERO_GRADIENT_NOT_FOUND')

SOURCE.write_text(s,encoding='utf-8')
print(json.dumps({'media_id':mid,'source_url':url,'slug':media.get('slug'),'overlay':'bright-v2'},ensure_ascii=False))
