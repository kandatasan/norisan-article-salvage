import base64, json, os, urllib.request

BASE='https://tsurikue.com/wp-json/wp/v2'
PAGE_ID=3154
user=os.environ['TSURIKUE_WP_USER']
pw=os.environ['TSURIKUE_WP_APP_PASSWORD']
token=base64.b64encode(f'{user}:{pw}'.encode()).decode()
req=urllib.request.Request(
    f'{BASE}/pages/{PAGE_ID}?context=edit&_fields=id,slug,status,content',
    headers={'Authorization':'Basic '+token,'Accept':'application/json','User-Agent':'tsurikue-outing-wording-verify/1.0'}
)
with urllib.request.urlopen(req,timeout=35) as r:
    page=json.loads(r.read().decode('utf-8'))
content=(page.get('content') or {}).get('raw') or (page.get('content') or {}).get('rendered') or ''
checks={
    'id':page.get('id')==PAGE_ID,
    'slug':page.get('slug')=='odekake',
    'draft':page.get('status')=='draft',
    'travel_label':content.count('旅に出る')>=2,
    'old_label_absent':'ちょっと遠くへ' not in content,
    'hiroshima_departure_phrase_absent':'広島を飛び出して遊んだ旅' not in content,
    'final_polish':'/* TQ OUTING FINAL POLISH v1 */' in content,
    'latest':'wp:latest-posts' in content,
}
print('OUTING_TRAVEL_WORDING_VERIFY='+json.dumps(checks,ensure_ascii=False))
if not all(checks.values()):
    raise SystemExit('VERIFY_FAILED')
print('OUTING_TRAVEL_WORDING_VERIFIED')
