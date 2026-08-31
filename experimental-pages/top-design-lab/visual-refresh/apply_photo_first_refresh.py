import base64, hashlib, json, os, pathlib, re, time, urllib.error, urllib.parse, urllib.request

PAGE_ID=2983
MEDIA_ID=3177
MARKER='<!-- tsurikue-experimental-page:v1:top-design-lab -->'
INSERT_BEFORE='/* TQ HEADER DRAWER PROTOTYPE v1 */'
PATCH_START='/* TQ TOP PHOTO-FIRST REFRESH v1 */'
PATCH_END='/* END TQ TOP PHOTO-FIRST REFRESH v1 */'
HERE=pathlib.Path(__file__).resolve().parent
BACKUP=HERE/'.photo_first_backup.json'
CONTENT_PATH=pathlib.Path('experimental-pages/top-design-lab/content.html')
CONFIG_PATH=pathlib.Path('experimental-pages/top-design-lab/config.json')

user=os.environ['TSURIKUE_WP_USER']; pw=os.environ['TSURIKUE_WP_APP_PASSWORD']
token=base64.b64encode(f'{user}:{pw}'.encode()).decode()
HEADERS={'Authorization':'Basic '+token,'Accept':'application/json','Content-Type':'application/json; charset=utf-8','User-Agent':'tsurikue-top-photo-first/1.0'}
BASE='https://tsurikue.com/wp-json/wp/v2'

def request(path,method='GET',payload=None,attempts=3,timeout=45):
    data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode('utf-8')
    last=None
    for attempt in range(1,attempts+1):
        req=urllib.request.Request(BASE+path,data=data,headers=HEADERS,method=method)
        try:
            with urllib.request.urlopen(req,timeout=timeout) as r:
                return json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            body=e.read().decode('utf-8','replace')
            raise RuntimeError(f'HTTP {e.code} {method} {path}: {body[:600]}') from e
        except Exception as e:
            last=e
            if attempt<attempts: time.sleep(4*attempt)
    raise RuntimeError(f'REQUEST_FAILED {method} {path}: {type(last).__name__}: {last}')

def get_page():
    q=urllib.parse.urlencode({'context':'edit','_fields':'id,status,content'})
    return request(f'/pages/{PAGE_ID}?{q}')

def raw(page): return (page.get('content') or {}).get('raw') or ''

def sync_source(content):
    CONTENT_PATH.write_text(content,encoding='utf-8')
    cfg=json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
    cfg['expected_current_content_sha256']=hashlib.sha256(content.encode()).hexdigest()
    CONFIG_PATH.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def patch_outing_card(content,url):
    needle='tq4-cat--outing'
    pos=content.find(needle)
    if pos<0: raise SystemExit('TOP_REFRESH_OUTING_CARD_NOT_FOUND')
    start=content.rfind('<!-- wp:cover',0,pos)
    open_end=content.find('-->',start)
    end=content.find('<!-- /wp:cover -->',open_end)
    if start<0 or open_end<0 or end<0: raise SystemExit('TOP_REFRESH_OUTING_CARD_RANGE_BAD')
    opening=content[start:open_end+3]
    if 'tq4-cat' not in opening: raise SystemExit('TOP_REFRESH_OUTING_OPENING_BAD')
    opening,n_url=re.subn(r'"url":"[^"]+"',f'"url":"{url}"',opening,count=1)
    if n_url!=1: raise SystemExit('TOP_REFRESH_OUTING_URL_ATTR_BAD')
    if re.search(r'"id":\d+',opening):
        opening=re.sub(r'"id":\d+',f'"id":{MEDIA_ID}',opening,count=1)
    else:
        opening=opening.replace(',"dimRatio"',f',"id":{MEDIA_ID},"dimRatio"',1)
    content=content[:start]+opening+content[open_end+3:]
    open_end=content.find('-->',start); end=content.find('<!-- /wp:cover -->',open_end)
    chunk=content[start:end]
    m=re.search(r'<img[^>]*class="[^"]*wp-block-cover__image-background[^"]*"[^>]*>',chunk)
    if not m: raise SystemExit('TOP_REFRESH_OUTING_IMG_NOT_FOUND')
    tag=m.group(0)
    tag,n_src=re.subn(r'src="[^"]+"',f'src="{url}"',tag,count=1)
    if n_src!=1: raise SystemExit('TOP_REFRESH_OUTING_IMG_SRC_BAD')
    if re.search(r'wp-image-\d+',tag): tag=re.sub(r'wp-image-\d+',f'wp-image-{MEDIA_ID}',tag,count=1)
    else: tag=tag.replace('wp-block-cover__image-background',f'wp-block-cover__image-background wp-image-{MEDIA_ID}',1)
    chunk=chunk[:m.start()]+tag+chunk[m.end():]
    return content[:start]+chunk+content[end:]

page=get_page(); content=raw(page); status=page.get('status')
if page.get('id')!=PAGE_ID or status!='publish': raise SystemExit('TOP_REFRESH_BLOCKED_NOT_PUBLISHED')
for x in [MARKER,INSERT_BEFORE,'tq4-hero','tq4-cat--outing','tq4-cat--gourmet','tq4-cat--fishing','tq4-cat--car']:
    if x not in content: raise SystemExit('TOP_REFRESH_REQUIRED_MARKER_MISSING='+x)
media=request(f'/media/{MEDIA_ID}?context=edit&_fields=id,source_url,slug')
if media.get('id')!=MEDIA_ID or not media.get('source_url'): raise SystemExit('TOP_REFRESH_DOLPHIN_MEDIA_BAD')
BACKUP.write_text(json.dumps({'status':status,'content':content},ensure_ascii=False),encoding='utf-8')

# Idempotently remove a previous refresh block, then refresh the outing card image.
content=re.sub(r'\n?/\* TQ TOP PHOTO-FIRST REFRESH v1 \*/.*?/\* END TQ TOP PHOTO-FIRST REFRESH v1 \*/\n?','\n',content,flags=re.S)
content=patch_outing_card(content,media['source_url'])

css=r'''
/* TQ TOP PHOTO-FIRST REFRESH v1 */
/* Keep the existing homepage structure; let the real photos carry the visual identity. */
.tq4 .tq4-hero .wp-block-cover__background{
  background:linear-gradient(90deg,rgba(7,20,26,.58) 0%,rgba(8,22,27,.44) 58%,rgba(9,24,28,.30) 100%)!important;
  background-color:transparent!important;
  opacity:1!important;
}
.tq4 .tq4-hero,
.tq4 .tq4-hero .wp-block-cover__inner-container,
.tq4 .tq4-hero .tq4-brand,
.tq4 .tq4-hero .tq4-label,
.tq4 .tq4-hero h1,
.tq4 .tq4-hero .tq4-hero-lead{color:#fff!important}
.tq4 .tq4-hero .tq4-hero-text{color:rgba(255,255,255,.90)!important}
.tq4 .tq4-hero h1{ text-shadow:0 3px 18px rgba(0,0,0,.42),0 1px 2px rgba(0,0,0,.66)!important }
.tq4 .tq4-hero .tq4-brand,
.tq4 .tq4-hero .tq4-label,
.tq4 .tq4-hero .tq4-hero-lead,
.tq4 .tq4-hero .tq4-hero-text{ text-shadow:0 2px 10px rgba(0,0,0,.42),0 1px 1px rgba(0,0,0,.52)!important }

.tq4 .tq4-cat .wp-block-cover__background,
.tq4 .tq4-cat--gourmet .wp-block-cover__background,
.tq4 .tq4-cat--fishing .wp-block-cover__background{
  background:linear-gradient(180deg,rgba(5,16,20,.16) 0%,rgba(5,17,21,.36) 48%,rgba(5,17,21,.76) 100%)!important;
  background-color:transparent!important;
  opacity:1!important;
}
.tq4 .tq4-cat-body{background:transparent!important}
.tq4 .tq4-cat,
.tq4 .tq4-cat .wp-block-cover__inner-container,
.tq4 .tq4-cat .tq4-card-label,
.tq4 .tq4-cat h3,
.tq4 .tq4-cat h3 a,
.tq4 .tq4-cat .tq4-card-desc{color:#fff!important}
.tq4 .tq4-card-label{color:rgba(255,255,255,.80)!important}
.tq4 .tq4-card-desc{color:rgba(255,255,255,.91)!important}
.tq4 .tq4-cat h3,
.tq4 .tq4-cat h3 a{ text-shadow:0 2px 10px rgba(0,0,0,.50),0 1px 1px rgba(0,0,0,.58)!important }
.tq4 .tq4-card-label,
.tq4 .tq4-card-desc{ text-shadow:0 1px 6px rgba(0,0,0,.52)!important }
.tq4 .tq4-pill-text{
  background:rgba(255,255,255,.90)!important;
  color:#242826!important;
  border-color:rgba(255,255,255,.48)!important;
  text-shadow:none!important;
  backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px)
}
.tq4 .tq4-cat img{transition:transform .45s ease!important}
.tq4 .tq4-cat:hover img{transform:scale(1.025)!important}
@media(max-width:560px){
  .tq4 .tq4-hero .wp-block-cover__background{
    background:linear-gradient(90deg,rgba(7,20,26,.60) 0%,rgba(8,22,27,.46) 62%,rgba(9,24,28,.34) 100%)!important;
    opacity:1!important;
  }
  .tq4 .tq4-cat .wp-block-cover__background,
  .tq4 .tq4-cat--gourmet .wp-block-cover__background,
  .tq4 .tq4-cat--fishing .wp-block-cover__background{
    background:linear-gradient(180deg,rgba(5,16,20,.12) 0%,rgba(5,17,21,.32) 42%,rgba(5,17,21,.78) 100%)!important;
    opacity:1!important;
  }
}
/* END TQ TOP PHOTO-FIRST REFRESH v1 */
'''
content=content.replace(INSERT_BEFORE,css+'\n'+INSERT_BEFORE,1)
request(f'/pages/{PAGE_ID}',method='POST',payload={'content':content})
after=get_page(); after_content=raw(after)
if after.get('status')!=status: raise SystemExit('TOP_REFRESH_VERIFY_STATUS_CHANGED')
checks=[PATCH_START,PATCH_END,media['source_url'],'tq4-cat--gourmet','tq4-cat--fishing','tq4-cat--car']
for x in checks:
    if x not in after_content: raise SystemExit('TOP_REFRESH_VERIFY_MISSING='+x)
if after_content.count(PATCH_START)!=1: raise SystemExit('TOP_REFRESH_VERIFY_DUPLICATE_PATCH')
sync_source(after_content)
print(json.dumps({'result':'TOP_PHOTO_FIRST_REFRESH_APPLIED','page':PAGE_ID,'status':status,'outing_media_id':MEDIA_ID,'outing_url':media['source_url']},ensure_ascii=False))
