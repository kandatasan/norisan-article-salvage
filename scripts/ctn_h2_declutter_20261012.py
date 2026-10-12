#!/usr/bin/env python3
"""CTN: reduce repetitive affiliate copy; at most three affiliate-bearing H2 sections.
No A8 URL/creative edits. Exact WordPress SHA guards, no metadata/status changes.
"""
from __future__ import annotations
import base64,hashlib,html,json,os,re,sys,urllib.parse,urllib.request
from pathlib import Path

SITE="https://tsurikue.com"
POSTS={
2222:"ux-resale",2240:"ux-mitsumori",2329:"ux300h",2517:"ux-koukai",
2948:"lexus-ux-used",2956:"lexus-ux-price",2962:"lexus-ux-discount",
3570:"lexus-ux-emotional-explorer",3601:"lexus-ux250h-used-vs-ux300h",
3604:"lexus-ux-vs-nx",3606:"lexus-ux-vs-lbx",3608:"lexus-lbx-regret",
3611:"lexus-lbx-options",3614:"car-sell-high",3835:"goodbuy",3863:"lexus-lbx-cheap",
3936:"lexus-lbx-price",3767:"landcruiser-fj-price",3816:"landcruiser-fj-cheap",
3774:"landcruiser-fj-review",3777:"landcruiser-fj-rear-seat",3778:"landcruiser-fj-drawbacks",
4004:"tanto-model-history"}
# Pinned to WP REST current content raw, collected by read-only audit before release.
EXPECTED={}
REMOVE_FOOTER_BANNER={2222,2240,2329,3570,3601,3604,3606,3608,3611,3614}
PARAGRAPH_DELETE={
2222:[
"次の車を10万円安く買うのも大事です。",
"もっと差が出れば、私の150万円差のように",
"高く売れる会社は探したい。<br>でも何社からも電話が来るのは避けたい。"],
2240:[
"前の車を少しでも高く売れれば、そのぶん次の車を安く買えたのと同じ",
"シエンタでは、ディーラー下取りと一括査定で25万円の差が出ました。",
"CTNは、買取価格の上位3社のみを紹介する仕組みです。"],
2948:[
"私がUXへ乗り換えたとき、前の車はディーラー下取りが50万円、買取サービスでは75万円",
"もちろん、いつでも買取の方が高くなるわけではありません。"],
2956:["「買えるUX」を決める前に、「今の車がいくらになるか」を見ておく。"],
3606:["LBXにするかUXにするか決める前でも、"],
3608:["「LBXにするか、UXにするか」まで決め切れていなくても、"]
}
WP_P=re.compile(r'<!-- wp:paragraph(?:\s+\{[^\n]*\})? -->\s*<p(?:\s[^>]*)?>.*?</p>\s*<!-- /wp:paragraph -->',re.S)
WP_SHORTCODE=lambda n: re.compile(r'<!-- wp:shortcode -->\s*\[blog_parts id="'+str(n)+r'"\]\s*<!-- /wp:shortcode -->',re.S)

def digest(s):return hashlib.sha256(s.encode()).hexdigest()

def drop_para(s, phrase, slug):
    matches=[m for m in WP_P.finditer(s) if phrase in m.group(0)]
    if len(matches)!=1:raise RuntimeError(f'{slug}: expected 1 removable paragraph for {phrase[:25]!r}, got {len(matches)}')
    m=matches[0]
    return s[:m.start()]+s[m.end():]

def replace_once(s, old, new, slug):
    if s.count(old)!=1:raise RuntimeError(f'{slug}: copy anchor count={s.count(old)}: {old[:36]!r}')
    return s.replace(old,new,1)

def ad_sections(s):
    sections=re.split(r'<h2\b[^>]*>.*?</h2>',s,flags=re.S|re.I)
    result=[]
    for i,body in enumerate(sections[1:],1):
        shortcode=re.findall(r'\[blog_parts id="(\d+)"\]',body)
        direct=len(re.findall(r'<a\b[^>]*href=["\'][^"\']*(?:px\.a8\.net|ctn-net\.jp)',body,flags=re.I))
        if shortcode or direct:result.append((i,shortcode,direct))
    return result

def transform(original,pid,slug):
    s=original
    if pid in REMOVE_FOOTER_BANNER:
        p=WP_SHORTCODE(2846);matches=list(p.finditer(s))
        if len(matches)!=1:raise RuntimeError(f'{slug}: expected one duplicate 2846 banner')
        if '[blog_parts id="2184"]' not in s:raise RuntimeError(f'{slug}: primary CTN button missing')
        m=matches[0];s=s[:m.start()]+s[m.end():]
    if pid==3835:
        p=WP_SHORTCODE(2890);matches=list(p.finditer(s))
        if len(matches)!=1:raise RuntimeError('goodbuy: duplicate footer bundle not uniquely located')
        m=matches[0];s=s[:m.start()]+s[m.end():]
    for phrase in PARAGRAPH_DELETE.get(pid,[]):
        s=drop_para(s,phrase,slug)
    if pid==2222:
        s=replace_once(s,
            "現在のCTNは最大15社で査定し、やり取りするのは高額査定の上位3社だけ。利用料・手数料も無料です。<br>「今の車がいくらになる？」を見ておくなら、",
            "CTNなら、やり取りする買取店は最大3社。電話の負担を抑えて比べられます。<br>次の車の予算が気になるなら、",slug)
    if pid==3863:
        s=replace_once(s,"装備を削る前に、今の車の買取額も比較。","売るかどうかは、査定額を見てから。",slug)
    if pid==3601:
        s=replace_once(s,
           "新車300hか中古250hかで迷うときも、今の車の売値まで分かると予算は一気に現実的になります。",
           "その先のローンや保険も含めて考えるなら、",slug)
    if s!=original:
        # Includes no ad URLs or tracking pixel modifications.
        for pattern in (r'https://px\.a8\.net/svt/ejp\?a8mat=[^"\s<]+',
                        r'https://www\d+\.a8\.net/0\.gif\?a8mat=[^"\s<]+',
                        r'<img\b[^>]*>',r'wp-image-\d+',
                        r'<h[123]\b[^>]*>.*?</h[123]>'):
            if re.findall(pattern,s,re.S|re.I)!=re.findall(pattern,original,re.S|re.I):
                raise RuntimeError(f'{slug}: protected HTML/image/affiliate changed: {pattern[:20]}')
        if s.count('<!-- wp:')!=s.count('<!-- /wp:'):
            # Existing articles may contain legacy malformed Gutenberg blocks; compare balance instead.
            if (s.count('<!-- wp:')-s.count('<!-- /wp:'))!=(original.count('<!-- wp:')-original.count('<!-- /wp:')):
                raise RuntimeError(f'{slug}: Gutenberg block imbalance')
        if len(ad_sections(s))>3:raise RuntimeError(f'{slug}: {len(ad_sections(s))} ad H2 sections (>3)')
        if len(ad_sections(s))>len(ad_sections(original)):raise RuntimeError(f'{slug}: added affiliate-bearing H2')
    return s

def http(endpoint,auth,data=None):
    h={'Accept':'application/json','Authorization':auth,'User-Agent':'tsurikue-ctn-cleanup/1.0'}
    if data is not None:h['Content-Type']='application/json; charset=utf-8'
    q=urllib.request.Request(SITE+endpoint,
       data=json.dumps(data,ensure_ascii=False).encode() if data is not None else None,
       method='POST' if data is not None else 'GET',headers=h)
    with urllib.request.urlopen(q,timeout=50) as r:
        return json.loads(r.read().decode()),dict(r.headers)

def get(pid,auth):
    q=urllib.parse.urlencode({'context':'edit','_fields':'id,slug,status,title,content,featured_media,author,categories'})
    return http(f'/wp-json/wp/v2/posts/{pid}?'+q,auth)[0]

def publish_count(auth):
    q=urllib.parse.urlencode({'context':'edit','status':'publish','per_page':1,'_fields':'id'})
    return int(http('/wp-json/wp/v2/posts?'+q,auth)[1]['X-WP-Total'])

def main(mode):
    user=os.getenv('TSURIKUE_WP_USER');password=os.getenv('TSURIKUE_WP_APP_PASSWORD')
    if not user or not password:raise RuntimeError('Missing auth secrets')
    auth='Basic '+base64.b64encode((user+':'+password).encode()).decode()
    before_total=publish_count(auth)
    snapshot=[]
    for pid,slug in POSTS.items():
        row=get(pid,auth)
        if (row['id'],row['slug'],row['status'])!=(pid,slug,'publish'):
            raise RuntimeError(f'{slug}: WordPress ID/slug/status differs, abort')
        old=row['content']['raw']
        try:
            new=transform(old,pid,slug)
        except Exception as e:
            if mode!='audit':raise
            print('DRAFT_BLOCKED',pid,slug,str(e),flush=True)
            for para in WP_P.finditer(old):
                if ('CTN' in para.group(0) or '査定' in para.group(0)) and pid in (2222,2240,2948,2956,3606,3608,3863):
                    print('NEAR',pid,' '.join(re.sub(r'<[^>]*>','',para.group(0)).split())[:330],flush=True)
            new=old
        actual=digest(old)
        before,after=ad_sections(old),ad_sections(new)
        print(f'AUDIT {pid} {slug} SHA={actual} edit={int(new!=old)} H2_ads={len(before)}->{len(after)} parts={old.count("[blog_parts")}->{new.count("[blog_parts")}',flush=True)
        snapshot.append((pid,slug,row,old,new))
    if mode=='audit':
        print('READ_ONLY_23_AUDIT_FINISHED (draft blockers shown above)',flush=True);return
    if len(EXPECTED)!=23:raise RuntimeError('BLOCKED: 23 live content hashes not pinned')
    for pid,slug,row,old,new in snapshot:
        if EXPECTED.get(pid)!=digest(old):
            raise RuntimeError(f'{slug}: content changed since audit; no writes')
    targets=[item for item in snapshot if item[3]!=item[4]]
    print('PREFLIGHT_OK',len(targets),'changed',23-len(targets),'unchanged; posts',before_total,flush=True)
    if mode=='check':return
    done=[]
    try:
        for pid,slug,row,old,new in targets:
            now=get(pid,auth)
            if digest(now['content']['raw'])!=digest(old):
                raise RuntimeError(f'{slug}: concurrent human edit; stopped')
            done.append((pid,slug,old,new))
            http(f'/wp-json/wp/v2/posts/{pid}',auth,{'content':new})
            saved=get(pid,auth)
            for field in ('id','slug','status','title','featured_media','author','categories'):
                if saved[field]!=row[field]:
                    raise RuntimeError(f'{slug}: protected field changed: {field}')
            if saved['content']['raw']!=new:
                raise RuntimeError(f'{slug}: WP raw-content mismatch')
            if len(ad_sections(saved['content']['raw']))>3:
                raise RuntimeError(f'{slug}: too many ad H2 sections')
            print('APPLIED_VERIFIED',pid,slug,flush=True)
        if publish_count(auth)!=before_total:raise RuntimeError('published posts count changed')
        for pid,slug,row,old,new in snapshot:
            current=get(pid,auth)
            if (current['id'],current['slug'],current['status'])!=(pid,slug,'publish'):
                raise RuntimeError(f'{slug}: final identity mismatch')
            if current['content']['raw']!=new:
                raise RuntimeError(f'{slug}: final content mismatch')
            if len(ad_sections(new))>3:
                raise RuntimeError(f'{slug}: final H2 ad count over three')
            print('FINAL_QA_OK',pid,slug,flush=True)
        print('FINAL_SUCCESS changed='+str(len(targets))+' unchanged='+str(23-len(targets)),flush=True)
    except Exception:
        for pid,slug,old,new in reversed(done):
            try:
                if digest(get(pid,auth)['content']['raw'])==digest(new):
                    http(f'/wp-json/wp/v2/posts/{pid}',auth,{'content':old})
                    print('ROLLBACK',pid,slug,flush=True)
            except Exception as e:
                print('ROLLBACK_FAILED',pid,slug,str(e),flush=True)
        raise

if __name__=='__main__':
    mode=sys.argv[1] if len(sys.argv)>1 else 'audit'
    if mode not in ('audit','check','apply'):raise SystemExit('usage: audit/check/apply')
    main(mode)
