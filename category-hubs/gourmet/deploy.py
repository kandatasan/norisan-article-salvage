import base64,json,os,pathlib,urllib.parse,urllib.request,time
BASE='https://tsurikue.com/wp-json/wp/v2'; HERE=pathlib.Path(__file__).parent
content=HERE.joinpath('content.html').read_text(encoding='utf-8')
user=os.environ['TSURIKUE_WP_USER']; pw=os.environ['TSURIKUE_WP_APP_PASSWORD']; token=base64.b64encode(f'{user}:{pw}'.encode()).decode()
H={'Authorization':'Basic '+token,'Content-Type':'application/json; charset=utf-8','User-Agent':'tsurikue-gourmet-hub/1.0'}
def req(path,method='GET',payload=None):
 data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode(); last=None
 for n in range(4):
  try:
   r=urllib.request.Request(BASE+path,data=data,headers=H,method=method)
   with urllib.request.urlopen(r,timeout=40) as x:return json.loads(x.read().decode())
  except Exception as e:last=e;time.sleep(4*(n+1))
 raise last
slug='gourmet-guide'; title='グルメ｜広島・旅先で実際に食べたラーメン・ご当地グルメ'
q=urllib.parse.urlencode({'slug':slug,'status':'draft','context':'edit','per_page':10})
found=req('/pages?'+q)
payload={'title':title,'slug':slug,'status':'draft','content':content}
if found:
 page=req('/pages/'+str(found[0]['id']),'POST',payload)
else:
 page=req('/pages','POST',payload)
assert page['status']=='draft' and page['slug']==slug
assert 'tsurikue-category-hub:v1:gourmet-blocks' in page['content']['raw']
print(json.dumps({'id':page['id'],'slug':page['slug'],'status':page['status']},ensure_ascii=False))