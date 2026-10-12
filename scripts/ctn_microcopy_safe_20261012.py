#!/usr/bin/env python3
"""Guarded published-post CTN CTA improvement; Oct 11 export SHA as strict preflight."""
from __future__ import annotations
import base64, hashlib, json, os, re, sys, urllib.parse, urllib.request
from pathlib import Path

SITE = 'https://tsurikue.com'
TARGETS = [[2222,"ux-resale","8ed61f6d79410fd6d49c68bf09b9984629725ca595d89373a953edbc0ec0746a","査定額に納得してから、売るか決めればOK。",2184],[2240,"ux-mitsumori","2d34c95d02427e4ead11d4b140fc5f329e5c2519e8d6d7a3994265b864ae9ff1","やり取りは最大3社。売却は査定額を見てから。",2184],[2329,"ux300h","a8550bed15a79ce580ec66e0dd853674bc74cfd0d9c449d8a03bc84af276201d","やり取りは最大3社。電話の負担を抑えて比較。",2184],[2517,"ux-koukai","4597692f1970fd9969fccf3c56eff4fba1dbff5033a06e3d916ce65e4c3637cc","売却は査定額に納得してから決めればOK。",2184],[2948,"lexus-ux-used","1057b87bf2ede332233050865fef2c735dbc67e02adad20d5269efc17ee96910","やり取りは最大3社。電話の負担を抑えて比較。",2184],[2956,"lexus-ux-price","85b7ad1aa5f590e52d84252d5ebc158b356b7eecd29cd9c0ebe1f6996ca35413","売却は、査定額を見てから決めればOK。",2184],[2962,"lexus-ux-discount","e3c2dca242875012d99365f71860dfa64eab0894fbfa20e4848640fa597c2428","やり取りは最大3社。売却は納得してから。",2184],[3570,"lexus-ux-emotional-explorer","fc25d1b28388915d9d781c0f54359a994e2a4989d9ba877593a3b7e5a9388389","やり取りは最大3社。買い替えは予算を見てから。",2184],[3601,"lexus-ux250h-used-vs-ux300h","15d6ec3049d267a59ece1e748be3bee905f739064fa95b811106b66410616dcd","売るかどうかは、査定額を見てから。",2184],[3604,"lexus-ux-vs-nx","1532a1f81f45fc19daf40352c42409863cbfdc173f8f63995dd4f5c002d62d31","やり取りは最大3社。売却するかは金額を見てから。",2184],[3606,"lexus-ux-vs-lbx","567ebd46571c335b0236ca0f94d3634397a532aa5e8e2cfdd892f2d3662bf8a0","やり取りする買取店は最大3社。",2184],[3608,"lexus-lbx-regret","c0a74706dd7cf779595933d390d13652c0dadede38ab4988c54a0b29284dac23","売却は、査定額に納得してから決めればOK。",2184],[3611,"lexus-lbx-options","16159611cbab252868e75f62608e37bf1a1b67905aea8cd94cba2279e32606eb","売却は、査定額に納得してから決めればOK。",2184],[3614,"car-sell-high","1acd58db6e2736123ac995188b81f5b2afdbbcbc93c231399746379304c27125","納得できる金額なら、そのとき売却を考える。",2184],[3835,"goodbuy","ca999e10c096758bc5f258ab3e092db2430b5eca610594a560a6c2ba54717a87","やり取りは最大3社。売るかどうかは金額を見てから。",2184],[3863,"lexus-lbx-cheap","9fe7657028956e11dc2d42c2d3a1b6f5bcc67cfc6c6ce80dcbf6d376f6fe4a95","装備を削る前に、今の車の買取額も比較。",2846],[3936,"lexus-lbx-price","aaa0cb0ce2b7c3f335cad4d71195ffee5fd945bb29e15620170d63cc7cab218a","最大3社とのやり取り。売却は納得してから。",2184],[3767,"landcruiser-fj-price","78522127f1eb9851f78dec2f1867462ba612904b2b4c4823925579faeefc98fe","やり取りは最大3社。売却は査定額を見てから。",3788],[3816,"landcruiser-fj-cheap","ce43bd4870452ecca6c515d9af05fb5b016ccbbb64bfac6aaadf4039065dfb02","買取店とのやり取りは最大3社。売却は納得してから。",3788]]
UNCHANGED = [(3774,'landcruiser-fj-review'),(3777,'landcruiser-fj-rear-seat'),(3778,'landcruiser-fj-drawbacks'),(4004,'tanto-model-history')]
SC = '<!-- wp:shortcode -->\n[blog_parts id="%s"]\n<!-- /wp:shortcode -->'
COPY = '<!-- wp:paragraph {"align":"center"} -->\n<p class="has-text-align-center"><strong>%s</strong></p>\n<!-- /wp:paragraph -->'
PREVIOUS = r'(<!-- wp:paragraph(?: \{[^\n]*\})? -->\s*<p class="has-text-align-center"><strong>)([^<]{3,100})(</strong></p>\s*<!-- /wp:paragraph -->\s*)$'

def hash_content(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()

def transform(original, key):
    pid, slug, expected_sha, microcopy, part = key
    anchor = SC % part
    if original.count(anchor) != 1:
        raise RuntimeError(f'{slug}: expected one primary CTA shortcode {part}, found {original.count(anchor)}')
    before, after = original.split(anchor, 1)
    old_microcopy = re.search(PREVIOUS, before)
    if old_microcopy:
        before = before[:old_microcopy.start(2)] + microcopy + before[old_microcopy.end(2):]
    else:
        before = before.rstrip() + '\n\n' + COPY % microcopy + '\n\n'
    modified = before + anchor + after
    if pid == 3863:
        modified = modified.replace(anchor, SC % 2184, 1)
    if pid in (3606, 3608, 3611):
        modified = modified.replace('カーズセブン', 'カーセブン')
    if modified == original: raise RuntimeError(f'{slug}: no difference')
    block_delta = 0 if old_microcopy else 1
    for p in ('<!-- wp:', '<!-- /wp:'):
        if modified.count(p) != original.count(p) + block_delta:
            raise RuntimeError(f'{slug}: Gutenberg block imbalance')
    for pattern in (r'<img\b', r'wp-image-\d+', r'https://px\.a8\.net/svt/ejp\?a8mat=[^"\s<]+'):
        if re.findall(pattern, modified) != re.findall(pattern, original):
            raise RuntimeError(f'{slug}: media or existing affiliate URL changed')
    for part_id in ('2184','2846','3788','2843','2890'):
        expected = original.count('[blog_parts id="' + part_id + '"]')
        if pid == 3863 and part_id in ('2184','2846'):
            expected += 1 if part_id == '2184' else -1
        if modified.count('[blog_parts id="' + part_id + '"]') != expected:
            raise RuntimeError(f'{slug}: shortcode count mismatch {part_id}')
    return modified

def request(endpoint, token, payload=None):
    headers={'Authorization':token,'Accept':'application/json','User-Agent':'tsurikue-ctn-microcopy/1.0'}
    if payload is not None: headers['Content-Type']='application/json; charset=utf-8'
    req=urllib.request.Request(SITE + endpoint,
        data=json.dumps(payload,ensure_ascii=False).encode() if payload is not None else None,
        headers=headers,method='POST' if payload is not None else 'GET')
    with urllib.request.urlopen(req,timeout=60) as r:
        return json.load(r),dict(r.headers)

def fetch(pid,token):
    q=urllib.parse.urlencode({'context':'edit','_fields':'id,slug,status,title,content,featured_media,categories,author'})
    return request(f'/wp-json/wp/v2/posts/{pid}?{q}',token)[0]

def current_total(token):
    q=urllib.parse.urlencode({'context':'edit','status':'publish','per_page':'1','_fields':'id'})
    return int(request('/wp-json/wp/v2/posts?'+q,token)[1]['X-WP-Total'])

def raw(row): return row['content']['raw']

def save(out,name,data):
    out.mkdir(parents=True,exist_ok=True)
    (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def execute(mode):
    username=os.getenv('TSURIKUE_WP_USER')
    password=os.getenv('TSURIKUE_WP_APP_PASSWORD')
    if not username or not password: raise RuntimeError('Missing WordPress secrets')
    token='Basic '+base64.b64encode((username+':'+password).encode()).decode()
    out=Path('reports/ctn-microcopy-20261012')
    before_total=current_total(token)
    ready=[]
    for key in TARGETS:
        row=fetch(key[0],token)
        if (row['id'],row['slug'],row['status']) != (key[0],key[1],'publish'):
            raise RuntimeError(f'{key[1]}: identity or publish status changed')
        old=raw(row)
        if hash_content(old)!=key[2]:
            raise RuntimeError(f'{key[1]}: content SHA differs from Oct 11 export; stopped before any writes')
        new=transform(old,key)
        ready.append((key,row,new))
    for pid,slug in UNCHANGED:
        row=fetch(pid,token)
        if (row['id'],row['slug'],row['status']) != (pid,slug,'publish'):
            raise RuntimeError(f'{slug}: preserve-only identity mismatch')
    save(out,'preflight.json',[{'id':key[0],'slug':key[1],'baseline_sha':key[2],'proposed_sha':hash_content(new)} for key,row,new in ready])
    print('PREFLIGHT_OK',len(ready),'changes and',len(UNCHANGED),'unchanged; public post count',before_total,flush=True)
    if mode=='check':return
    done=[]
    try:
        for key,row,new in ready:
            latest=fetch(key[0],token)
            if hash_content(raw(latest))!=key[2] or latest['status']!='publish':
                raise RuntimeError(f'{key[1]}: concurrent edit, stop')
            done.append((key,row,new))  # attempted write is rollback eligible
            request(f'/wp-json/wp/v2/posts/{key[0]}',token,{'content':new})
            verified=fetch(key[0],token)
            if any(verified[k]!=row[k] for k in ('id','slug','status','title','featured_media','categories','author')):
                raise RuntimeError(f'{key[1]}: protected field changed')
            if raw(verified)!=new:
                raise RuntimeError(f'{key[1]}: live content verification failed')
            if key[3] not in verified['content'].get('rendered',''):
                raise RuntimeError(f'{key[1]}: microcopy absent in rendered HTML')
            print('LIVE_VERIFIED',key[0],key[1],flush=True)
        if current_total(token)!=before_total: raise RuntimeError('published count changed')
        save(out,'result.json',{'status':'SUCCESS','verified':len(done),'preserved':len(UNCHANGED),'public_post_count':before_total})
    except Exception:
        for key,row,new in reversed(done):
            try:
                if hash_content(raw(fetch(key[0],token)))==hash_content(new):
                    request(f'/wp-json/wp/v2/posts/{key[0]}',token,{'content':raw(row)})
                    print('ROLLBACK',key[1],flush=True)
            except Exception as ex:
                print('ROLLBACK_FAILED',key[1],str(ex),flush=True)
        raise

if __name__=='__main__':
    mode=sys.argv[1] if len(sys.argv)>1 else 'check'
    if mode not in ('check','apply'):raise SystemExit('mode must be check or apply')
    execute(mode)
