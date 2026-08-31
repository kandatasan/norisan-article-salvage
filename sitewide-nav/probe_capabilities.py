import base64, json, os, urllib.error, urllib.request

BASE='https://tsurikue.com/wp-json'
user=os.environ['TSURIKUE_WP_USER']
pw=os.environ['TSURIKUE_WP_APP_PASSWORD']
token=base64.b64encode(f'{user}:{pw}'.encode()).decode()
headers={'Authorization':'Basic '+token,'Accept':'application/json','User-Agent':'tsurikue-sitewide-nav-probe/1.0'}

checks=[
 ('me','/wp/v2/users/me?context=edit&_fields=id,roles,capabilities'),
 ('menu-items','/wp/v2/menu-items?context=edit&per_page=5'),
 ('menus','/wp/v2/menus?context=edit&per_page=5'),
 ('navigation','/wp/v2/navigation?context=edit&per_page=5'),
 ('widgets','/wp/v2/widgets?context=edit&per_page=5'),
 ('settings','/wp/v2/settings?context=edit'),
 ('custom-css-type','/wp/v2/types/custom_css?context=edit'),
 ('wp-blocks','/wp/v2/blocks?context=edit&per_page=5'),
 ('templates','/wp/v2/templates?context=edit&per_page=5'),
]

def fetch(path):
    req=urllib.request.Request(BASE+path,headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=25) as r:
            body=r.read().decode('utf-8','replace')
            return r.status, body
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8','replace')
    except Exception as e:
        return 'ERR', type(e).__name__+': '+str(e)

for name,path in checks:
    status,body=fetch(path)
    summary=''
    try:
        data=json.loads(body)
        if name=='me' and isinstance(data,dict):
            caps=data.get('capabilities') or {}
            wanted=['edit_posts','edit_pages','publish_posts','manage_categories','edit_theme_options','edit_widgets','activate_plugins','install_plugins','edit_css']
            summary={'roles':data.get('roles'), 'caps':{k:bool(caps.get(k)) for k in wanted}}
        elif isinstance(data,list):
            summary={'count':len(data),'sample_ids':[x.get('id') for x in data[:5] if isinstance(x,dict)]}
        elif isinstance(data,dict):
            summary={'keys':list(data.keys())[:12], 'code':data.get('code'), 'message':data.get('message')}
        else:
            summary=str(data)[:300]
    except Exception:
        summary=body[:300]
    print(f'{name}: status={status} summary={json.dumps(summary,ensure_ascii=False)}')
