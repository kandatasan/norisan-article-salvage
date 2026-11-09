#!/usr/bin/env python3
"""Guarded CTN placement and copy rewrite for 23 tsurikue.com published car posts.
PR: authenticated read-only check. Main push: content-only guarded update and verification.
Source baseline: WordPress.2026-11-09.xml. All article content must match before ANY writes.
"""
import base64, hashlib, html, json, os, re, sys, urllib.parse, urllib.request
from pathlib import Path

SITE="https://tsurikue.com"
OUT=Path("reports/ctn-natural-flow-20261110")
SRC={
2222:("ux-resale","83dcad321fbcaab23838d79427a2467d8eb409fd2757fc135883a449e79c6cf7"),
2240:("ux-mitsumori","51066e5e996b62d90a1e482a8a28376458414349dd9927009493ddb7cb583f50"),
2329:("ux300h","01682bb16300b1ba8b1a0e35245b3f8514dc04ae35e6e6cf800e06ea38845194"),
2517:("ux-koukai","eb2ecce1875c9909aff3bae13cb1c8da20cf096c0b66a7524285c7f06f4fb6d6"),
2948:("lexus-ux-used","cfb322a7fe51702c03cbf87f1f9755ac8abfb94c8fef134d1326cddf34ccb26e"),
2956:("lexus-ux-price","41701db9e9b2577dd5263653164724d3e0277fd092363893cc52ea1c59cc5df8"),
2962:("lexus-ux-discount","389c1d0e9c1381805aa06e38d811bb726e62a4b0e2cd4f91b142830608bc0f88"),
3570:("lexus-ux-emotional-explorer","1949137dfa9fc9625eb03b94fa3fc10250c73c4319b4f7b266b070041b484bf7"),
3601:("lexus-ux250h-used-vs-ux300h","517f896a14e5fb7fed9a830d7ac29a80aea263c197a12521345b5b8a44fe2aec"),
3604:("lexus-ux-vs-nx","acf36da8e4aa460871fb4644c055a213f13e686e1149973cfe8de81b72344d95"),
3606:("lexus-ux-vs-lbx","c3827240d2fd750811c188194e4bbc732a0b1511d1a34d5ddc0b36cfcdeb05fa"),
3608:("lexus-lbx-regret","816149cf6415fab1b3edb36f5c90a9a5cb328d9e42f773c2a234c75c30755220"),
3611:("lexus-lbx-options","6202dc4cfd0b8c04f743770b6a501b0391e921b41abe66e45f0d27fb3606b854"),
3614:("car-sell-high","9e9a8b05383f8db1cbb6f8c4a3038fa7ef14ee8afaa73b7adad2d761e16ae99d"),
3835:("goodbuy","c716ca293a16d776051263b2ab2d54c6fdf8acfa08244cfc60f7eba74c9cd56b"),
3863:("lexus-lbx-cheap","85ac0e8308e91c3c0eb35490e37aa441849f6d7c6d62a4c8633f89e896ddfeeb"),
3936:("lexus-lbx-price","770d3c72557132aedb6e87ec3524fa115fdf3c1f6e292e73efe3eb095a202292"),
3945:("lexus-lbx-used","9d5ccdd12e1fbed43c3b48f1ceff51ac6e6f585b2c9e92462f7bcd7c62cbecd0"),
3965:("tanto-6years-review","0890138a6d74691f7bfe1456bd97324cf3c264f55fbd00739d4d4dd42b87c395"),
3973:("tanto-used-best-year","9f81a418fedd7fc129d3f26efd82ef067f2bbe7e135cc7124f29fc005f65654d"),
4004:("tanto-model-history","28aa930e40f79afdb10089532711ef2196301ae36ea1ac6e912b7fd71b75131e"),
3767:("landcruiser-fj-price","1e7560161dc2f9642305aa81131ca3d39b9c12f9d02c3fc805e73d44709c2447"),
3816:("landcruiser-fj-cheap","8e462eb85d54617aa041c7783dac5771c342d37b9514d4bcb3e6acd323b923fb"),
}
# zero-based CTN shortcode indexes to KEEP; all other CTN shortcodes are removed.
KEEPS={2222:[1],2240:[0],2329:[],2517:[0],2948:[0],2956:[0],2962:[0],3570:[0],
3601:[0],3604:[0],3606:[0],3608:[],3611:[0],3614:[0],3835:[0],3863:[0],
3936:[0],3945:[0],3965:[],3973:[0],4004:[],3767:[0],3816:[0]}
MOVE={2517:"ディーラー査定350万円は驚いた",
3945:"中古LBXと中古UX、400万円前後なら両方見たい",
3973:"中古タントを探すなら年式を決めてから在庫を比べる"}
EXTRA={
2517:[
"以前使った一般の一括査定では、申し込み後の電話がすごかった。<br>査定額には驚いたけれど、あの着信ラッシュはもう勘弁。",
"そこでUXを実際に手放すときはCTNを利用しました。<br>私の場合、連絡が来たのは2社だけ。最終的にはカーセブンへ427万円で売却しています。<br><strong>査定先で金額は変わる。でも、電話ラッシュまでは欲しくない。</strong>"
],
3945:[
"次のLBXを買うなら、安く探すだけでなく、今の車をいくらで売れるかも気になります。<br>私はシエンタからUXへ乗り換えたとき、ディーラー下取り50万円に対して一般の一括査定で75万円。<strong>差は25万円でした。</strong>",
"ただ、その一括査定では大量の電話が来ました。<br>後にUXを手放したときはCTNを選び、連絡は2社だけ。最終的に427万円で売却しました。<br>中古LBXの予算を考えるなら、買う車の値段と一緒に今の車の売値も見ておきたいところ。"
],
3973:[
"乗り換えで中古タントを買うなら、購入価格だけでなく、今の車の売値も効いてきます。<br>私がシエンタを手放したときは、ディーラー下取り50万円に対して一般の一括査定では75万円。25万円違いました。",
"その一括査定では電話が大量に来ましたが、後にUXを売却するとき利用したCTNは連絡が2社だけ。<br>電話ラッシュを避けたい人には、こういう選択肢もあります。"
]
}
HTML=r'<!-- wp:html -->\s*<div class="[^"]*(?:tsq-ctn-last-20261014|tsq-ctn-primary-20261014|tsq-cta-microcopy)[^"]*"[^>]*>[^<]*(?:<span[^>]*>[^<]*</span>|<wbr>|<strong[^>]*>[^<]*</strong>|[^<])*</div>\s*<!-- /wp:html -->'
SC=r'<!-- wp:shortcode -->\s*\[blog_parts id="(?:2184|3788|2846)"\]\s*<!-- /wp:shortcode -->'
TRIPLE=re.compile('('+HTML+')\s*('+SC+')\s*('+HTML+')',re.S)
BUTTON=re.compile(SC,re.S)
DIRECT=re.compile(r'(?:<br\s*/?>)?(?:今の車の)?査定額を(?:見ておく|比べる)なら、\s*<a\s+[^>]*href="https://px\.a8\.net/svt/ejp\?a8mat=3Z8YF4\+7VEGL6\+5I4S\+5YRHE"[^>]*>[^<]+</a>\s*<img\b[^>]*src="https://www19\.a8\.net/0\.gif\?a8mat=3Z8YF4\+7VEGL6\+5I4S\+5YRHE"[^>]*>',re.I)
TOP='<!-- wp:html -->\n<div class="tsq-ctn-cta-20261110 top" style="text-align:center;margin:1.1em auto .35em;font-weight:700;font-size:clamp(14px,3.8vw,16px);line-height:1.55">お試しだけでもOK！</div>\n<!-- /wp:html -->'
BOTTOM='<!-- wp:html -->\n<div class="tsq-ctn-cta-20261110 bottom" style="text-align:center;margin:.35em auto 1.15em;font-size:clamp(12px,3.4vw,14px);line-height:1.55">電話ラッシュなし！連絡は最大3社だけ</div>\n<!-- /wp:html -->'
META=("id","slug","status","title","featured_media","categories","author")

def sha(s):return hashlib.sha256(s.encode("utf-8")).hexdigest()
def pblock(s):return '<!-- wp:paragraph -->\n<p>'+s+'</p>\n<!-- /wp:paragraph -->'
def transform(pid,orig):
    a=list(BUTTON.finditer(orig))
    if not a:raise RuntimeError(str(pid)+": missing CTN button")
    if pid==4004:
        m=re.search(r'<!-- wp:heading \{"level":3\} -->\s*<h3[^>]*>買い替えなら、今の車の値段も先に見ておく</h3>.*?'+SC,orig,re.S)
        if not m:raise RuntimeError("4004: CTA-only section changed")
        end=m.end()
        d=re.match(r'\s*<!-- wp:paragraph -->\s*<p>※査定額は[^<]*</p>\s*<!-- /wp:paragraph -->',orig[end:])
        if d:end+=d.end()
        e=re.match(r'\s*<!-- wp:paragraph -->\s*<p>\s*</p>\s*<!-- /wp:paragraph -->',orig[end:])
        if e:end+=e.end()
        new=orig[:m.start()]+orig[end:]
    else:
        groups=list(TRIPLE.finditer(orig))
        if len(groups)!=len(a):raise RuntimeError(str(pid)+": CTN wrappers/shortcodes do not align")
        keep=KEEPS[pid]
        if any(z>=len(groups) for z in keep):raise RuntimeError(str(pid)+": missing kept shortcode")
        saved=[groups[z].group(2) for z in keep]
        new=orig
        for i,g in reversed(list(enumerate(groups))):
            rep='\n\n'+TOP+'\n\n'+g.group(2)+'\n\n'+BOTTOM+'\n\n' if i in keep and pid not in MOVE else ''
            new=new[:g.start()]+rep+new[g.end():]
        new=DIRECT.sub('',new)
        new=re.sub(r'<!-- wp:paragraph -->\s*<p>\s*</p>\s*<!-- /wp:paragraph -->\s*','',new)
        if pid in MOVE:
            want=MOVE[pid]
            h=re.search(r'<!-- wp:heading(?: \{[^\n]*\})? -->\s*<h[23][^>]*>'+re.escape(want)+r'</h[23]>\s*<!-- /wp:heading -->',new)
            if not h:raise RuntimeError(str(pid)+": target heading changed")
            nxt=re.search(r'<!-- wp:heading(?: \{[^\n]*\})? -->',new[h.end():])
            if not nxt:raise RuntimeError(str(pid)+": no next heading")
            at=h.end()+nxt.start()
            extra='\n\n'+'\n\n'.join(pblock(z) for z in EXTRA[pid])+'\n\n'+TOP+'\n\n'+saved[0]+'\n\n'+BOTTOM+'\n\n'
            new=new[:at]+extra+new[at:]
    if len(BUTTON.findall(new))!=len(KEEPS[pid]):raise RuntimeError(str(pid)+": CTN number mismatch")
    if re.findall(r'<!-- wp:image.*?<!-- /wp:image -->',orig,re.S)!=re.findall(r'<!-- wp:image.*?<!-- /wp:image -->',new,re.S):
        raise RuntimeError(str(pid)+": image markup changed")
    if re.findall(r'\[blog_parts id="(?:2843|4172|4173|2890)"\]',orig)!=re.findall(r'\[blog_parts id="(?:2843|4172|4173|2890)"\]',new):
        raise RuntimeError(str(pid)+": non-CTN ad changed")
    if re.findall(r'<h2\b[^>]*>',orig)!=re.findall(r'<h2\b[^>]*>',new):
        raise RuntimeError(str(pid)+": H2 changed")
    before_balance=orig.count('<!-- wp:')-orig.count('<!-- /wp:')
    after_balance=new.count('<!-- wp:')-new.count('<!-- /wp:')
    if before_balance!=after_balance:raise RuntimeError(str(pid)+": Gutenberg block imbalance")
    if new==orig:raise RuntimeError(str(pid)+": no change")
    return new

def auth():
    u=os.environ.get("TSURIKUE_WP_USER");p=os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not u or not p:raise RuntimeError("WordPress secrets absent")
    return 'Basic '+base64.b64encode((u+':'+p).encode()).decode()

def api(path,token,payload=None):
    head={"Authorization":token,"Accept":"application/json","User-Agent":"tsurikue-ctn-natural-flow/20261110"}
    if payload is not None:head["Content-Type"]="application/json; charset=utf-8"
    req=urllib.request.Request(SITE+path,headers=head,method="POST" if payload is not None else "GET",
        data=json.dumps(payload,ensure_ascii=False).encode() if payload is not None else None)
    with urllib.request.urlopen(req,timeout=60) as r:return json.load(r),dict(r.headers)

def fetch(pid,token):
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,featured_media,categories,author,content"})
    return api("/wp-json/wp/v2/posts/"+str(pid)+"?"+q,token)[0]

def published_total(token):
    q=urllib.parse.urlencode({"status":"publish","per_page":1,"_fields":"id"})
    return int(api("/wp-json/wp/v2/posts?"+q,token)[1]["X-WP-Total"])

def raw(p):return p["content"]["raw"]

def main(mode):
    if mode not in ("check","apply"):raise RuntimeError("Expected check/apply")
    token=auth(); count=published_total(token); ready=[]
    for pid,(slug,expected_sha) in SRC.items():
        post=fetch(pid,token)
        if (post["id"],post["slug"],post["status"])!=(pid,slug,"publish"):
            raise RuntimeError(str(pid)+": identity/status changed; NO WRITES")
        if sha(raw(post))!=expected_sha:raise RuntimeError(str(pid)+": content drift; NO WRITES")
        new=transform(pid,raw(post))
        ready.append((pid,post,new))
    OUT.mkdir(parents=True,exist_ok=True)
    record={"expected_posts":23,"published_before":count,"wordpress_modified":False,
            "posts":[{"id":pid,"slug":post["slug"],"before_sha":sha(raw(post)),"after_sha":sha(new),
                      "ctn_before":len(BUTTON.findall(raw(post))),"ctn_after":len(BUTTON.findall(new))}
                     for pid,post,new in ready]}
    (OUT/"preflight.json").write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n")
    print("CTN_NATURAL_FLOW_PREFLIGHT_OK",len(ready),flush=True)
    if mode=="check":return
    done=[]
    try:
        for pid,post,new in ready:
            live=fetch(pid,token)
            if sha(raw(live))!=sha(raw(post)) or any(live[k]!=post[k] for k in META):
                raise RuntimeError(str(pid)+": concurrent change; STOP")
            done.append((pid,post,new))
            api("/wp-json/wp/v2/posts/"+str(pid),token,{"content":new})
            verified=fetch(pid,token)
            if raw(verified)!=new or any(verified[k]!=post[k] for k in META):
                raise RuntimeError(str(pid)+": after-write drift")
            if len(BUTTON.findall(raw(verified)))!=len(KEEPS[pid]):
                raise RuntimeError(str(pid)+": saved CTN count mismatch")
            print("CTN_POST_VERIFIED",pid,post["slug"],flush=True)
        if published_total(token)!=count:raise RuntimeError("Published post total changed")
        record["wordpress_modified"]=True
        record["verified_posts"]=len(done)
        (OUT/"result.json").write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n")
    except Exception:
        for pid,post,new in reversed(done):
            try:
                if sha(raw(fetch(pid,token)))==sha(new):
                    api("/wp-json/wp/v2/posts/"+str(pid),token,{"content":raw(post)})
                    print("CTN_ROLLBACK",pid,flush=True)
            except Exception as err:
                print("CTN_ROLLBACK_FAILED",pid,type(err).__name__,flush=True)
        raise

if __name__=="__main__":
    main(sys.argv[1] if len(sys.argv)>1 else "check")
