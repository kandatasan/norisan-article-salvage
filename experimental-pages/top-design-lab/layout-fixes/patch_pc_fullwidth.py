import base64, hashlib, json, os, pathlib, re, time, urllib.error, urllib.parse, urllib.request

PAGE_ID=2983
MARKER='<!-- tsurikue-experimental-page:v1:top-design-lab -->'
INSERT_BEFORE='/* TQ HEADER DRAWER PROTOTYPE v1 */'
PATCH_START='/* TQ TOP DESKTOP SECTION FULLWIDTH v1 */'
PATCH_END='/* END TQ TOP DESKTOP SECTION FULLWIDTH v1 */'
ROOT_MARKUP='class="wp-block-group alignfull tq4"'
HERE=pathlib.Path(__file__).resolve().parent
BACKUP=HERE/'.pc_fullwidth_backup.json'
CONTENT_PATH=pathlib.Path('experimental-pages/top-design-lab/content.html')
CONFIG_PATH=pathlib.Path('experimental-pages/top-design-lab/config.json')

user=os.environ['TSURIKUE_WP_USER']; pw=os.environ['TSURIKUE_WP_APP_PASSWORD']
token=base64.b64encode(f'{user}:{pw}'.encode()).decode()
HEADERS={'Authorization':'Basic '+token,'Accept':'application/json','Content-Type':'application/json; charset=utf-8','User-Agent':'tsurikue-top-pc-fullwidth/1.2'}

def request(path,method='GET',payload=None,attempts=3,timeout=45):
    data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode('utf-8')
    last=None
    for attempt in range(1,attempts+1):
        req=urllib.request.Request('https://tsurikue.com/wp-json/wp/v2'+path,data=data,headers=HEADERS,method=method)
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

page=get_page(); content=raw(page); status=page.get('status')
if page.get('id')!=PAGE_ID or status!='publish': raise SystemExit('PC_WIDTH_BLOCKED_TOP_NOT_PUBLISHED')
if MARKER not in content or INSERT_BEFORE not in content or ROOT_MARKUP not in content: raise SystemExit('PC_WIDTH_BLOCKED_EXPECTED_TOP_MARKERS_MISSING')
BACKUP.write_text(json.dumps({'status':status,'content':content},ensure_ascii=False),encoding='utf-8')

content=re.sub(r'\n?/\* TQ TOP DESKTOP SECTION FULLWIDTH v1 \*/.*?/\* END TQ TOP DESKTOP SECTION FULLWIDTH v1 \*/\n?','\n',content,flags=re.S)
css=r'''
/* TQ TOP DESKTOP SECTION FULLWIDTH v1 */
@media(min-width:960px){
  .tq4>.wp-block-group__inner-container{
    width:100%!important;
    max-width:none!important;
    margin-left:0!important;
    margin-right:0!important;
    padding-left:0!important;
    padding-right:0!important;
  }
  .tq4>.wp-block-group__inner-container>.tq4-party,
  .tq4>.wp-block-group__inner-container>.tq4-hero,
  .tq4>.wp-block-group__inner-container>.tq4-section,
  .tq4>.wp-block-group__inner-container>.tq4-final{
    width:100%!important;
    max-width:none!important;
    margin-left:0!important;
    margin-right:0!important;
    left:0!important;
    right:auto!important;
    transform:none!important;
  }
  .tq4 .tq4-section>.wp-block-group__inner-container,
  .tq4 .tq4-final>.wp-block-group__inner-container{
    width:min(1080px,91vw)!important;
    max-width:none!important;
    margin-left:auto!important;
    margin-right:auto!important;
  }
}
/* END TQ TOP DESKTOP SECTION FULLWIDTH v1 */
'''
content=content.replace(INSERT_BEFORE,css+'\n'+INSERT_BEFORE,1)
request(f'/pages/{PAGE_ID}',method='POST',payload={'content':content})
after=get_page(); after_content=raw(after)
if after.get('status')!=status: raise SystemExit('PC_WIDTH_VERIFY_STATUS_CHANGED')
if PATCH_START not in after_content or PATCH_END not in after_content: raise SystemExit('PC_WIDTH_VERIFY_PATCH_MISSING')
if after_content.count(PATCH_START)!=1: raise SystemExit('PC_WIDTH_VERIFY_PATCH_DUPLICATED')
sync_source(after_content)
print('SUCCESS_TOP_PC_FULLWIDTH_PATCH')
