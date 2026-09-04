#!/usr/bin/env python3
import base64,json,os,re,urllib.request
SITE='https://tsurikue.com'; BASE=SITE+'/wp-json/wp/v2'
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()
H={'Authorization':AUTH,'Accept':'application/json','User-Agent':'tsurikue-cadore-current/1.0'}
def get(path):
    r=urllib.request.Request(BASE+path,headers=H)
    with urllib.request.urlopen(r,timeout=60) as x:return json.loads(x.read().decode())
def main():
    p=get('/posts/3548?context=edit&_fields=id,status,slug,title,content,featured_media,modified')
    raw=p['content']['raw']
    ids=sorted({int(x) for x in re.findall(r'wp-image-(\d+)',raw)})
    vids=re.findall(r'<video[^>]+src="([^"]+)"',raw)
    media=[]
    for i in ids:
        try:
            m=get(f'/media/{i}?context=edit&_fields=id,slug,source_url,mime_type,title')
            media.append({'id':m['id'],'slug':m['slug'],'url':m['source_url'],'mime':m['mime_type'],'title':m['title']['raw']})
        except Exception as e: media.append({'id':i,'error':str(e)})
    print(json.dumps({'post':{'id':p['id'],'status':p['status'],'slug':p['slug'],'title':p['title']['raw'],'featured_media':p['featured_media'],'modified':p['modified']},'image_ids':ids,'video_urls':vids,'media':media,'raw':raw},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
