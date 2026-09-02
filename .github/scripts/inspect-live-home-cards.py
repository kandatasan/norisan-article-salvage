#!/usr/bin/env python3
import base64, json, os, urllib.request, urllib.parse
BASE='https://tsurikue.com/wp-json/wp/v2'
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()
q=urllib.parse.urlencode({'context':'edit','_fields':'id,slug,status,content'})
req=urllib.request.Request(f'{BASE}/pages/2983?{q}',headers={'Authorization':AUTH,'Accept':'application/json'})
with urllib.request.urlopen(req,timeout=60) as r: row=json.loads(r.read().decode())
text=(row.get('content') or {}).get('raw') or ''
needle='tq4-cat--outing'
pos=text.find(needle)
if pos<0: raise SystemExit('CARD_NEEDLE_NOT_FOUND')
start=max(0,text.rfind('<!-- wp:',0,pos)-200)
end=text.find('<!-- /wp:group -->',pos)
if end<0: end=min(len(text),pos+9000)
else: end=min(len(text),end+2000)
print(text[start:end])
