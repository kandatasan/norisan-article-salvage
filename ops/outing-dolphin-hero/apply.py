import base64,json,os,re,pathlib,urllib.parse,urllib.request,time
BASE='https://tsurikue.com/wp-json/wp/v2'
HERE=pathlib.Path(__file__).resolve().parents[2]
SOURCE=HERE/'category-hubs/outing/content.html'
user=os.environ['TSURIKUE_WP_USER']; pw=os.environ['TSURIKUE_WP_APP_PASSWORD']
token=base64.b64encode(f'{user}:{pw}'.encode()).decode()
H={'Authorization':'Basic '+token,'Accept':'application/json','Content-Type':'application/json; charset=utf-8','User-Agent':'tsurikue-dolphin-hero/1.0'}
def req(path,method='GET',payload=None):
 data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode()
 last=None
 for n in range(3):
  try:
   r=urllib.request.Request(BASE+path,data=data,headers=H,method=method)
   with urllib.request.urlopen(r,timeout=35) as x:return json.loads(x.read().decode())
  except Exception as e:
   last=e; time.sleep(4*(n+1))
 raise last
q=urllib.parse.urlencode({'search':'IMG_2419','context':'edit','per_page':100,'orderby':'date','order':'desc','_fields':'id,date,slug,source_url,media_details'})
items=req('/media?'+q)
# Prefer the user's latest cropped upload: IMG_2419(4), normally the newest matching media item.
candidates=[x for x in items if '2419' in (x.get('source_url') or '')]
if not candidates: raise SystemExit('DOLPHIN_MEDIA_NOT_FOUND')
media=candidates[0]
url=media['source_url']; mid=media['id']
s=SOURCE.read_text(encoding='utf-8')
# Replace only the Cover block image URL/id; CSS/text remain editable Gutenberg blocks.
pat=r'(<!-- wp:cover \{"url":")[^"]+("[^\n]*?"id":)\d+(,"dimRatio":0,"overlayColor":"black","minHeight":520,"minHeightUnit":"px","className":"tq-out-hero")'
m=re.search(pat,s)
if not m: raise SystemExit('HERO_COVER_BLOCK_NOT_FOUND')
s=re.sub(pat,lambda m:m.group(1)+url+m.group(2)+str(mid)+m.group(3),s,count=1)
# Also replace the img element inside this cover only.
start=s.find('<!-- wp:cover '); end=s.find('<!-- /wp:cover -->',start)
chunk=s[start:end]
chunk=re.sub(r'(<img class="wp-block-cover__image-background wp-image-)\d+(" alt="" src=")[^"]+(" data-object-fit="cover"/>)',lambda m:m.group(1)+str(mid)+m.group(2)+url+m.group(3),chunk,count=1)
s=s[:start]+chunk+s[end:]
# Lighten the existing overlay while retaining strong white-copy contrast.
s=s.replace('linear-gradient(90deg,rgba(8,22,28,.74) 0%,rgba(11,28,31,.60) 58%,rgba(14,29,31,.50) 100%)','linear-gradient(90deg,rgba(7,20,26,.56) 0%,rgba(9,24,28,.43) 58%,rgba(10,25,29,.34) 100%)')
SOURCE.write_text(s,encoding='utf-8')
print(json.dumps({'media_id':mid,'source_url':url,'matched':len(candidates)},ensure_ascii=False))