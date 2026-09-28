#!/usr/bin/env python3
from __future__ import annotations
import base64, html, json, os, re, time, urllib.parse, urllib.request

SITE='https://tsurikue.com'
UA='tsurikue-update-lbx-links-20260928/1.0'
SLUGS=[
 'lexus-lbx-price','lexus-lbx-interior','lexus-lbx-options',
 'lexus-lbx-cheap','lexus-lbx-regret','lexus-ux-vs-lbx'
]
EDIT_SLUGS=['lexus-lbx-interior','lexus-lbx-options','lexus-lbx-cheap','lexus-lbx-regret','lexus-ux-vs-lbx']
SHORTCODE_RE=re.compile(r'\[blog_parts\s+id=["\']?(\d+)["\']?\]',re.I)
TOKEN=re.compile(r'<!--\s+/?wp:[\s\S]*?-->')
OPEN=re.compile(r'<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->')
CLOSE=re.compile(r'<!--\s+/wp:([\w\-/]+)\s+-->')

def auth():
    u=os.environ.get('TSURIKUE_WP_USER'); p=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
    if not u or not p: raise SystemExit('BLOCKED_MISSING_SECRETS')
    return 'Basic '+base64.b64encode(f'{u}:{p}'.encode()).decode()

def req(url,method='GET',payload=None,timeout=60):
    headers={'Authorization':auth(),'Accept':'application/json','User-Agent':UA}; data=None
    if payload is not None:
        data=json.dumps(payload,ensure_ascii=False).encode(); headers['Content-Type']='application/json; charset=utf-8'
    last=None
    for n in range(3):
        try:
            r=urllib.request.Request(url,data=data,headers=headers,method=method)
            with urllib.request.urlopen(r,timeout=timeout) as resp:
                return json.loads(resp.read().decode()),dict(resp.headers)
        except Exception as e:
            last=e
            if n<2: time.sleep(3*(n+1))
    raise last

def raw(row,key):
    v=row.get(key) or {}
    return (v.get('raw') or v.get('rendered') or '') if isinstance(v,dict) else str(v)

def get_slug(slug):
    q=urllib.parse.urlencode({'context':'edit','slug':slug,'status':'any','per_page':10,'_fields':'id,slug,status,title,content,featured_media,categories,tags'})
    rows,_=req(f'{SITE}/wp-json/wp/v2/posts?{q}',timeout=60)
    if len(rows)!=1: raise RuntimeError(f'{slug}: expected exactly one post, got {len(rows)}')
    return rows[0]

def published_count():
    q=urllib.parse.urlencode({'status':'publish','per_page':1,'_fields':'id'})
    _,h=req(f'{SITE}/wp-json/wp/v2/posts?{q}',timeout=45)
    return int(h.get('X-WP-Total','0'))

def gutenberg_problems(text):
    stack=[]
    for m in TOKEN.finditer(text):
        t=m.group(0); o=OPEN.fullmatch(t); c=CLOSE.fullmatch(t)
        if o:
            if not o.group(2): stack.append(o.group(1))
        elif c:
            if not stack or stack[-1]!=c.group(1): return 1
            stack.pop()
    return len(stack)

def replace_once(text,old,new,label):
    n=text.count(old)
    if n!=1: raise RuntimeError(f'{label}: expected anchor once, got {n}')
    return text.replace(old,new,1)

def replace_related_block(text,slug,new_block):
    start=f'<!-- tq-lexus-related-cards:v1:{slug} -->'
    end='<!-- tq-lexus-related-cards:v1:end -->'
    i=text.find(start)
    if i<0: raise RuntimeError(f'{slug}: related-card start marker missing')
    j=text.find(end,i)
    if j<0: raise RuntimeError(f'{slug}: related-card end marker missing')
    j += len(end)
    if text.find(start,i+1)>=0: raise RuntimeError(f'{slug}: duplicate related-card start marker')
    return text[:i]+new_block+text[j:]

def card_block(slug,targets):
    bits=[f'<!-- tq-lexus-related-cards:v1:{slug} -->',
          '<!-- wp:heading {"level":3} -->',
          '<h3 class="wp-block-heading">次に読みたいレクサス記事</h3>',
          '<!-- /wp:heading -->','']
    for url in targets:
        bits += [
          f'<!-- wp:embed {{"url":"https://tsurikue.com/{url}/"}} -->',
          '<figure class="wp-block-embed"><div class="wp-block-embed__wrapper">',
          f'https://tsurikue.com/{url}/',
          '</div></figure>',
          '<!-- /wp:embed -->',''
        ]
    bits += ['<!-- tq-lexus-related-cards:v1:end -->']
    return '\n'.join(bits)

def transform(slug,text):
    if slug=='lexus-lbx-interior':
        if 'https://tsurikue.com/lexus-lbx-price/' in text: return text
        anchor='''<!-- wp:paragraph -->
<p>価格だけならElegantやActiveもありますが、私が選ぶなら<strong>Relax</strong>です。</p>
<!-- /wp:paragraph -->'''
        addition=anchor+'''

<!-- wp:paragraph -->
<p>各パッケージの2WD・AWD価格と、私ならいくらを予算の基準にするかは<a href="https://tsurikue.com/lexus-lbx-price/">レクサスLBXの価格記事</a>にまとめています。</p>
<!-- /wp:paragraph -->'''
        return replace_once(text,anchor,addition,slug+' price link')
    if slug=='lexus-lbx-cheap':
        if 'https://tsurikue.com/lexus-lbx-price/' in text: return text
        anchor='''<!-- wp:paragraph -->
<p>LBXはElegantが420万円、Activeが440万円、RelaxとCoolが460万円です。</p>
<!-- /wp:paragraph -->'''
        addition=anchor+'''

<!-- wp:paragraph -->
<p>現行LBXの2WD・AWDを含む価格一覧は<a href="https://tsurikue.com/lexus-lbx-price/">LBXの価格記事</a>でまとめています。</p>
<!-- /wp:paragraph -->'''
        return replace_once(text,anchor,addition,slug+' price link')
    if slug=='lexus-lbx-options':
        return replace_related_block(text,slug,card_block(slug,['lexus-lbx-price','lexus-lbx-interior','lexus-lbx-cheap']))
    if slug=='lexus-lbx-regret':
        return replace_related_block(text,slug,card_block(slug,['lexus-lbx-price','lexus-lbx-interior','lexus-ux-vs-lbx']))
    if slug=='lexus-ux-vs-lbx':
        return replace_related_block(text,slug,card_block(slug,['lexus-lbx-regret','lexus-lbx-price','lexus-ux-used']))
    raise RuntimeError('unexpected slug '+slug)

def main():
    rows={s:get_slug(s) for s in SLUGS}
    before_pub=published_count()
    original={}
    updated={}

    # Fail closed: validate all current posts and all transformations before any write.
    for s,r in rows.items():
        if r.get('status')!='publish': raise RuntimeError(f'{s}: expected publish, got {r.get("status")}')
        c=raw(r,'content')
        if gutenberg_problems(c)!=0: raise RuntimeError(f'{s}: existing Gutenberg imbalance')
        original[s]={
          'id':r['id'],'title':html.unescape(raw(r,'title')),'slug':r['slug'],'status':r['status'],
          'featured_media':int(r.get('featured_media') or 0),
          'categories':list(r.get('categories') or []),'tags':list(r.get('tags') or []),
          'affiliate':SHORTCODE_RE.findall(c),'content':c
        }
    for s in EDIT_SLUGS:
        c2=transform(s,original[s]['content'])
        if c2==original[s]['content']: raise RuntimeError(f'{s}: transformation made no change')
        if gutenberg_problems(c2)!=0: raise RuntimeError(f'{s}: transformed Gutenberg imbalance')
        if SHORTCODE_RE.findall(c2)!=original[s]['affiliate']: raise RuntimeError(f'{s}: affiliate blocks would change')
        updated[s]=c2

    # Ensure target routing before writes.
    must={
      'lexus-lbx-interior':['lexus-lbx-price'],
      'lexus-lbx-options':['lexus-lbx-price','lexus-lbx-interior','lexus-lbx-cheap'],
      'lexus-lbx-cheap':['lexus-lbx-price','lexus-lbx-options'],
      'lexus-lbx-regret':['lexus-lbx-price','lexus-lbx-interior','lexus-ux-vs-lbx'],
      'lexus-ux-vs-lbx':['lexus-lbx-price','lexus-lbx-regret'],
    }
    for s,targets in must.items():
        c=updated[s]
        for t in targets:
            if f'https://tsurikue.com/{t}/' not in c:
                raise RuntimeError(f'{s}: missing planned target {t}')

    for s in EDIT_SLUGS:
        pid=original[s]['id']
        req(f'{SITE}/wp-json/wp/v2/posts/{pid}',method='POST',payload={'content':updated[s]},timeout=90)

    # Separate GET verification.
    for s in EDIT_SLUGS:
        r=get_slug(s); o=original[s]; c=raw(r,'content')
        assert r['id']==o['id']
        assert r['slug']==o['slug']
        assert r['status']=='publish'
        assert html.unescape(raw(r,'title'))==o['title']
        assert int(r.get('featured_media') or 0)==o['featured_media']
        assert list(r.get('categories') or [])==o['categories']
        assert list(r.get('tags') or [])==o['tags']
        assert SHORTCODE_RE.findall(c)==o['affiliate']
        assert gutenberg_problems(c)==0
        for t in must[s]:
            assert f'https://tsurikue.com/{t}/' in c
    after_pub=published_count()
    assert before_pub==after_pub

    print('# Lexus LBX internal-link update')
    print('- result: **SUCCESS**')
    print(f'- updated_posts: **{len(EDIT_SLUGS)}**')
    print('- unchanged_hub: **lexus-lbx-price**')
    print(f'- published_posts_before: **{before_pub}**')
    print(f'- published_posts_after: **{after_pub}**')
    print('- affiliate_changes: **0**')
    print('- title_slug_status_taxonomy_media_changes: **0**')
    print('- Gutenberg problems: **0**')
    print('- publish_count_change: **0**')
    for s in EDIT_SLUGS:
        print(f'- {s}: **updated + verified**')

if __name__=='__main__': main()
