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
EXPECTED={"2222":"f157449077971c7d7407519a3d54fba6e2ce402603a7c9d2986b6bcfb38b8c40","2240":"ed3934088602b4d9552335e1189681a366101ca3526ef7b920522080d2351f67","2329":"408f2ebef91444cf3df5be81397c7941ee3544a1713c0f2143b32bad432c16c2","2517":"60dfdee41d23b9350d785f2b899397289bf5924cbb9ce0dea1ab7a42386934fe","2948":"339883b44f2bbb27884284c80a47714ff1c5955009286e2b4ada544c005da6a4","2956":"341d4e02b6d88b852ffbd9e9b14bbe4568b0cbc65d5718176511c973ec78a0b2","2962":"10b60de9ab12e3cc70fcc51925e44c2629e5a3bd8d43d542242a98da6528c7e1","3570":"2bdb1f6749ccf5197df9cb0f9735a74b3a4afdb355a616e88fca543ee2494cda","3601":"b64f109c73c123ccb79b4bc83a06e13a46a9334c3e2dcc7162f8af2cbc9b9abf","3604":"3b1c3312c72b33bce48ba96432f18957b9c56b3ed29e098b2859be27957dd06e","3606":"3c28bbaa1941c1f04571d865df3c78b5c8d2ed936eb347eca8e57ede15501866","3608":"2819140868dec82a01b5d69d956a88ea06dacf18a6b6d1016022f99187a9753a","3611":"cefccaeedaeb842c477fae8f6965aaaa3d359d701204ef00d77bbf5a61197031","3614":"73ffc46ebb16c32ea767c2a47e205a0d3687e7a4aff1534bbdb2c347851777a8","3767":"b115d696d051a8c3e06ba2a4f1ece093c33a2bab6326d79a3643e7bbf2681220","3774":"ed2fac0d6c00e14e8b1eadc13f4bb6261f74e84bb9ced2f3fa6774ed3fbd6b27","3777":"94ecf1d71a5e46d1744a58070b42dcf448d25a7c4dcf25726f33f47e5bb2dc05","3778":"498d0992f9e815751972ab670f1902d6b1801f0efcce270756a59b35c9cd7613","3816":"c3dcc2158edfe030299b0001f4c3d578c9e8b98d8b030cac2d83901962257c70","3835":"802817dac7379326a63f47d5cfbe6d74468fb1c4718637c564db26fa17181794","3863":"f487736ddadb765e839782ce835d0f9640efe15f15ad5034f08f7b7c46707244","3936":"cccc15f226acf06ed0cc8eb73a033175aebd9aa2eb81c56bf9c195205e1f0c17","4004":"55cc74c22f38e046b2018c6db2acfaba3a8abf204a6ce162f8f9d5d564d70307"}
EXPECTED = {int(k):v for k,v in EXPECTED.items()}
REMOVE_FOOTER_BANNER={2222,2240,2329,3570,3601,3604,3606,3608,3611,3614}
PARAGRAPH_DELETE={
2222:[
"次の車を10万円安く買うのも大事です。",
"もっと差が出れば、私の150万円差のように",
"高く売れる会社は探したい。<br>でも何社からも電話が来るのは避けたい。"],
2240:[
"前の車を少しでも高く売れれば、そのぶん次の車を安く買えたのと同じ",
"シエンタでは、ディーラー下取りと一括査定で25万円の差が出ました。",
"CTNは、条件に合う買取店を最大3社まで紹介する仕組みです。"],
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
            "CTNは車に合う買取店を絞り、やり取りするのは最大3社だけ。利用料・手数料も無料です。",
            "CTNなら、やり取りする買取店は最大3社。電話対応の負担を抑えて比べられます。",slug)
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
    blockers=[]
    for pid,slug in POSTS.items():
        row=get(pid,auth)
        if (row['id'],row['slug'],row['status'])!=(pid,slug,'publish'):
            raise RuntimeError(f'{slug}: WordPress ID/slug/status differs, abort')
        old=row['content']['raw']
        try:
            new=transform(old,pid,slug)
        except Exception as e:
            if mode!='audit':raise
            blockers.append((pid,slug,str(e)))
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
        if blockers: raise RuntimeError(f'cannot approve: {len(blockers)} proposed edits blocked')
        print('READ_ONLY_23_AUDIT_OK',flush=True);return
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
