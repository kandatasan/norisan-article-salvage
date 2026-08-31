import base64,json,os,re,pathlib,urllib.parse,urllib.request,time
BASE='https://tsurikue.com/wp-json/wp/v2'
HERE=pathlib.Path(__file__).resolve().parents[2]
SOURCE=HERE/'category-hubs/outing/content.html'
user=os.environ['TSURIKUE_WP_USER']; pw=os.environ['TSURIKUE_WP_APP_PASSWORD']
token=base64.b64encode(f'{user}:{pw}'.encode()).decode()
H={'Authorization':'Basic '+token,'Accept':'application/json','Content-Type':'application/json; charset=utf-8','User-Agent':'tsurikue-dolphin-hero/1.1'}
def req(path):
 last=None
 for n in range(3):
  try:
   r=urllib.request.Request(BASE+path,headers=H)
   with urllib.request.urlopen(r,timeout=35) as x:return json.loads(x.read().decode())
  except Exception as e:
   last=e; time.sleep(4*(n+1))
 raise last
# WordPress media search does not reliably index original filenames. Inspect the newest uploads directly.
q=urllib.parse.urlencode({'context':'edit','per_page':100,'orderby':'date','order':'desc','_fields':'id,date,slug,source_url,media_details,title,caption'})
items=req('/media?'+q)
def hay(x):
 md=x.get('media_details') or {}
 f=md.get('file') or ''
 return ' '.join([x.get('slug') or '',x.get('source_url') or '',f,json.dumps(x.get('title') or {},ensure_ascii=False),json.dumps(x.get('caption') or {},ensure_ascii=False)]).lower()
candidates=[x for x in items if '2419' in hay(x)]
if not candidates:
 # User uploaded immediately before this run; if WordPress renamed the file beyond recognition, report recent image names safely.
 recent=[{'id':x.get('id'),'url':x.get('source_url'),'file':(x.get('media_details') or {}).get('file')} for x in items[:12]]
 raise SystemExit('DOLPHIN_MEDIA_NOT_FOUND recent='+json.dumps(recent,ensure_ascii=False))
media=candidates[0]; url=media['source_url']; mid=media['id']
s=SOURCE.read_text(encoding='utf-8')
pat=r'(<!-- wp:cover \{"url":")[^"]+("[^\n]*?"id":)\d+(,"dimRatio":0,"overlayColor":"black","minHeight":520,"minHeightUnit":"px","className":"tq-out-hero")'
if not re.search(pat,s): raise SystemExit('HERO_COVER_BLOCK_NOT_FOUND')
s=re.sub(pat,lambda m:m.group(1)+url+m.group(2)+str(mid)+m.group(3),s,count=1)
start=s.find('<!-- wp:cover '); end=s.find('<!-- /wp:cover -->',start)
chunk=s[start:end]
chunk=re.sub(r'(<img class="wp-block-cover__image-background wp-image-)\d+(" alt="" src=")[^"]+(" data-object-fit="cover"/>)',lambda m:m.group(1)+str(mid)+m.group(2)+url+m.group(3),chunk,count=1)
s=s[:start]+chunk+s[end:]
s=s.replace('linear-gradient(90deg,rgba(8,22,28,.74) 0%,rgba(11,28,31,.60) 58%,rgba(14,29,31,.50) 100%)','linear-gradient(90deg,rgba(7,20,26,.56) 0%,rgba(9,24,28,.43) 58%,rgba(10,25,29,.34) 100%)')
SOURCE.write_text(s,encoding='utf-8')
print(json.dumps({'media_id':mid,'source_url':url,'matched':len(candidates)},ensure_ascii=False))