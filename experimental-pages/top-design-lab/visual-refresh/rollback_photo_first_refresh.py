import base64,json,os,pathlib,time,urllib.error,urllib.request
PAGE_ID=2983
HERE=pathlib.Path(__file__).resolve().parent
BACKUP=HERE/'.photo_first_backup.json'
user=os.environ['TSURIKUE_WP_USER']; pw=os.environ['TSURIKUE_WP_APP_PASSWORD']
token=base64.b64encode(f'{user}:{pw}'.encode()).decode()
H={'Authorization':'Basic '+token,'Accept':'application/json','Content-Type':'application/json; charset=utf-8','User-Agent':'tsurikue-top-photo-first-rollback/1.0'}
if not BACKUP.exists(): raise SystemExit('TOP_REFRESH_ROLLBACK_BACKUP_MISSING')
data=json.loads(BACKUP.read_text(encoding='utf-8'))
payload=json.dumps({'content':data['content'],'status':data['status']},ensure_ascii=False).encode()
last=None
for n in range(3):
    try:
        req=urllib.request.Request(f'https://tsurikue.com/wp-json/wp/v2/pages/{PAGE_ID}',data=payload,headers=H,method='POST')
        with urllib.request.urlopen(req,timeout=45) as r:
            out=json.loads(r.read().decode())
        if out.get('id')!=PAGE_ID or out.get('status')!=data['status']: raise RuntimeError('ROLLBACK_VERIFY_FAILED')
        print('TOP_PHOTO_FIRST_REFRESH_ROLLED_BACK')
        raise SystemExit(0)
    except SystemExit: raise
    except Exception as e:
        last=e
        if n<2: time.sleep(4*(n+1))
raise SystemExit('TOP_REFRESH_ROLLBACK_FAILED '+repr(last))
