import base64, json, os, pathlib, urllib.error, urllib.parse, urllib.request, time

BASE='https://tsurikue.com/wp-json/wp/v2'
SLUG='odekake'
TITLE='おでかけ｜広島・山口・中国地方の観光・ドライブ・旅行'
STATUS='draft'
MARKER='<!-- tsurikue-category-hub:v1:outing -->'
NAV_MARKER='<!-- tq-global-site-nav:v1 -->'
NAV_REF_START='<!-- tq-global-site-nav-ref:v1 start -->'
NAV_REF_END='<!-- tq-global-site-nav-ref:v1 end -->'
HERE=pathlib.Path(__file__).resolve().parent
SOURCE=HERE/'content.html'
PARENT_SLUG='sightseeing-leisure'
CHILD_SLUG='drive'

user=os.environ['TSURIKUE_WP_USER']
pw=os.environ['TSURIKUE_WP_APP_PASSWORD']
token=base64.b64encode(f'{user}:{pw}'.encode()).decode()
HEADERS={'Authorization':'Basic '+token,'Accept':'application/json','Content-Type':'application/json; charset=utf-8','User-Agent':'tsurikue-outing-hub-deploy/1.1'}

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

def find_nav_block_id():
    blocks=request('/blocks?context=edit&per_page=100&_fields=id,title,status,content')
    for block in blocks:
        content=raw(block,'content')
        title=raw(block,'title')
        if NAV_MARKER in content or title=='つりくえ！共通ナビ（自動管理）':
            if block.get('status')!='publish':
                raise RuntimeError(f'NAV_BLOCK_NOT_PUBLISHED id={block["id"]}')
            return block['id']
    raise RuntimeError('NAV_BLOCK_NOT_FOUND')

def build_content():
    parent=find_category(PARENT_SLUG)
    child=find_category(CHILD_SLUG)
    if child.get('parent')!=parent['id']:
        raise RuntimeError(f'CHILD_PARENT_MISMATCH child={child["id"]} parent={child.get("parent")} expected={parent["id"]}')
    template=SOURCE.read_text(encoding='utf-8')
    if MARKER not in template:
        raise RuntimeError('SOURCE_MARKER_MISSING')
    template=template.replace('{{OUTING_CATEGORY_IDS}}',f'{parent["id"]},{child["id"]}')
    if '{{' in template or '}}' in template:
        raise RuntimeError('UNRESOLVED_TEMPLATE_TOKEN')
    nav_id=find_nav_block_id()
    nav=f'{NAV_REF_START}\n<!-- wp:block {{"ref":{nav_id}}} /-->\n{NAV_REF_END}\n\n'
    return nav+template, parent, child, nav_id

def find_page():
    q=urllib.parse.urlencode({'slug':SLUG,'context':'edit','per_page':10,'_fields':'id,slug,status,title,content,excerpt,link'})
    items=request('/pages?'+q)
    if len(items)>1:
        raise RuntimeError(f'PAGE_NOT_UNIQUE slug={SLUG} count={len(items)}')
    return items[0] if items else None

def verify(page_id,parent,child,nav_id):
    check=request(f'/pages/{page_id}?context=edit&_fields=id,slug,status,title,content,link')
    check_content=raw(check,'content')
    checks={
      'slug':check.get('slug')==SLUG,
      'status':check.get('status')==STATUS,
      'marker':MARKER in check_content,
      'nav_ref':NAV_REF_START in check_content and f'"ref":{nav_id}' in check_content,
      'latest_block':'wp:latest-posts' in check_content,
      'parent_cat':str(parent['id']) in check_content,
      'child_cat':str(child['id']) in check_content,
      'hero':'次の休日、' in check_content,
      'archive_link':'/category/sightseeing-leisure/' in check_content,
    }
    if not all(checks.values()):
        raise RuntimeError('VERIFY_FAILED '+json.dumps(checks,ensure_ascii=False))
    return check,checks

def main():
    content,parent,child,nav_id=build_content()
    existing=find_page()
    payload={'title':TITLE,'slug':SLUG,'status':STATUS,'content':content,'excerpt':'広島・山口・中国地方を中心に、実際に出かけた観光地・ドライブ・旅行モデルコースから次の休日を探せる、つりくえ！のおでかけ入口です。'}
    old_payload=None
    created=False
    page_id=None
    try:
        if existing:
            current=raw(existing,'content')
            if MARKER not in current:
                raise RuntimeError(f'REFUSE_OVERWRITE_UNRELATED_PAGE id={existing["id"]} status={existing.get("status")}')
            if existing.get('status')!='draft':
                raise RuntimeError(f'REFUSE_OVERWRITE_NON_DRAFT id={existing["id"]} status={existing.get("status")}')
            old_payload={'title':raw(existing,'title'),'slug':existing.get('slug'),'status':existing.get('status'),'content':current,'excerpt':raw(existing,'excerpt')}
            page=request(f'/pages/{existing["id"]}',method='POST',payload=payload)
            action='UPDATED'
        else:
            page=request('/pages',method='POST',payload=payload)
            action='CREATED'; created=True
        page_id=page['id']
        check,checks=verify(page_id,parent,child,nav_id)
    except Exception:
        if page_id is not None:
            try:
                if created:
                    request(f'/pages/{page_id}?force=true',method='DELETE')
                    print(f'ROLLBACK_DELETED_NEW_PAGE id={page_id}')
                elif old_payload is not None:
                    request(f'/pages/{page_id}',method='POST',payload=old_payload)
                    print(f'ROLLBACK_RESTORED_DRAFT id={page_id}')
            except Exception as rollback_error:
                print(f'ROLLBACK_FAILED id={page_id} error={rollback_error}')
        raise
    print(json.dumps({
      'action':action,
      'page_id':page_id,
      'slug':SLUG,
      'status':check.get('status'),
      'title':raw(check,'title'),
      'edit_link':f'https://tsurikue.com/wp-admin/post.php?post={page_id}&action=edit',
      'preview_link':f'https://tsurikue.com/?page_id={page_id}&preview=true',
      'outing_category_id':parent['id'],
      'model_course_category_id':child['id'],
      'nav_block_id':nav_id,
      'checks':checks,
    },ensure_ascii=False))

if __name__=='__main__': main()
