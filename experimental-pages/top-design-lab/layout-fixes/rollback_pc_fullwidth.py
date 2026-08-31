import base64, hashlib, json, os, pathlib, time, urllib.error, urllib.parse, urllib.request

PAGE_ID=2983
HERE=pathlib.Path(__file__).resolve().parent
BACKUP=HERE/'.pc_fullwidth_backup.json'
CONTENT_PATH=pathlib.Path('experimental-pages/top-design-lab/content.html')
CONFIG_PATH=pathlib.Path('experimental-pages/top-design-lab/config.json')
user=os.environ['TSURIKUE_WP_USER']; pw=os.environ['TSURIKUE_WP_APP_PASSWORD']
token=base64.b64encode(f'{user}:{pw}'.encode()).decode()
HEADERS={'Authorization':'Basic '+token,'Accept':'application/json','Content-Type':'application/json; charset=utf-8','User-Agent':'tsurikue-top-pc-fullwidth-rollback/1.0'}

def request(path,method='GET',payload=None,attempts=3,timeout=45):
    data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode('utf-8')
    last=None
    for attempt in range(1,attempts+1):
        req=urllib.request.Request('https://tsurikue.com/wp-json/wp/v2'+path,data=data,headers=HEADERS,method=method)
        try:
            with urllib.request.urlopen(req,timeout=timeout) as r: return json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            body=e.read().decode('utf-8','replace'); raise RuntimeError(f'HTTP {e.code} {method} {path}: {body[:600]}') from e
        except Exception as e:
            last=e
            if attempt<attempts: time.sleep(4*attempt)
    raise RuntimeError(f'REQUEST_FAILED {method} {path}: {type(last).__name__}: {last}')

if not BACKUP.exists(): raise SystemExit('ROLLBACK_BACKUP_MISSING')
backup=json.loads(BACKUP.read_text(encoding='utf-8')); content=backup['content']; status=backup['status']
request(f'/pages/{PAGE_ID}',method='POST',payload={'content':content})
q=urllib.parse.urlencode({'context':'edit','_fields':'id,status,content'})
after=request(f'/pages/{PAGE_ID}?{q}'); after_content=(after.get('content') or {}).get('raw') or ''
if after.get('status')!=status or after_content!=content: raise SystemExit('ROLLBACK_VERIFY_FAILED')
CONTENT_PATH.write_text(after_content,encoding='utf-8')
cfg=json.loads(CONFIG_PATH.read_text(encoding='utf-8')); cfg['expected_current_content_sha256']=hashlib.sha256(after_content.encode()).hexdigest(); CONFIG_PATH.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('SUCCESS_TOP_PC_FULLWIDTH_ROLLBACK')
