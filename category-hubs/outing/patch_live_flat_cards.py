import base64,json,os,re,time,urllib.error,urllib.request
PAGE_ID=3154
BASE='https://tsurikue.com/wp-json/wp/v2'
MARKER='<!-- tsurikue-category-hub:v1:outing -->'
FIX='/* TQ OUTING FLAT CARD FIX v1 */'
TRIP_WRAP='class="wp-block-group tq-out-trip-copy"'
ROUTE_WRAP='class="wp-block-group tq-out-route-copy"'
user=os.environ['TSURIKUE_WP_USER']; pw=os.environ['TSURIKUE_WP_APP_PASSWORD']
token=base64.b64encode(f'{user}:{pw}'.encode()).decode()
H={'Authorization':'Basic '+token,'Accept':'application/json','Content-Type':'application/json; charset=utf-8','User-Agent':'tsurikue-outing-flat-card-fix/1.1'}
def req(path,method='GET',payload=None,attempts=4,timeout=28):
    data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode()
    last=None
    for n in range(attempts):
        try:
            r=urllib.request.Request(BASE+path,data=data,headers=H,method=method)
            with urllib.request.urlopen(r,timeout=timeout) as x:return json.loads(x.read().decode())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f'HTTP {e.code}: '+e.read().decode('utf-8','replace')[:500])
        except Exception as e:
            last=e
            if n+1<attempts: time.sleep(5*(n+1))
    raise RuntimeError(f'REQUEST_FAILED {method} {path}: {last}')
def raw(p): return (p.get('content') or {}).get('raw') or ''
def flatten(cls,s):
    pat=re.compile(rf'<!-- wp:group \{{"className":"{re.escape(cls)}","layout":\{{"type":"(?:constrained|default)"\}}\}} -->\s*<div class="wp-block-group {re.escape(cls)}">(.*?)</div>\s*<!-- /wp:group -->',re.S)
    return pat.subn(lambda m:m.group(1),s)

def verify(c,status):
    checks={'draft':status=='draft','marker':MARKER in c,'fix':FIX in c,'trip_copy_removed':TRIP_WRAP not in c,'route_copy_removed':ROUTE_WRAP not in c,'trip_cards':c.count('class="wp-block-group tq-out-trip-card"')==4,'route_cards':c.count('class="wp-block-group tq-out-route-card"')==3,'temp_nav_absent':'tq-global-site-nav-ref:v1' not in c}
    if not all(checks.values()): raise SystemExit('VERIFY_FAILED '+json.dumps(checks,ensure_ascii=False))
    return checks

page=req(f'/pages/{PAGE_ID}?context=edit&_fields=id,slug,status,content')
content=raw(page)
if page.get('status')!='draft' or MARKER not in content: raise SystemExit('REFUSE_WRONG_PAGE_STATE')
if FIX in content and TRIP_WRAP not in content and ROUTE_WRAP not in content:
    checks=verify(content,page.get('status'))
    print(json.dumps({'page_id':PAGE_ID,'already_flat':True,'checks':checks},ensure_ascii=False)); raise SystemExit(0)
original=content
content,n1=flatten('tq-out-trip-copy',content); content,n2=flatten('tq-out-route-copy',content)
if n1!=4 or n2!=3: raise SystemExit(f'UNEXPECTED_FLATTEN_COUNTS trip={n1} route={n2}')
for cls in ('tq-out-trip-card','tq-out-route-list','tq-out-route-card'):
    content=re.sub(rf'(<!-- wp:group \{{"className":"{re.escape(cls)}","layout":\{{"type":")(?:constrained|default)("\}}\}} -->)',r'\1default\2',content)
content=re.sub(r'/\* TQ OUTING FLAT CARD FIX v1 \*/.*?/\* END TQ OUTING FLAT CARD FIX v1 \*/','',content,flags=re.S)
css=r'''/* TQ OUTING FLAT CARD FIX v1 */
@media(min-width:861px){
.tq-out .tq-out-trip-card{display:grid!important;grid-template-columns:90px minmax(0,1fr)!important;grid-template-rows:auto auto auto!important;column-gap:20px!important;row-gap:7px!important;align-items:center!important}
.tq-out .tq-out-trip-card>*{min-width:0!important;max-width:none!important;margin-left:0!important;margin-right:0!important}
.tq-out .tq-out-trip-badge{grid-column:1!important;grid-row:1/4!important;justify-self:start!important}
.tq-out .tq-out-trip-label{grid-column:2!important;grid-row:1!important;width:auto!important;margin:0!important;white-space:nowrap!important;word-break:keep-all!important}
.tq-out .tq-out-trip-card>h3{grid-column:2!important;grid-row:2!important;width:auto!important;margin:0!important;font-size:18px!important;line-height:1.5!important;writing-mode:horizontal-tb!important;word-break:normal!important;overflow-wrap:break-word!important}
.tq-out .tq-out-trip-card>h3 a{writing-mode:horizontal-tb!important;word-break:normal!important}
.tq-out .tq-out-trip-text{grid-column:2!important;grid-row:3!important;width:auto!important;margin:0!important;writing-mode:horizontal-tb!important;word-break:normal!important}
.tq-out .tq-out-route-list{display:grid!important;gap:10px!important;width:100%!important;max-width:none!important}
.tq-out .tq-out-route-card{display:grid!important;grid-template-columns:155px minmax(0,1fr) 28px!important;grid-template-rows:auto auto!important;column-gap:22px!important;row-gap:5px!important;align-items:center!important}
.tq-out .tq-out-route-card>*{min-width:0!important;max-width:none!important;margin-left:0!important;margin-right:0!important}
.tq-out .tq-out-route-label{grid-column:1!important;grid-row:1/3!important;width:auto!important;white-space:nowrap!important;word-break:keep-all!important}
.tq-out .tq-out-route-card>h3{grid-column:2!important;grid-row:1!important;width:auto!important;margin:0!important;font-size:18px!important;line-height:1.5!important;writing-mode:horizontal-tb!important;word-break:normal!important;overflow-wrap:break-word!important}
.tq-out .tq-out-route-card>h3 a{writing-mode:horizontal-tb!important;word-break:normal!important}
.tq-out .tq-out-route-text{grid-column:2!important;grid-row:2!important;width:auto!important;margin:0!important;writing-mode:horizontal-tb!important}
.tq-out .tq-out-route-arrow{grid-column:3!important;grid-row:1/3!important;width:auto!important;margin:0!important}}
@media(max-width:600px){
.tq-out .tq-out-trip-card,.tq-out .tq-out-route-card{display:block!important;width:100%!important;max-width:none!important}
.tq-out .tq-out-trip-badge,.tq-out .tq-out-route-label{display:inline-flex!important;width:auto!important;height:auto!important;margin:0 0 12px!important;padding:8px 12px!important;border-radius:999px!important;white-space:nowrap!important;word-break:keep-all!important}
.tq-out .tq-out-trip-label{display:block!important;width:100%!important;margin:0 0 7px!important;white-space:normal!important}
.tq-out .tq-out-trip-card>h3,.tq-out .tq-out-route-card>h3{display:block!important;width:100%!important;margin:0!important;font-size:19px!important;line-height:1.55!important;writing-mode:horizontal-tb!important;word-break:normal!important;overflow-wrap:break-word!important}
.tq-out .tq-out-trip-text,.tq-out .tq-out-route-text{display:block!important;width:100%!important;margin:8px 0 0!important;writing-mode:horizontal-tb!important;word-break:normal!important}
.tq-out .tq-out-route-arrow{display:none!important}}
/* END TQ OUTING FLAT CARD FIX v1 */'''
if '</style>' not in content: raise SystemExit('STYLE_CLOSE_NOT_FOUND')
content=content.replace('</style>',css+'\n</style>',1)
if content==original: raise SystemExit('NO_CHANGE')
req(f'/pages/{PAGE_ID}','POST',{'content':content})
check=req(f'/pages/{PAGE_ID}?context=edit&_fields=id,status,content'); c=raw(check); checks=verify(c,check.get('status'))
print(json.dumps({'page_id':PAGE_ID,'flattened_trip':n1,'flattened_route':n2,'checks':checks},ensure_ascii=False))