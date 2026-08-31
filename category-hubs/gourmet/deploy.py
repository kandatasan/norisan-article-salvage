import base64,json,os,pathlib,urllib.parse,urllib.request,time
BASE='https://tsurikue.com/wp-json/wp/v2'; HERE=pathlib.Path(__file__).parent
content=HERE.joinpath('content.html').read_text(encoding='utf-8')
user=os.environ['TSURIKUE_WP_USER']; pw=os.environ['TSURIKUE_WP_APP_PASSWORD']; token=base64.b64encode(f'{user}:{pw}'.encode()).decode()
H={'Authorization':'Basic '+token,'Content-Type':'application/json; charset=utf-8','User-Agent':'tsurikue-gourmet-hub/1.1'}
def req(path,method='GET',payload=None):
 data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode(); last=None
 for n in range(4):
  try:
   r=urllib.request.Request(BASE+path,data=data,headers=H,method=method)
   with urllib.request.urlopen(r,timeout=40) as x:return json.loads(x.read().decode())
  except Exception as e:last=e;time.sleep(4*(n+1))
 raise last
cats=req('/categories?'+urllib.parse.urlencode({'slug':'gourmet','per_page':10}))
if not cats: raise SystemExit('GOURMET_CATEGORY_NOT_FOUND')
content=content.replace('"categories":[6]',f'"categories":[{cats[0]["id"]}]')
slug='gourmet-guide'; title='グルメ｜広島・旅先で実際に食べたラーメン・ご当地グルメ'
q=urllib.parse.urlencode({'slug':slug,'status':'draft','context':'edit','per_page':10})
found=req('/pages?'+q); payload={'title':title,'slug':slug,'status':'draft','content':content}
page=req('/pages/'+str(found[0]['id']),'POST',payload) if found else req('/pages','POST',payload)
assert page['status']=='draft' and page['slug']==slug and 'tsurikue-category-hub:v1:gourmet-blocks' in page['content']['raw']
print(json.dumps({'id':page['id'],'slug':page['slug'],'status':page['status'],'category_id':cats[0]['id']},ensure_ascii=False))