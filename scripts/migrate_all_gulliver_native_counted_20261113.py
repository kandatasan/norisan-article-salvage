"""Copy published Gulliver A8 creative to native counted SWELL buttons, article by article.

Does not alter article prose, photos, tables, headings, CTN buttons or global parts.
Each new Gutenberg loos/button has isCount=true and a unique data-id, as declared
by the live WordPress block schema. A8 href and impression-pixel URLs are copied.
"""
from __future__ import annotations
import hashlib,html,json,re
from pathlib import Path

A8="4B65SD+8DUSHE+9QU+NVHCY"
URL="https://px.a8.net/svt/ejp?a8mat="+A8
OLD_SC=re.compile(r'<!-- wp:shortcode -->\s*\[blog_parts id="(?P<part>2843|4172|4507)"\]\s*<!-- /wp:shortcode -->',re.S)
TOP=re.compile(r'<!-- wp:html -->\s*<div class="tsq-gulliver-micro-20261014 top"[\s\S]*?</div>\s*<!-- /wp:html -->')
BOTTOM=re.compile(r'<!-- wp:html -->\s*<div class="tsq-gulliver-micro-20261014 bottom"[\s\S]*?</div>\s*<!-- /wp:html -->')
PAR=re.compile(r'<!-- wp:paragraph(?: \{[^\n]*\})? -->[\s\S]*?<!-- /wp:paragraph -->')
BTN=re.compile(r'<!-- wp:loos/button(?: (\{[^\n]*\}))? -->[\s\S]*?<!-- /wp:loos/button -->')
DIRECT=re.compile(r'<p(?: [^>]*)?>\s*(?P<a><[aA]\s+[^>]*href=["\x27]https://px\.a8\.net/svt/ejp\?a8mat=4B65SD\+8DUSHE\+9QU\+NVHCY["\x27][^>]*>[\s\S]*?</[aA]>)\s*(?P<img><img\s+[^>]*a8mat=4B65SD\+8DUSHE\+9QU\+NVHCY[^>]*>)\s*</p>',re.S)
BASELINES={
4268:'c004395b54e90134a66313ee11dc8683a04fef620f56d87033574b0fbced41cf',
4264:'a05f33b798d6fade8bbc9122fc8e9943db844093050b087c91993f92184b6c15',
4261:'1dc54cb8896799db9e43d7a7c3533f5c13d79e83c83691812a2e2087a995d0f9',
4256:'6b41dc5564f18d561c1fc2d7fefaf039f43a3a8ae74ad46fbfb4513fea89736f',
2517:'96fbdd25a4e7a71d85fd797971c5a6c1b9789c63f7db8b2f5d742d19c7d629da',
4004:'95f6072cf37f608945076969c05661762956e16ae55f48928f333b0699387ada',
3965:'8fa1b762df13d51702b58f88a7a96e927940601ac8491eda3252bb59b9bb1d27',
3973:'30e0b6482160c6ac3e8fbc84055e59622e7818818aa2c2177724069329017b4e',
3945:'5ff98f9deab57da362d2651992e051fb08a3cf28b43ac7e1da98dfbc0f03c92d',
3863:'6102dfeb2b64ab6048e6995b20ad30fe83544b3ed398baf148bbf7c31b83d177',
3611:'34db9a055eab9b60f56cc2ed2392e3b85933b830682c51f900a9d45aa0fd4429',
3608:'ed0541578169f1cd2110bd28940d6e711c74ebce2d9e6b4f97fcb2198395a5f6',
3606:'80176d2be21bfa87f8ebfa37115d529f4018cf92085c295d4ab59c37cce8b42e',
3604:'d47ce097f2338442361c15c1c5b1653bfc63e3ba15de7d6e260ba9ed6cb97bf2',
3601:'395060275e726cbdefe40c09fed2b39211f57118662eecf5091a242176baafba',
3570:'43ce10f7141b8d6efd8a04a2fc1acb73fc78e4e67e9f5bf97a088933adadd1bf',
2956:'f1e4b263c531e1fee5007516014c118f0f655c05011f632e5ff7afd80dfb33f2',
2329:'1738205e4d851bfde9c51ad174aa0f48227499f627a3b69cbab573e348a67eca',
3835:'f4c14d52f3d0a9f7aa9db0b35eb48eedd18dd700522c7804e503c3197974e0cf',
}

def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def plain(s):return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',s))).strip()
def label(slug):
    if slug.startswith('tanto-'):return 'ガリバーで希望のタントを探してみる'
    if slug in ('lexus-ux-vs-lbx','lexus-ux-vs-nx','lexus-lbx-regret'):return 'ガリバーで中古のレクサスを探してみる'
    if 'rival' in slug:return 'ガリバーで中古SUVを探してみる' if 'tanto' not in slug else 'ガリバーで中古の軽自動車を探してみる'
    if 'lbx' in slug:return 'ガリバーで希望のLBXを探してみる'
    if 'nx' in slug:return 'ガリバーで希望のNXを探してみる'
    if 'ux' in slug:return 'ガリバーで希望のUXを探してみる'
    return 'ガリバーで希望の中古車を探してみる'

def copy_button(template,identifier,link_label=None):
    m=BTN.fullmatch(template.strip())
    if not m:raise RuntimeError('Published 4507 has invalid button block')
    attrs=json.loads(m.group(1) or '{}')
    attrs['isCount']=True
    attrs.pop('btnId',None)
    first='<!-- wp:loos/button '+json.dumps(attrs,ensure_ascii=False,separators=(',',':'))+' -->'
    old=m.group(0);rest=old[old.index('-->')+3:]
    div=re.search(r'<div class="swell-block-button[^"]*"',rest)
    if not div or 'data-id=' in rest:raise RuntimeError('Gulliver source button div or data-id invalid')
    rest=rest[:div.end()]+' data-id="'+identifier+'"'+rest[div.end():]
    if link_label:
        a=re.search(r'(<[aA]\s+[^>]*>)([\s\S]*?)(</[aA]>)',rest)
        if not a or A8 not in a.group(1):raise RuntimeError('Not a Gulliver A8 creative')
        rest=rest[:a.start(2)]+html.escape(link_label)+rest[a.end(2):]
    if rest.count(URL)!=1 or rest.count(A8)<2:raise RuntimeError('A8 tracking URL or 1px pixel lost')
    return first+rest

def convert_direct(block,ident,template):
    middle=re.search(r'-->([\s\S]*?)<!-- /wp:paragraph -->',block)
    if not middle:raise RuntimeError('Malformed direct A8 paragraph')
    matched=DIRECT.fullmatch(middle.group(1).strip())
    if not matched:raise RuntimeError('Direct A8 paragraph has extra content')
    cloned=copy_button(template,ident)
    ad=re.search(r'<[aA]\s+[^>]*>[\s\S]*?</[aA]>\s*<img\b[^>]*>',cloned)
    if not ad:raise RuntimeError('Cannot locate new source A8 tag')
    code=matched.group('a')+'\n'+matched.group('img')
    cloned=cloned[:ad.start()]+code+cloned[ad.end():]
    if code not in cloned:raise RuntimeError('Original A8 free-text ad was modified')
    return cloned

def microparagraph(s,bold=False,small=False):
    attrs={'style':{'typography':{'textAlign':'center'}}}
    if small:attrs['fontSize']='small'
    css='has-text-align-center'+(' has-small-font-size' if small else '')
    txt=html.escape(plain(s))
    if bold:txt='<strong>'+txt+'</strong>'
    return ('<!-- wp:paragraph '+json.dumps(attrs,ensure_ascii=False,separators=(',',':'))+' -->\n'
            '<p class="'+css+'">'+txt+'</p>\n<!-- /wp:paragraph -->')

def transformed(pid,slug,source,source_button,source_funnel):
    spans=[]
    def overlap(a,b):return any(a<d and b>c for c,d,_,_ in spans)
    def add(a,b,new,reason):
        if overlap(a,b):raise RuntimeError('Overlapping CTA span on '+str(pid))
        spans.append((a,b,new,reason))
    def next_after(pos,pattern):
        q=pos+len(source[pos:])-len(source[pos:].lstrip())
        return pattern.match(source,q)
    # Triplets with Oct 14 wrappers are replaced as one native Gutenberg unit.
    for top in TOP.finditer(source):
        mid=next_after(top.end(),OLD_SC)
        if mid is None:
            mid=next_after(top.end(),PAR)
            if mid:
                h=re.search(r'-->([\s\S]*?)<!-- /wp:paragraph -->',mid.group(0))
                if not h or not DIRECT.fullmatch(h.group(1).strip()):mid=None
        if mid is None:continue
        bottom=next_after(mid.end(),BOTTOM)
        if bottom is None:continue
        ident='gu'+str(pid)+'-'+str(len(spans)+1).zfill(2)
        center=(copy_button(source_button,ident,label(slug))
                if OLD_SC.fullmatch(mid.group(0)) else convert_direct(mid.group(0),ident,source_button))
        new=microparagraph(top.group(0),True)+'\n\n'+center+'\n\n'+microparagraph(bottom.group(0),small=True)
        add(top.start(),bottom.end(),new,'old-micro-new-Gutenberg')
    # Any remaining old banner, button or unmeasurable new 4507 shortcode.
    for m in OLD_SC.finditer(source):
        if overlap(m.start(),m.end()):continue
        ident='gu'+str(pid)+'-'+str(len(spans)+1).zfill(2)
        if m.group('part')=='4507':
            buttons=list(BTN.finditer(source_funnel))
            if len(buttons)!=1:raise RuntimeError('Funnel source button count is not one')
            cloned=copy_button(buttons[0].group(0),ident,label(slug))
            new=source_funnel[:buttons[0].start()]+cloned+source_funnel[buttons[0].end():]
            reason='copy-4507-inline-tracked'
        else:
            new=copy_button(source_button,ident,label(slug))
            reason='replace-blog-parts-'+m.group('part')
        add(m.start(),m.end(),new,reason)
    # Older inline plain A8 links; retain exact linked copy + 1px GIF.
    for m in PAR.finditer(source):
        if overlap(m.start(),m.end()) or URL not in m.group(0):continue
        inner=re.search(r'-->([\s\S]*?)<!-- /wp:paragraph -->',m.group(0))
        if inner and DIRECT.fullmatch(inner.group(1).strip()):
            ident='gu'+str(pid)+'-'+str(len(spans)+1).zfill(2)
            add(m.start(),m.end(),convert_direct(m.group(0),ident,source_button),'old-inline-link-tracked')
    # Existing direct SWELL native buttons (not counted yet).
    for m in BTN.finditer(source):
        if overlap(m.start(),m.end()) or URL not in m.group(0):continue
        if '"isCount":true' in m.group(0) and 'data-id=' in m.group(0):continue
        attrs=json.loads(m.group(1) or '{}')
        attrs.pop('btnId',None);attrs['isCount']=True
        b=m.group(0);new='<!-- wp:loos/button '+json.dumps(attrs,ensure_ascii=False,separators=(',',':'))+' -->'+b[b.index('-->')+3:]
        div=re.search(r'<div class="swell-block-button[^"]*"',new)
        if not div or 'data-id=' in new:raise RuntimeError('Existing SWELL counted ID conflict')
        ident='gu'+str(pid)+'-'+str(len(spans)+1).zfill(2)
        new=new[:div.end()]+' data-id="'+ident+'"'+new[div.end():]
        add(m.start(),m.end(),new,'existing-native-enable-count')

    original_replaced=''.join(source[a:b] for a,b,_,_ in spans)
    for token in ('[blog_parts id="2843"]','[blog_parts id="4172"]','[blog_parts id="4507"]','tsq-gulliver-micro-20261014'):
        if source.count(token)!=original_replaced.count(token):
            raise RuntimeError('Unconverted legacy Gulliver '+token+' on '+str(pid))
    if len(spans)>12:raise RuntimeError('Unexpected excessive ad count '+str(pid))
    if not spans:
        # Old articles with already native, already counted buttons need no rewrite.
        if URL in source:
            native=''.join(m.group(0) for m in BTN.finditer(source))
            plain=''.join(m.group(0) for m in PAR.finditer(source))
            if source.count(URL)!=native.count(URL):
                raise RuntimeError('Untracked Gulliver URL remains in post '+str(pid))
            if native.count('"isCount":true')<native.count(URL):
                raise RuntimeError('Existing native Gulliver tracking is disabled')
        return source,[]
    spans.sort(key=lambda x:x[0])
    if any(spans[i][1]>spans[i+1][0] for i in range(len(spans)-1)):
        raise RuntimeError('Overlapping Gutenberg transforms')
    result='';pos=0
    for a,b,new,reason in spans:
        result+=source[pos:a]+new;pos=b
    result+=source[pos:]
    for k in ('<!-- wp:image','<!-- wp:table','<!-- wp:heading','<!-- wp:list','[blog_parts id="4521"]'):
        if result.count(k)!=source.count(k):raise RuntimeError('Protected blog content changed '+k)
    for k in ('[blog_parts id="2843"]','[blog_parts id="4172"]','[blog_parts id="4507"]','tsq-gulliver-micro-20261014'):
        if k in result:raise RuntimeError('Old Gulliver placement remains '+k)
    counted=[m.group(0) for m in BTN.finditer(result) if URL in m.group(0)]
    if len(counted)<len(spans):raise RuntimeError('New counted buttons missing')
    if any('"isCount":true' not in b or 'data-id=' not in b for b in counted):
        raise RuntimeError('A Gulliver button was not configured for SWELL analytics')
    ids=re.findall(r'data-id="([^"]+)"',result)
    if len(ids)!=len(set(ids)):raise RuntimeError('Duplicate SWELL click count IDs')
    return result,[dict(kind=k,old_bytes=b-a,new_bytes=len(n)) for a,b,n,k in spans]

def run(cfg,auth,api,dry_run=False):
    if cfg.get('operation')!='migrate_all_gulliver_native_counted_20261113':
        raise RuntimeError('Unexpected migration operation')
    get_json,post_json,public_counts,site_url=api
    part,_=get_json(site_url+'/wp-json/wp/v2/blog_parts/4507?context=edit&_fields=id,status,content',auth)
    if part.get('id')!=4507 or part.get('status')!='publish':
        raise RuntimeError('Published Gulliver master creative 4507 unavailable')
    source_funnel=part['content']['raw']
    buttons=list(BTN.finditer(source_funnel))
    if len(buttons)!=1 or buttons[0].group(0).count(URL)!=1 or buttons[0].group(0).count(A8)<2:
        raise RuntimeError('The approved 4507 A8 redirect and tracking pixel changed')
    source_button=buttons[0].group(0)
    block,_=get_json(site_url+'/wp-json/wp/v2/block-types/loos/button?context=edit',auth)
    attrs=block.get('attributes') or {}
    if attrs.get('isCount',{}).get('type')!='boolean' or attrs.get('btnId',{}).get('attribute')!='data-id':
        raise RuntimeError('Unexpected SWELL counting attributes')
    posts=[]
    for page in range(1,4):
        rows,_=get_json(site_url+f'/wp-json/wp/v2/posts?context=edit&status=publish&per_page=100&page={page}'
                        '&_fields=id,slug,status,title,content,featured_media,categories,author',auth)
        posts+=rows
        if len(rows)<100:break
    if len(posts)<100:raise RuntimeError('Incomplete WordPress published inventory')
    proposed=[]
    for post in posts:
        body=post['content']['raw']
        if not any(k in body for k in ('[blog_parts id="2843"]','[blog_parts id="4172"]',
                '[blog_parts id="4507"]','tsq-gulliver-micro-20261014',URL)):continue
        if post['id'] in BASELINES and digest(body)!=BASELINES[post['id']]:
            # Allow post that was already converted by a previous successful run.
            if '[blog_parts id="2843"]' in body or '[blog_parts id="4172"]' in body or 'tsq-gulliver-micro-20261014' in body:
                raise RuntimeError('Article source changed since audited baseline: '+str(post['id']))
        revised,spans=transformed(post['id'],post['slug'],body,source_button,source_funnel)
        if revised!=body:proposed.append((post,body,revised,spans))
    for post,body,revised,spans in proposed:
        report={'id':post['id'],'slug':post['slug'],'before_sha':digest(body),'after_sha':digest(revised),
                'placements':len(spans),'types':[x['kind'] for x in spans]}
        print('GULLIVER_PREFLIGHT_POST',json.dumps(report,ensure_ascii=False),flush=True)
    summary={'posts_examined':len(posts),'posts_to_modify':len(proposed),
             'buttons_to_migrate':sum(len(x[3]) for x in proposed)}
    print('GULLIVER_PREFLIGHT_SUMMARY',json.dumps(summary,ensure_ascii=False),flush=True)
    if dry_run:return summary
    count_before=public_counts(auth)
    result=[]
    for post,body,revised,spans in proposed:
        pid=post['id']
        fresh,_=get_json(site_url+f'/wp-json/wp/v2/posts/{pid}?context=edit&_fields=id,slug,status,title,content,featured_media,categories,author',auth)
        for k in ('id','slug','status','title','featured_media','categories','author'):
            if fresh[k]!=post[k]:raise RuntimeError(f'Post {pid} metadata edited concurrently')
        if fresh['content']['raw']!=body:raise RuntimeError(f'Post {pid} body edited concurrently')
        saved=post_json(site_url+f'/wp-json/wp/v2/posts/{pid}',auth,{'content':revised})
        if saved['id']!=pid or saved['status']!='publish':
            raise RuntimeError('WordPress unexpectedly changed publication status')
        verify,_=get_json(site_url+f'/wp-json/wp/v2/posts/{pid}?context=edit&_fields=id,slug,status,title,content,featured_media,categories,author',auth)
        if verify['content']['raw']!=revised:raise RuntimeError(f'Saved body failed exact check {pid}')
        for k in ('id','slug','status','title','featured_media','categories','author'):
            if verify[k]!=post[k]:raise RuntimeError('Metadata changed after publishing CTA')
        if 'data-id="gu'+str(pid)+'-' not in verify['content'].get('rendered',''):
            raise RuntimeError(f'Counted SWELL button not visible in rendered article {pid}')
        item={'id':pid,'slug':post['slug'],'old_sha':digest(body),'new_sha':digest(revised),
              'native_counted_buttons_added':len(spans)}
        result.append(item)
        print('GULLIVER_UPDATED',json.dumps(item,ensure_ascii=False),flush=True)
    count_after=public_counts(auth)
    if count_after!=count_before:raise RuntimeError('Site published count changed unexpectedly')
    outcome={'articles_updated':len(result),'buttons_migrated':sum(i['native_counted_buttons_added'] for i in result),
             'results':result,'before_counts':count_before,'after_counts':count_after}
    dest=Path('reports/gulliver-counted-migration-20261113');dest.mkdir(parents=True,exist_ok=True)
    (dest/'result.json').write_text(json.dumps(outcome,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('GULLIVER_MIGRATION_RESULT',json.dumps(outcome,ensure_ascii=False),flush=True)
    return outcome
