#!/usr/bin/env python3
import base64, json, os, urllib.request, urllib.parse
BASE='https://tsurikue.com/wp-json/wp/v2'
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()
q=urllib.parse.urlencode({'context':'edit','_fields':'id,slug,status,content'})
req=urllib.request.Request(f'{BASE}/pages/2983?{q}',headers={'Authorization':AUTH,'Accept':'application/json'})
with urllib.request.urlopen(req,timeout=60) as r: row=json.loads(r.read().decode())
text=(row.get('content') or {}).get('raw') or ''
needle='<!-- wp:group {"className":"tq4-cat-grid"'
pos=text.find(needle)
if pos<0: raise SystemExit('CARD_GRID_NEEDLE_NOT_FOUND')
print(text[pos:pos+14000])
