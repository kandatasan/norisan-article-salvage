#!/usr/bin/env python3
from __future__ import annotations
import base64,json,os,re,urllib.parse,urllib.request

SITE='https://tsurikue.com'; UA='tsurikue-diagnose-lbx-links-20260928/1.0'
SLUGS=['lexus-lbx-price','lexus-lbx-interior','lexus-lbx-options','lexus-lbx-cheap','lexus-lbx-regret','lexus-ux-vs-lbx']
TOKEN=re.compile(r'<!--\s+/?wp:[\s\S]*?-->')
OPEN=re.compile(r'<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->')
CLOSE=re.compile(r'<!--\s+/wp:([\w\-/]+)\s+-->')

def auth():
 u=os.environ.get('TSURIKUE_WP_USER'); p=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
 return 'Basic '+base64.b64encode(f'{u}:{p}'.encode()).decode()
def req(url):
 r=urllib.request.Request(url,headers={'Authorization':auth(),'Accept':'application/json','User-Agent':UA})
 with urllib.request.urlopen(r,timeout=60) as resp:return json.loads(resp.read().decode())
def get(s):
 q=urllib.parse.urlencode({'context':'edit','slug':s,'status':'any','per_page':10,'_fields':'id,slug,status,content'})
 rows=req(f'{SITE}/wp-json/wp/v2/posts?{q}'); assert len(rows)==1; return rows[0]
def raw(r):
 v=r['content']; return v.get('raw') or v.get('rendered') or ''
def gp(text):
 stack=[]
 for m in TOKEN.finditer(text):
  t=m.group(0);o=OPEN.fullmatch(t);c=CLOSE.fullmatch(t)
  if o:
   if not o.group(2):stack.append(o.group(1))
  elif c:
   if not stack or stack[-1]!=c.group(1):return ('mismatch',stack[-5:],c.group(1))
   stack.pop()
 return ('remaining',stack[-10:]) if stack else ('ok',[])
def snippets(text,needle):
 out=[]
 for line in text.splitlines():
  if needle in line: out.append(line[:500])
 return out[:10]
def main():
 print('# Diagnose LBX link updater failure (GET only)')
 print('- wordpress_write_count: **0**')
 for s in SLUGS:
  c=raw(get(s)); print(f'\n## {s}'); print(f'- gutenberg={gp(c)}')
  print(f'- price_url_count={c.count("https://tsurikue.com/lexus-lbx-price/")}')
  if s=='lexus-lbx-interior':
   a='<p>価格だけならElegantやActiveもありますが、私が選ぶなら<strong>Relax</strong>です。</p>'
   print(f'- interior_anchor_count={c.count(a)}')
   print(f'- lines_with_価格だけなら={snippets(c,"価格だけなら")}')
  if s=='lexus-lbx-cheap':
   a='<p>LBXはElegantが420万円、Activeが440万円、RelaxとCoolが460万円です。</p>'
   print(f'- cheap_anchor_count={c.count(a)}')
   print(f'- lines_with_Elegantが420万円={snippets(c,"Elegantが420万円")}')
  if s in ['lexus-lbx-options','lexus-lbx-regret','lexus-ux-vs-lbx']:
   st=f'<!-- tq-lexus-related-cards:v1:{s} -->'; en='<!-- tq-lexus-related-cards:v1:end -->'
   print(f'- start_marker_count={c.count(st)} end_marker_count={c.count(en)}')
if __name__=='__main__':main()
