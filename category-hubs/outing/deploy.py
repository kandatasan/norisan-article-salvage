import base64, json, os, pathlib, urllib.error, urllib.parse, urllib.request, time

BASE='https://tsurikue.com/wp-json/wp/v2'
SLUG='odekake'
TITLE='おでかけ｜広島・山口・中国地方の観光・ドライブ・旅行'
STATUS='draft'
MARKER='<!-- tsurikue-category-hub:v1:outing -->'
NAV_REF_START='<!-- tq-global-site-nav-ref:v1 start -->'
NAV_REF_END='<!-- tq-global-site-nav-ref:v1 end -->'
HERE=pathlib.Path(__file__).resolve().parent
SOURCE=HERE/'content.html'
PARENT_SLUG='sightseeing-leisure'
CHILD_SLUG='drive'
PLACEHOLDER='{{OUTING_CATEGORY_IDS}}'

user=os.environ['TSURIKUE_WP_USER']
pw=os.environ['TSURIKUE_WP_APP_PASSWORD']
token=base64.b64encode(f'{user}:{pw}'.encode()).decode()
HEADERS={'Authorization':'Basic '+token,'Accept':'application/json','Content-Type':'application/json; charset=utf-8','User-Agent':'tsurikue-outing-hub-deploy/1.6'}

def request(path, method='GET', payload=None, attempts=3, timeout=35):
    data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode('utf-8')
    last=None
    for attempt in range(1,attempts+1):
        req=urllib.request.Request(BASE+path,data=data,headers=HEADERS,method=method)
        try:
            with urllib.request.urlopen(req,timeout=timeout) as r:
                body=r.read().decode('utf-8')
                return json.loads(body) if body else None
        except urllib.error.HTTPError as e:
            body=e.read().decode('utf-8','replace')
            raise RuntimeError(f'HTTP {e.code} {method} {path}: {body[:800]}') from e
        except Exception as e:
            last=e
            if attempt<attempts:
                time.sleep(4*attempt)
    raise RuntimeError(f'REQUEST_FAILED {method} {path}: {type(last).__name__}: {last}')

def raw(obj, field):
    value=obj.get(field) or {}
    return value.get('raw') or value.get('rendered') or ''

def find_category(slug):
    q=urllib.parse.urlencode({'slug':slug,'context':'edit','per_page':10,'_fields':'id,slug,name,parent'})
    items=request('/categories?'+q)
    if len(items)!=1:
        raise RuntimeError(f'CATEGORY_NOT_UNIQUE slug={slug} count={len(items)}')
    return items[0]

def ensure_default_card_layouts(template):
    classes=('tq-out-trip-card','tq-out-trip-copy','tq-out-route-card','tq-out-route-copy')
    changed=0
    defaults={}
    for cls in classes:
        old=f'<!-- wp:group {{"className":"{cls}","layout":{{"type":"constrained"}}}} -->'
        new=f'<!-- wp:group {{"className":"{cls}","layout":{{"type":"default"}}}} -->'
        count=template.count(old)
        if count:
            template=template.replace(old,new)
            changed+=count
        defaults[cls]=template.count(new)
    if not all(v>0 for v in defaults.values()):
        raise RuntimeError('DEFAULT_CARD_LAYOUT_MISSING '+json.dumps(defaults,ensure_ascii=False))
    return template, changed, defaults

def build_content():
    parent=find_category(PARENT_SLUG)
    child=find_category(CHILD_SLUG)
    if child.get('parent')!=parent['id']:
        raise RuntimeError(f'CHILD_PARENT_MISMATCH child={child["id"]} parent={child.get("parent")} expected={parent["id"]}')
    template=SOURCE.read_text(encoding='utf-8')
    if MARKER not in template:
        raise RuntimeError('SOURCE_MARKER_MISSING')
    template, layout_replacements, default_counts=ensure_default_card_layouts(template)
    if template.count(PLACEHOLDER)!=1:
        raise RuntimeError(f'PLACEHOLDER_COUNT_INVALID count={template.count(PLACEHOLDER)}')
    template=template.replace(PLACEHOLDER,f'{parent["id"]},{child["id"]}')
    if PLACEHOLDER in template:
        raise RuntimeError('UNRESOLVED_TEMPLATE_TOKEN')
    if NAV_REF_START in template or NAV_REF_END in template:
        raise RuntimeError('SOURCE_MUST_NOT_CONTAIN_TEMP_NAV_REF')
    return template, parent, child, layout_replacements, default_counts

def find_page():
    q=urllib.parse.urlencode({'slug':SLUG,'status':STATUS,'context':'edit','per_page':10,'_fields':'id,slug,status,title,content,excerpt,link'})
    items=request('/pages?'+q)
    if len(items)>1:
        raise RuntimeError(f'PAGE_NOT_UNIQUE slug={SLUG} status={STATUS} count={len(items)}')
    return items[0] if items else None

def verify(page_id,parent,child):
    check=request(f'/pages/{page_id}?context=edit&_fields=id,slug,status,title,content,link')
    c=raw(check,'content')
    checks={
      'slug':check.get('slug')==SLUG,
      'status':check.get('status')==STATUS,
      'marker':MARKER in c,
      'temp_nav_absent':NAV_REF_START not in c and NAV_REF_END not in c,
      'latest_block':'wp:latest-posts' in c,
      'parent_cat':str(parent['id']) in c,
      'child_cat':str(child['id']) in c,
      'hero':'次の休日、' in c,
      'archive_link':'/category/sightseeing-leisure/' in c,
      'trip_card_default':'<!-- wp:group {"className":"tq-out-trip-card","layout":{"type":"default"}} -->' in c,
      'trip_copy_default':'<!-- wp:group {"className":"tq-out-trip-copy","layout":{"type":"default"}} -->' in c,
      'route_card_default':'<!-- wp:group {"className":"tq-out-route-card","layout":{"type":"default"}} -->' in c,
      'route_copy_default':'<!-- wp:group {"className":"tq-out-route-copy","layout":{"type":"default"}} -->' in c,
    }
    if not all(checks.values()):
        raise RuntimeError('VERIFY_FAILED '+json.dumps(checks,ensure_ascii=False))
    return check,checks

def main():
    content,parent,child,layout_replacements,default_counts=build_content()
    existing=find_page()
    payload={'title':TITLE,'slug':SLUG,'status':STATUS,'content':content,'excerpt':'広島・山口・中国地方を中心に、実際に出かけた観光地・ドライブ・旅行モデルコースから次の休日を探せる、つりくえ！のおでかけ入口です。'}
    old_payload=None; created=False; page_id=None
    try:
        if existing:
            current=raw(existing,'content')
            if MARKER not in current:
                raise RuntimeError(f'REFUSE_OVERWRITE_UNRELATED_PAGE id={existing["id"]} status={existing.get("status")}')
            if existing.get('status')!='draft':
                raise RuntimeError(f'REFUSE_OVERWRITE_NON_DRAFT id={existing["id"]} status={existing.get("status")}')
            old_payload={'title':raw(existing,'title'),'slug':existing.get('slug'),'status':existing.get('status'),'content':current,'excerpt':raw(existing,'excerpt')}
            page=request(f'/pages/{existing["id"]}',method='POST',payload=payload); action='UPDATED'
        else:
            page=request('/pages',method='POST',payload=payload); action='CREATED'; created=True
        page_id=page['id']; check,checks=verify(page_id,parent,child)
    except Exception:
        if page_id is not None:
            try:
                if created:
                    request(f'/pages/{page_id}?force=true',method='DELETE'); print(f'ROLLBACK_DELETED_NEW_PAGE id={page_id}')
                elif old_payload is not None:
                    request(f'/pages/{page_id}',method='POST',payload=old_payload); print(f'ROLLBACK_RESTORED_DRAFT id={page_id}')
            except Exception as rollback_error:
                print(f'ROLLBACK_FAILED id={page_id} error={rollback_error}')
        raise
    print(json.dumps({'action':action,'page_id':page_id,'slug':SLUG,'status':check.get('status'),'title':raw(check,'title'),'preview_link':f'https://tsurikue.com/?page_id={page_id}&preview=true','temporary_nav':'absent','layout_replacements':layout_replacements,'default_counts':default_counts,'checks':checks},ensure_ascii=False))

if __name__=='__main__': main()
