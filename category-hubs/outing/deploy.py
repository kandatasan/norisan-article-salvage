import base64, json, os, pathlib, urllib.error, urllib.request, time

BASE='https://tsurikue.com/wp-json/wp/v2'
PAGE_ID=3154
SLUG='odekake'
TITLE='おでかけ｜広島・山口・中国地方の観光・ドライブ・旅行'
STATUS='draft'
PARENT_ID=7
CHILD_ID=8
MARKER='<!-- tsurikue-category-hub:v1:outing -->'
NAV_REF_START='<!-- tq-global-site-nav-ref:v1 start -->'
NAV_REF_END='<!-- tq-global-site-nav-ref:v1 end -->'
HERE=pathlib.Path(__file__).resolve().parent
SOURCE=HERE/'content.html'
PLACEHOLDER='{{OUTING_CATEGORY_IDS}}'

user=os.environ['TSURIKUE_WP_USER']
pw=os.environ['TSURIKUE_WP_APP_PASSWORD']
token=base64.b64encode(f'{user}:{pw}'.encode()).decode()
HEADERS={'Authorization':'Basic '+token,'Accept':'application/json','Content-Type':'application/json; charset=utf-8','User-Agent':'tsurikue-outing-hub-deploy/1.7'}

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

def ensure_default_card_layouts(template):
    classes=('tq-out-trip-card','tq-out-trip-copy','tq-out-route-card','tq-out-route-copy')
    changed=0; defaults={}
    for cls in classes:
        old=f'<!-- wp:group {{"className":"{cls}","layout":{{"type":"constrained"}}}} -->'
        new=f'<!-- wp:group {{"className":"{cls}","layout":{{"type":"default"}}}} -->'
        count=template.count(old)
        if count:
            template=template.replace(old,new); changed+=count
        defaults[cls]=template.count(new)
    if not all(v>0 for v in defaults.values()):
        raise RuntimeError('DEFAULT_CARD_LAYOUT_MISSING '+json.dumps(defaults,ensure_ascii=False))
    return template, changed, defaults

def build_content():
    template=SOURCE.read_text(encoding='utf-8')
    if MARKER not in template:
        raise RuntimeError('SOURCE_MARKER_MISSING')
    template,layout_replacements,default_counts=ensure_default_card_layouts(template)
    if template.count(PLACEHOLDER)!=1:
        raise RuntimeError(f'PLACEHOLDER_COUNT_INVALID count={template.count(PLACEHOLDER)}')
    template=template.replace(PLACEHOLDER,f'{PARENT_ID},{CHILD_ID}')
    if PLACEHOLDER in template:
        raise RuntimeError('UNRESOLVED_TEMPLATE_TOKEN')
    if NAV_REF_START in template or NAV_REF_END in template:
        raise RuntimeError('SOURCE_MUST_NOT_CONTAIN_TEMP_NAV_REF')
    return template,layout_replacements,default_counts

def verify_content(c):
    checks={
      'marker':MARKER in c,
      'temp_nav_absent':NAV_REF_START not in c and NAV_REF_END not in c,
      'latest_block':'wp:latest-posts' in c,
      'parent_cat':str(PARENT_ID) in c,
      'child_cat':str(CHILD_ID) in c,
      'hero':'次の休日、' in c,
      'archive_link':'/category/sightseeing-leisure/' in c,
      'trip_card_default':'<!-- wp:group {"className":"tq-out-trip-card","layout":{"type":"default"}} -->' in c,
      'trip_copy_default':'<!-- wp:group {"className":"tq-out-trip-copy","layout":{"type":"default"}} -->' in c,
      'route_card_default':'<!-- wp:group {"className":"tq-out-route-card","layout":{"type":"default"}} -->' in c,
      'route_copy_default':'<!-- wp:group {"className":"tq-out-route-copy","layout":{"type":"default"}} -->' in c,
    }
    if not all(checks.values()):
        raise RuntimeError('VERIFY_CONTENT_FAILED '+json.dumps(checks,ensure_ascii=False))
    return checks

def main():
    content,layout_replacements,default_counts=build_content()
    verify_content(content)

    # Directly read the known managed draft. Avoid /categories collection calls,
    # which intermittently time out on this WordPress install.
    existing=request(f'/pages/{PAGE_ID}?context=edit&_fields=id,slug,status,title,content,excerpt,link',attempts=2,timeout=25)
    current=raw(existing,'content')
    if existing.get('id')!=PAGE_ID or existing.get('slug')!=SLUG:
        raise RuntimeError(f'REFUSE_WRONG_PAGE id={existing.get("id")} slug={existing.get("slug")}')
    if existing.get('status')!='draft':
        raise RuntimeError(f'REFUSE_OVERWRITE_NON_DRAFT status={existing.get("status")}')
    if MARKER not in current:
        raise RuntimeError('REFUSE_OVERWRITE_UNRELATED_PAGE')

    payload={
      'title':TITLE,'slug':SLUG,'status':STATUS,'content':content,
      'excerpt':'広島・山口・中国地方を中心に、実際に出かけた観光地・ドライブ・旅行モデルコースから次の休日を探せる、つりくえ！のおでかけ入口です。'
    }
    page=request(f'/pages/{PAGE_ID}',method='POST',payload=payload,attempts=3,timeout=40)
    if page.get('id')!=PAGE_ID or page.get('slug')!=SLUG or page.get('status')!='draft':
        raise RuntimeError('POST_RESPONSE_VERIFY_FAILED '+json.dumps({'id':page.get('id'),'slug':page.get('slug'),'status':page.get('status')},ensure_ascii=False))

    check=request(f'/pages/{PAGE_ID}?context=edit&_fields=id,slug,status,title,content,link',attempts=2,timeout=25)
    checks=verify_content(raw(check,'content'))
    checks.update({'slug':check.get('slug')==SLUG,'status':check.get('status')==STATUS})
    if not all(checks.values()):
        raise RuntimeError('FINAL_VERIFY_FAILED '+json.dumps(checks,ensure_ascii=False))

    print(json.dumps({
      'action':'UPDATED','page_id':PAGE_ID,'slug':SLUG,'status':check.get('status'),
      'title':raw(check,'title'),'preview_link':f'https://tsurikue.com/?page_id={PAGE_ID}&preview=true',
      'outing_category_id':PARENT_ID,'model_course_category_id':CHILD_ID,
      'temporary_nav':'absent','layout_replacements':layout_replacements,
      'default_counts':default_counts,'checks':checks
    },ensure_ascii=False))

if __name__=='__main__': main()
