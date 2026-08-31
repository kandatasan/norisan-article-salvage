import base64, json, os, pathlib, re, sys, time, urllib.error, urllib.parse, urllib.request

BASE='https://tsurikue.com/wp-json/wp/v2'
BLOCK_TITLE='つりくえ！共通ナビ（自動管理）'
BLOCK_MARKER='<!-- tq-global-site-nav:v1 -->'
REF_START='<!-- tq-global-site-nav-ref:v1 start -->'
REF_END='<!-- tq-global-site-nav-ref:v1 end -->'
TOP_PAGE_ID=2983
CANARY_SLUG='ux-koukai'
NAV_SOURCE=pathlib.Path(__file__).with_name('nav-block.html')

user=os.environ['TSURIKUE_WP_USER']
pw=os.environ['TSURIKUE_WP_APP_PASSWORD']
token=base64.b64encode(f'{user}:{pw}'.encode()).decode()
HEADERS={
  'Authorization':'Basic '+token,
  'Accept':'application/json',
  'Content-Type':'application/json; charset=utf-8',
  'User-Agent':'tsurikue-sitewide-nav-deploy/1.0',
}

def request(path, method='GET', payload=None, attempts=3, timeout=35):
    url=BASE+path
    data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode('utf-8')
    last=None
    for attempt in range(1,attempts+1):
        req=urllib.request.Request(url,data=data,headers=HEADERS,method=method)
        try:
            with urllib.request.urlopen(req,timeout=timeout) as r:
                return json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            body=e.read().decode('utf-8','replace')
            raise RuntimeError(f'HTTP {e.code} {method} {path}: {body[:500]}') from e
        except Exception as e:
            last=e
            if attempt < attempts:
                time.sleep(4*attempt)
    raise RuntimeError(f'REQUEST_FAILED {method} {path}: {type(last).__name__}: {last}')

def raw_content(item):
    return (item.get('content') or {}).get('raw') or ''

def ensure_block():
    source=NAV_SOURCE.read_text(encoding='utf-8')
    blocks=request('/blocks?context=edit&per_page=100&_fields=id,title,status,content')
    found=None
    for b in blocks:
        if BLOCK_MARKER in raw_content(b) or ((b.get('title') or {}).get('raw') == BLOCK_TITLE):
            found=b; break
    if found:
        bid=found['id']
        if raw_content(found) != source or found.get('status') != 'publish':
            request(f'/blocks/{bid}',method='POST',payload={'title':BLOCK_TITLE,'status':'publish','content':source})
            print(f'UPDATED_BLOCK id={bid}')
        else:
            print(f'BLOCK_OK id={bid}')
    else:
        created=request('/blocks',method='POST',payload={'title':BLOCK_TITLE,'status':'publish','content':source})
        bid=created['id']
        print(f'CREATED_BLOCK id={bid}')
    check=request(f'/blocks/{bid}?context=edit&_fields=id,status,content')
    if check.get('status')!='publish' or BLOCK_MARKER not in raw_content(check):
        raise RuntimeError('BLOCK_VERIFY_FAILED')
    return bid

def ref_html(block_id):
    return f'{REF_START}\n<!-- wp:block {{"ref":{block_id}}} /-->\n{REF_END}\n\n'

def strip_ref(content):
    return re.sub(r'\s*<!-- tq-global-site-nav-ref:v1 start -->.*?<!-- tq-global-site-nav-ref:v1 end -->\s*','\n',content,flags=re.S)

def add_ref_to_item(kind,item,block_id):
    content=raw_content(item)
    if REF_START in content:
        return False
    updated=ref_html(block_id)+content
    request(f'/{kind}/{item["id"]}',method='POST',payload={'content':updated})
    verify=request(f'/{kind}/{item["id"]}?context=edit&_fields=id,content')
    if REF_START not in raw_content(verify) or f'"ref":{block_id}' not in raw_content(verify):
        raise RuntimeError(f'REF_VERIFY_FAILED {kind} {item["id"]}')
    return True

def get_canary():
    q=urllib.parse.urlencode({'slug':CANARY_SLUG,'context':'edit','_fields':'id,slug,status,content'})
    items=request('/posts?'+q)
    if len(items)!=1: raise RuntimeError(f'CANARY_NOT_UNIQUE count={len(items)}')
    return items[0]

def list_items(kind,status):
    page=1; out=[]
    while True:
        q=urllib.parse.urlencode({'context':'edit','status':status,'per_page':100,'page':page,'_fields':'id,slug,status,content'})
        try:
            batch=request(f'/{kind}?'+q)
        except RuntimeError as e:
            if 'HTTP 400' in str(e) and page>1: break
            raise
        out.extend(batch)
        if len(batch)<100: break
        page+=1
    return out

def rollout(block_id):
    changed=[]; seen=set()
    for kind in ('posts','pages'):
        for status in ('publish','draft'):
            for item in list_items(kind,status):
                key=(kind,item['id'])
                if key in seen: continue
                seen.add(key)
                if kind=='pages' and item['id']==TOP_PAGE_ID:
                    continue
                if add_ref_to_item(kind,item,block_id):
                    changed.append(key)
                    print(f'ADDED_REF {kind} id={item["id"]} slug={item.get("slug","")}')
                time.sleep(0.08)
    print(f'ROLLOUT_DONE changed={len(changed)} checked={len(seen)} block_id={block_id}')

def rollback_all():
    changed=0
    for kind in ('posts','pages'):
        for status in ('publish','draft'):
            for item in list_items(kind,status):
                content=raw_content(item)
                if REF_START not in content: continue
                cleaned=strip_ref(content)
                request(f'/{kind}/{item["id"]}',method='POST',payload={'content':cleaned})
                changed+=1
                print(f'REMOVED_REF {kind} id={item["id"]}')
                time.sleep(0.08)
    print(f'ROLLBACK_DONE changed={changed}')

mode=(sys.argv[1] if len(sys.argv)>1 else '').strip()
if mode=='canary':
    bid=ensure_block()
    item=get_canary()
    changed=add_ref_to_item('posts',item,bid)
    print(f'CANARY_READY id={item["id"]} block_id={bid} changed={changed}')
elif mode=='rollout':
    bid=ensure_block(); rollout(bid)
elif mode=='rollback':
    rollback_all()
else:
    raise SystemExit('usage: deploy.py canary|rollout|rollback')
