#!/usr/bin/env python3
import base64, hashlib, html, json, os, pathlib, re, time, urllib.error, urllib.request

BASE='https://tsurikue.com/wp-json/wp/v2'
PAGE_ID=3316
SLUG='fishing-guide'
TITLE='釣り｜初心者向けの釣り方・実釣レビュー・釣行記'
STATUS='draft'
OLD_SHA='7d92830783c476fa40457d04be629ca54458f30eb06dfb03180bce933479be64'
MARKER='tsurikue-category-hub:v4:fishing-accordion'
SCRIPT_MARKER='tq-fishing-auto-index:v4'
HERO_URL='https://tsurikue.com/wp-content/uploads/2026/06/IMG_9050-768x1024.jpeg'
ROOT=pathlib.Path(__file__).resolve().parent
USER=os.environ['TSURIKUE_WP_USER']
APP=os.environ['TSURIKUE_WP_APP_PASSWORD']
AUTH='Basic '+base64.b64encode(f'{USER}:{APP}'.encode()).decode()
writes=0


def req(path, method='GET', data=None, timeout=45, retries=4):
    global writes
    headers={'Authorization':AUTH,'User-Agent':'tsurikue-fishing-hub-v4/1.0'}
    body=None
    if data is not None:
        body=json.dumps(data,ensure_ascii=False).encode('utf-8')
        headers['Content-Type']='application/json; charset=utf-8'
    last=None
    for i in range(retries):
        try:
            r=urllib.request.Request(BASE+path,data=body,headers=headers,method=method)
            with urllib.request.urlopen(r,timeout=timeout) as res:
                raw=res.read(); total=res.headers.get('X-WP-Total')
                if method not in ('GET','HEAD'): writes+=1
                return json.loads(raw.decode('utf-8')), total
        except (urllib.error.URLError, TimeoutError) as e:
            last=e
            if i+1==retries: raise
            time.sleep(2*(i+1))
    raise last


def count_public():
    _,p=req('/posts?status=publish&per_page=1&_fields=id')
    _,q=req('/pages?status=publish&per_page=1&_fields=id')
    return {'posts':int(p or 0),'pages':int(q or 0)}


def get_page():
    p,_=req(f'/pages/{PAGE_ID}?context=edit&_fields=id,slug,status,title,content,link,modified')
    return p


def clean_title(v):
    if isinstance(v,dict): v=v.get('rendered','')
    v=re.sub(r'<[^>]+>','',v or '')
    return html.unescape(v).strip()


def tag_text(tag):
    return ((tag.get('name','')+' '+tag.get('slug','')).lower()).strip()


def classify(post, tagmap):
    tags=' '.join(tag_text(tagmap[i]) for i in post.get('tags',[]) if i in tagmap)
    if re.search(r'実験|experiment|(^|\s)lab(\s|$)',tags,re.I): return 'experiment'
    if re.search(r'釣り日記|釣行記|fishing.?diary|(^|\s)diary(\s|$)',tags,re.I): return 'diary'
    if re.search(r'釣り方|初心者|how.?to|beginner',tags,re.I): return 'howto'
    title=clean_title(post.get('title'))
    if re.search(r'実験|試して|試した|釣れる[？?]|効果は[？?]|激安|裏技|GoPro|GOPRO|ガルプ|小麦粉|羽で|粉',title): return 'experiment'
    if re.search(r'釣り方|初心者|ガイド|初めて|初フライ|仕掛け|コツ',title): return 'howto'
    if re.search(r'釣行記|体験記|釣り日記|釣行|爆釣',title): return 'diary'
    if re.search(r'レビュー|インプレ',title): return 'howto'
    return 'howto'


def method_label(title):
    if 'サビキ' in title: return 'サビキ'
    if 'ヤリイカ' in title: return 'ヤリイカ'
    if 'アオリイカ' in title or 'エギング' in title: return 'アオリイカ'
    if 'サヨリ' in title: return 'サヨリ'
    if 'ナマズ' in title: return 'ナマズ'
    if 'フライ' in title or '管理釣り場' in title: return 'フライ'
    if 'ルアー' in title or 'ワーム' in title: return 'ルアー'
    return '釣り方'


def li(post, kind):
    title=clean_title(post.get('title'))
    url=html.escape(post.get('link',''),quote=True)
    text=html.escape(title)
    badge=''
    if kind=='howto': badge=f'<span class="tq-method">{html.escape(method_label(title))}</span>'
    return f'<li>{badge}<a href="{url}">{text}</a></li>'


def build_desired():
    cats,_=req('/categories?per_page=100&hide_empty=false&_fields=id,name,slug,parent,count')
    wild=[c for c in cats if c.get('id')==5 and c.get('parent')==1 and c.get('slug')=='wild-food-fish-cooking']
    if len(wild)!=1: raise RuntimeError('WILD_FOOD_CATEGORY_IDENTITY_FAILED '+json.dumps(wild,ensure_ascii=False))
    tags,_=req('/tags?per_page=100&hide_empty=false&_fields=id,name,slug,count')
    posts,_=req('/posts?categories=1&status=publish&per_page=100&orderby=date&order=desc&_fields=id,slug,link,title,tags,date')
    wild_posts,_=req('/posts?categories=5&status=publish&per_page=100&orderby=date&order=desc&_fields=id,slug,link,title,date')
    tagmap={t['id']:t for t in tags}
    groups={'howto':[],'experiment':[],'diary':[]}
    for p in posts: groups[classify(p,tagmap)].append(p)
    if len(posts)<10 or len(wild_posts)<1: raise RuntimeError('FISHING_SOURCE_TOO_SMALL')
    if not all(groups[k] for k in groups): raise RuntimeError('EMPTY_AUTO_GROUP '+json.dumps({k:len(v) for k,v in groups.items()}))
    tpl=(ROOT/'content.template.html').read_text(encoding='utf-8')
    repl={
        '{{HOWTO_COUNT}}':str(len(groups['howto'])),
        '{{EXPERIMENT_COUNT}}':str(len(groups['experiment'])),
        '{{DIARY_COUNT}}':str(len(groups['diary'])),
        '{{WILD_COUNT}}':str(len(wild_posts)),
        '{{HOWTO_ITEMS}}':'\n'.join(li(p,'howto') for p in groups['howto']),
        '{{EXPERIMENT_ITEMS}}':'\n'.join(li(p,'experiment') for p in groups['experiment']),
        '{{DIARY_ITEMS}}':'\n'.join(li(p,'diary') for p in groups['diary']),
        '{{WILD_ITEMS}}':'\n'.join(li(p,'wild') for p in wild_posts),
    }
    for a,b in repl.items(): tpl=tpl.replace(a,b)
    if '{{' in tpl or '}}' in tpl: raise RuntimeError('UNRESOLVED_TEMPLATE_PLACEHOLDER')
    return tpl, {'fishing_posts':len(posts),'wild_posts':len(wild_posts),'groups':{k:len(v) for k,v in groups.items()},'tag_count':len(tags)}


def checks(raw, rendered):
    return {
        'marker_once':raw.count(MARKER)==1,
        'single_custom_html':raw.count('<!-- wp:html -->')==1,
        'four_details':raw.count('<!-- wp:details ')==4,
        'script_raw':SCRIPT_MARKER in raw and '<script>' in raw,
        'script_rendered':SCRIPT_MARKER in rendered and '<script>' in rendered,
        'hero':HERO_URL in raw and '今日は、なに釣る？' in raw,
        'accordion_labels':all(x in raw for x in ['はじめての釣り・釣り方','>実験 <','>釣り日記 <','>とったら食べる！ <']),
        'positive_copy':'自分でとったら、うまさは別格。' in raw,
        'wild_category_fetch':'categories=5' in raw,
        'fishing_category_fetch':'categories=1' in raw,
        'swell_post_list':'<!-- wp:loos/post-list' in raw and '"catID":"1"' in raw and '"listCount":6' in raw,
        'archive_link':'https://tsurikue.com/category/fishing/' in raw,
        'fallback_howto':'/sabiki-beginner/' in raw,
        'fallback_experiment':'/gulpalivepowder/' in raw,
        'fallback_diary':'/aoriika-nikki/' in raw,
        'old_layout_absent':all(x not in raw for x in ['まず読む3本。','ちょっと試したくなった。','今日は、どこから見る？']),
        'no_emoji':not bool(re.search('[\U0001F300-\U0001FAFF]',raw)),
    }


before=count_public()
page=get_page()
if page['id']!=PAGE_ID or page['slug']!=SLUG or page['status']!=STATUS or page['title']['raw']!=TITLE:
    raise RuntimeError('PAGE_IDENTITY_MISMATCH '+json.dumps({'id':page.get('id'),'slug':page.get('slug'),'status':page.get('status'),'title':page.get('title',{}).get('raw')},ensure_ascii=False))
current=page['content']['raw']
current_sha=hashlib.sha256(current.encode()).hexdigest()

if MARKER in current:
    final_checks=checks(current,page['content']['rendered'])
    if not all(final_checks.values()): raise RuntimeError('V4_VERIFY_FAILED '+json.dumps(final_checks,ensure_ascii=False))
    after=count_public()
    if before!=after: raise RuntimeError('PUBLIC_COUNTS_CHANGED')
    print(json.dumps({'action':'VERIFIED_EXISTING_FISHING_V4','page_id':PAGE_ID,'slug':SLUG,'status':STATUS,'wordpress_write_count':0,'public_before':before,'public_after':after,'checks':final_checks,'content_sha256':current_sha},ensure_ascii=False))
    raise SystemExit

if current_sha!=OLD_SHA:
    raise RuntimeError('STALE_DRAFT_REFUSED '+json.dumps({'expected':OLD_SHA,'actual':current_sha},ensure_ascii=False))

desired,source=build_desired()
pre=checks(desired,desired)
if not all(pre.values()): raise RuntimeError('DESIRED_STRUCTURE_FAILED '+json.dumps(pre,ensure_ascii=False))

req(f'/pages/{PAGE_ID}',method='POST',data={'content':desired,'status':'draft'})
final=get_page(); saved=final['content']['raw']; rendered=final['content']['rendered']
final_checks=checks(saved,rendered)
if not all(final_checks.values()):
    # Restore the exact previous draft if WordPress strips the live auto-index script or breaks structure.
    req(f'/pages/{PAGE_ID}',method='POST',data={'content':current,'status':'draft'})
    raise RuntimeError('FINAL_STRUCTURE_FAILED_ROLLED_BACK '+json.dumps(final_checks,ensure_ascii=False))
if final['status']!='draft' or final['slug']!=SLUG: raise RuntimeError('FINAL_IDENTITY_FAILED')
after=count_public()
if before!=after: raise RuntimeError('PUBLIC_COUNTS_CHANGED '+json.dumps({'before':before,'after':after}))

print(json.dumps({
    'action':'UPDATED_FISHING_CATEGORY_HUB_V4','page_id':PAGE_ID,'slug':SLUG,'status':final['status'],
    'wordpress_write_count':writes,'publish_count':0,'delete_count':0,
    'public_before':before,'public_after':after,'source':source,'checks':final_checks,
    'old_content_sha256':current_sha,'final_content_sha256':hashlib.sha256(saved.encode()).hexdigest(),
    'block_counts':{'html':saved.count('<!-- wp:html -->'),'details':saved.count('<!-- wp:details '),'heading':saved.count('<!-- wp:heading'),'paragraph':saved.count('<!-- wp:paragraph'),'list':saved.count('<!-- wp:list '),'swell_post_list':saved.count('<!-- wp:loos/post-list')}
},ensure_ascii=False))