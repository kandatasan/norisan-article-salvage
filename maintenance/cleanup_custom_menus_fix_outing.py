import base64, json, os, re, time, urllib.error, urllib.parse, urllib.request

BASE='https://tsurikue.com/wp-json/wp/v2'
TOP_PAGE_ID=2983
OUTING_PAGE_ID=3154
TOP_MARKER='<!-- tsurikue-experimental-page:v1:top-design-lab -->'
OUTING_MARKER='<!-- tsurikue-category-hub:v1:outing -->'
NAV_BLOCK_TITLE='つりくえ！共通ナビ（自動管理）'
NAV_BLOCK_MARKER='<!-- tq-global-site-nav:v1 -->'
REF_START='<!-- tq-global-site-nav-ref:v1 start -->'
PC_FIX_START='<!-- tq-outing-pc-card-width-fix:v1 start -->'
PC_FIX_END='<!-- tq-outing-pc-card-width-fix:v1 end -->'

user=os.environ['TSURIKUE_WP_USER']
pw=os.environ['TSURIKUE_WP_APP_PASSWORD']
token=base64.b64encode(f'{user}:{pw}'.encode()).decode()
HEADERS={'Authorization':'Basic '+token,'Accept':'application/json','Content-Type':'application/json; charset=utf-8','User-Agent':'tsurikue-cleanup-custom-nav/1.0'}

def request(path,method='GET',payload=None,attempts=4,timeout=45):
    data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode('utf-8')
    last=None
    for n in range(1,attempts+1):
        req=urllib.request.Request(BASE+path,data=data,headers=HEADERS,method=method)
        try:
            with urllib.request.urlopen(req,timeout=timeout) as r:
                body=r.read().decode('utf-8')
                return json.loads(body) if body else None
        except urllib.error.HTTPError as e:
            body=e.read().decode('utf-8','replace')
            raise RuntimeError(f'HTTP {e.code} {method} {path}: {body[:700]}') from e
        except Exception as e:
            last=e
            if n<attempts: time.sleep(4*n)
    raise RuntimeError(f'REQUEST_FAILED {method} {path}: {last}')

def raw_content(obj):
    return ((obj.get('content') or {}).get('raw') or '')

def get_page(pid):
    return request(f'/pages/{pid}?context=edit&_fields=id,slug,status,title,content')

def put_content(pid,content):
    return request(f'/pages/{pid}',method='POST',payload={'content':content})

def clean_top_custom_menu():
    page=get_page(TOP_PAGE_ID); content=raw_content(page); status=page.get('status')
    if TOP_MARKER not in content: raise RuntimeError('TOP_MARKER_MISSING')
    clean=re.sub(r'\n?/\* TQ HEADER DRAWER PROTOTYPE v1 \*/.*?/\* END TQ HEADER DRAWER PROTOTYPE v1 \*/\n?','\n',content,flags=re.S)
    clean=re.sub(r'\n?<p><!-- TQ HEADER NAV PROTOTYPE v1 START --></p>.*?<p><!-- TQ HEADER NAV PROTOTYPE v1 END --></p>\s*','\n',clean,flags=re.S)
    clean=re.sub(r'\n?<!-- TQ HEADER NAV PROTOTYPE v1 START -->.*?<!-- TQ HEADER NAV PROTOTYPE v1 END -->\n?','\n',clean,flags=re.S)
    if clean!=content: put_content(TOP_PAGE_ID,clean)
    after=get_page(TOP_PAGE_ID); a=raw_content(after)
    if after.get('status')!=status: raise RuntimeError('TOP_STATUS_CHANGED')
    bad=['TQ HEADER DRAWER PROTOTYPE','TQ HEADER NAV PROTOTYPE','tq-site-menu-toggle','class="tq-site-nav"']
    remain=[x for x in bad if x in a]
    if remain: raise RuntimeError('TOP_CUSTOM_NAV_REMAINS '+repr(remain))
    print('TOP_CUSTOM_NAV_REMOVED')

def fix_outing_desktop_cards():
    page=get_page(OUTING_PAGE_ID); content=raw_content(page); status=page.get('status')
    if status!='draft' or OUTING_MARKER not in content: raise RuntimeError('OUTING_DRAFT_GUARD_FAILED')
    # Constrained nested groups are the root of the desktop min-content collapse.
    targets=['tq-out-trip-card','tq-out-trip-copy','tq-out-route-list','tq-out-route-card','tq-out-route-copy']
    for cls in targets:
        content=content.replace(f'{{"className":"{cls}","layout":{{"type":"constrained"}}}}',f'{{"className":"{cls}","layout":{{"type":"default"}}}}')
    content=re.sub(re.escape(PC_FIX_START)+r'.*?'+re.escape(PC_FIX_END),'',content,flags=re.S)
    patch=r'''
<!-- wp:html -->
<!-- tq-outing-pc-card-width-fix:v1 start -->
<style>
@media(min-width:861px){
  .tq-out .tq-out-trip-card{display:grid!important;grid-template-columns:82px minmax(0,1fr)!important;gap:18px!important;align-items:center!important}
  .tq-out .tq-out-route-card{display:grid!important;grid-template-columns:145px minmax(0,1fr) auto!important;gap:24px!important;align-items:center!important}
  .tq-out .tq-out-trip-card>* , .tq-out .tq-out-route-card>*{min-width:0!important;max-width:none!important;margin-left:0!important;margin-right:0!important}
  .tq-out .tq-out-trip-copy,.tq-out .tq-out-route-copy{display:block!important;width:100%!important;min-width:0!important;max-width:none!important;margin:0!important;padding:0!important}
  .tq-out .tq-out-trip-copy>.wp-block-group__inner-container,.tq-out .tq-out-route-copy>.wp-block-group__inner-container{display:block!important;width:100%!important;min-width:0!important;max-width:none!important;margin:0!important;padding:0!important}
  .tq-out .tq-out-trip-copy>*,.tq-out .tq-out-trip-copy>.wp-block-group__inner-container>*,.tq-out .tq-out-route-copy>*,.tq-out .tq-out-route-copy>.wp-block-group__inner-container>*{width:100%!important;min-width:0!important;max-width:none!important;margin-left:0!important;margin-right:0!important;writing-mode:horizontal-tb!important;text-orientation:mixed!important}
  .tq-out .tq-out-trip-copy h3,.tq-out .tq-out-trip-copy h3 a,.tq-out .tq-out-trip-copy p,.tq-out .tq-out-route-copy h3,.tq-out .tq-out-route-copy h3 a,.tq-out .tq-out-route-copy p{white-space:normal!important;word-break:normal!important;overflow-wrap:break-word!important;writing-mode:horizontal-tb!important}
  .tq-out .tq-out-trip-label{white-space:nowrap!important;word-break:keep-all!important}
  .tq-out .tq-out-route-list,.tq-out .tq-out-route-list>.wp-block-group__inner-container{width:100%!important;max-width:none!important;margin-left:0!important;margin-right:0!important}
}
</style>
<!-- tq-outing-pc-card-width-fix:v1 end -->
<!-- /wp:html -->
'''
    content=content.rstrip()+"\n"+patch
    put_content(OUTING_PAGE_ID,content)
    after=get_page(OUTING_PAGE_ID); a=raw_content(after)
    checks={
      'status_draft':after.get('status')=='draft',
      'marker':OUTING_MARKER in a,
      'pc_fix':PC_FIX_START in a,
      'temp_nav_absent':REF_START not in a,
      'trip_default':'"className":"tq-out-trip-copy","layout":{"type":"default"}' in a,
      'route_default':'"className":"tq-out-route-copy","layout":{"type":"default"}' in a,
    }
    if not all(checks.values()): raise RuntimeError('OUTING_FIX_VERIFY_FAILED '+json.dumps(checks,ensure_ascii=False))
    print('OUTING_PC_CARDS_FIXED '+json.dumps(checks,ensure_ascii=False))

def delete_unused_nav_block_best_effort():
    try:
        blocks=request('/blocks?context=edit&per_page=100&_fields=id,title,status,content')
        for b in blocks:
            title=((b.get('title') or {}).get('raw') or '')
            c=raw_content(b)
            if title==NAV_BLOCK_TITLE or NAV_BLOCK_MARKER in c:
                bid=b['id']
                try:
                    request(f'/blocks/{bid}?force=true',method='DELETE')
                    print(f'DELETED_NAV_BLOCK id={bid}')
                except Exception as e:
                    print(f'NAV_BLOCK_DELETE_SKIPPED id={bid} error={e}')
    except Exception as e:
        print('NAV_BLOCK_SCAN_SKIPPED',e)

clean_top_custom_menu()
fix_outing_desktop_cards()
delete_unused_nav_block_best_effort()
print('CUSTOM_MENU_CLEANUP_AND_OUTING_FIX_DONE')
