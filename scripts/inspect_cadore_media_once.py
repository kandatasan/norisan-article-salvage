#!/usr/bin/env python3
import base64,json,os,re,urllib.parse,urllib.request
SITE='https://tsurikue.com'; BASE=SITE+'/wp-json/wp/v2'
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()
H={'Authorization':AUTH,'Accept':'application/json','User-Agent':'tsurikue-cadore-inspect/1.0'}
def get(path):
    r=urllib.request.Request(BASE+path,headers=H)
    with urllib.request.urlopen(r,timeout=60) as x:return json.loads(x.read().decode())
def main():
    terms=['カドーレ','ジェラート','牧場']
    posts=[]
    for term in terms:
        rows=get('/posts?'+urllib.parse.urlencode({'search':term,'status':'any','context':'edit','per_page':100,'_fields':'id,slug,status,title,content,link'}))
        for p in rows:
            raw=p.get('content',{}).get('raw','')
            ids=sorted({int(x) for x in re.findall(r'wp-image-(\d+)',raw)})
            posts.append({'term':term,'id':p['id'],'slug':p['slug'],'status':p['status'],'title':p['title']['raw'],'link':p['link'],'image_ids':ids})
    # Search media titles/captions/slugs too
    media=[]
    for term in ['カドーレ','ジェラート','cadore']:
        rows=get('/media?'+urllib.parse.urlencode({'search':term,'context':'edit','per_page':100,'_fields':'id,slug,date,source_url,title,caption'}))
        for m in rows:
            media.append({'term':term,'id':m['id'],'slug':m['slug'],'date':m['date'],'url':m['source_url'],'title':m['title']['raw'],'caption':m['caption']['raw']})
    # Resolve all image ids referenced by matching posts
    ids=sorted({i for p in posts for i in p['image_ids']})
    refs=[]
    for i in ids:
        try:
            m=get(f'/media/{i}?context=edit&_fields=id,slug,date,source_url,title,caption,alt_text')
            refs.append({'id':m['id'],'slug':m['slug'],'date':m['date'],'url':m['source_url'],'title':m['title']['raw'],'caption':m['caption']['raw'],'alt':m.get('alt_text','')})
        except Exception as e:
            refs.append({'id':i,'error':str(e)})
    detail=get('/posts/1911?context=edit&_fields=id,title,content')
    raw=detail['content']['raw']
    contexts=[]
    for mm in re.finditer(r'wp-image-(\\d+)',raw):
        contexts.append({'image_id':int(mm.group(1)),'context':re.sub(r'\\s+',' ',raw[max(0,mm.start()-500):mm.end()+500])})
    print(json.dumps({'posts':posts,'media_search':media,'referenced_media':refs,'post1911_contexts':contexts},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
