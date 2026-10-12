#!/usr/bin/env python3
"""つりくえ！ five-article subtractive edit: remove sales detours, keep owner's voice.
PR = authenticated GET/read-only preflight. main push = exact-content guarded edits.
"""
from __future__ import annotations
import base64, hashlib, json, os, re, sys, urllib.parse, urllib.request

SITE = "https://tsurikue.com"
POSTS = {
 2222:"ux-resale",2240:"ux-mitsumori",2329:"ux300h",
 2517:"ux-koukai",3608:"lexus-lbx-regret"
}
P = re.compile(r'<!-- wp:paragraph(?:[ \t]+\{[^\n]*\})? -->\s*<p(?:\s[^>]*)?>.*?</p>\s*<!-- /wp:paragraph -->',re.S)
SC = re.compile(r'<!-- wp:shortcode -->\s*\[blog_parts id="(\d+)"\]\s*<!-- /wp:shortcode -->')
ADS = re.compile(r'https://px\.a8\.net/svt/ejp\?a8mat=[^"\s<]+')
def sha(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()

REMOVE = {
 2517: [
 "レクサスUXを買って、街中も旅行も気軽に走れて",
 "でも、500〜600万円台を出したあとで",
 "しかもガリバーには、Webに出る前の",
 "お宝UX、まだ表に出てないかも",
 "ガリバーで中古のレクサスUXを探してみる",
 "この査定差を見て、",
 "そこで候補になるのがCTNです",
 "ちなみに、このとき私がUXを査定に出したきっかけは",
 "その好奇心で試してみたら",
 "私みたいに「売る気はないけど"
 ],
 2222: [
 "150万円あったら、次の車をどこまで変えられる",
 "2026年9月現在、",
 "つまり150万円あれば、単純な車両価格",
 "同じ車なのに、査定先が違うだけで",
 "これを一度経験すると、最初の査定額だけで",
 "150万円をただの数字で見ると",
 "でも今のレクサスで考えると",
 "私が見た約150万円差は、イメージとしては",
 "CTNなら、やり取りする買取店は最大3社",
 "427万円あれば、次の車を探すときの景色も",
 "車を高く売ることは、売却で得するだけじゃなく",
 "私の場合、CTN経由で2社に実車査定してもらい",
 "10万円、20万円違えば、欲しかったオプション",
 "せっかく買い替えるなら、「いくらで買うか」だけでなく"
 ],
 2329: [
 "UX300hと中古のUX250hで迷っているなら",
 "毎日見るメーターやシフト、燃費まで含めて",
 "ただ、カタログを見ただけでは",
 "250hと300h、どちらにするか見えてきたら次は予算",
 "中古UXを実車ベースで見比べてみる",
 "ガリバーで中古のレクサスUXを探してみる",
 "UX300hと中古UX250hの価格差を比べるのと同じくらい",
 "売るかどうかは、金額を見てから決めればOK"
 ],
 2240: [
 "一方、UXへ乗り換える前のシエンタは",
 "この経験から、私は見積もりが高くなったときに",
 "値引きがないなら、装備を削るか",
 "欲しいメーカーオプションを削る前に、今の車で何万円",
 "三眼LEDやムーンルーフを諦める前に"
 ],
 3608: []
}
def drop_paragraph(s, phrase, slug, applied):
    found=[m for m in P.finditer(s) if phrase in m.group()]
    if len(found)>1: raise RuntimeError(f"{slug}: ambiguous paragraph {phrase}")
    if not found:
        print("ALREADY_ABSENT_OR_EDITED",slug,phrase[:32],flush=True)
        return s
    m=found[0]
    applied.append("paragraph: "+phrase[:42])
    return s[:m.start()]+s[m.end():]

def drop_shortcode(s, part, slug, applied):
    matches=[m for m in SC.finditer(s) if m.group(1)==str(part)]
    if len(matches)>1:raise RuntimeError(f"{slug}: shortcode {part} not unique")
    if not matches:return s
    m=matches[0]
    applied.append(f"shortcode:{part}")
    return s[:m.start()]+s[m.end():]

def drop_section(s, start_heading, next_heading, slug, applied):
    start_pattern=(r'<!-- wp:heading(?:[ \t]+\{[^\n]*\})? -->\s*<h[23][^>]*>'+re.escape(start_heading)+r'</h[23]>\s*<!-- /wp:heading -->')
    end_pattern=(r'<!-- wp:heading(?:[ \t]+\{[^\n]*\})? -->\s*<h[23][^>]*>'+re.escape(next_heading)+r'</h[23]>\s*<!-- /wp:heading -->')
    starts=list(re.finditer(start_pattern,s,re.S))
    if not starts:
        print("ALREADY_ABSENT_OR_EDITED_SECTION",slug,start_heading,flush=True)
        return s
    if len(starts)!=1:raise RuntimeError(f"{slug}: start heading ambiguous")
    start=starts[0].start()
    ends=list(re.finditer(end_pattern,s[starts[0].end():],re.S))
    if len(ends)!=1:raise RuntimeError(f"{slug}: end heading count {len(ends)}")
    end=starts[0].end()+ends[0].start()
    removed=s[start:end]
    if re.search(r'wp:image|wp:gallery|wp:video|<img[^>]+wp-image-',removed,re.I):
        raise RuntimeError(f"{slug}: owner image inside proposed removal")
    applied.append("section: "+start_heading)
    return s[:start]+s[end:]

def transform(old,pid,slug):
    s=old;applied=[]
    for needle in REMOVE[pid]:
        s=drop_paragraph(s,needle,slug,applied)
    if pid==2222:
        old_word="そして私のUXは、納車から約3か月ごろのほぼ同じ時期に"
        if s.count(old_word)==1:
            s=s.replace(old_word,"私のUXは、納車から約3か月ごろのほぼ同じ時期に",1)
            applied.append("opening conjunction removed")
    if pid==2517:
        s=drop_section(s,"今の車が高く売れれば、中古UXはさらに狙いやすい",
                        "買う前に、次はここを見ればOK",slug,applied)
    if pid==3608:
        s=drop_section(s,"乗り換えるなら、今の車の値段も先に見ておく",
                        "まとめ｜LBXで後悔するかは「小ささに何を期待するか」で変わる",slug,applied)
        s=drop_shortcode(s,2843,slug,applied) # Direct Gulliver link in comparative H2 remains.
    if pid==2329:
        s=drop_shortcode(s,2184,slug,applied) # CTN off-topic for a test-drive comparison.
    if s==old:
        raise RuntimeError(f"{slug}: no applicable changes; stop to avoid false success")
    # Require owner's distinctive experience and images preserved.
    signatures={2517:["荷室でテトリスが始まります","約616万円","文句はある。でも私はUXが好きだった"],
                2222:["カーセブンへ427万円","生活のために手放すしか","2025年2月"],
                2329:["左手、どこへ置くん","UX300h、超良くなってるじゃん"],
                2240:["まだ一社目と話してるんだけど","もう最初の会社でいいや","6,156,510"],
                3608:["スクーター感覚","スネまで前席に当たり"]}
    for phrase in signatures[pid]:
        if phrase in old and phrase not in s: raise RuntimeError(f"{slug}: owner signature lost {phrase}")
    for pat in (r'wp-image-\d+',r'<figure\b[^>]*class="[^"]*(?:wp-block-image|wp-block-gallery|wp-block-video)[^"]*"[^>]*>',r'<img\b[^>]*(?:wp-image-\d+|uploads/)[^>]*>'):
        if re.findall(pat,s,re.I)!=re.findall(pat,old,re.I):
            raise RuntimeError(f"{slug}: owner's visual evidence changed")
    # An affiliate link may only be REMOVED as part of a preapproved deletion, never rewritten.
    old_ads=ADS.findall(old);new_ads=ADS.findall(s)
    remaining=list(old_ads)
    for a in new_ads:
        if a not in remaining:raise RuntimeError(f"{slug}: affiliate URL added or changed")
        remaining.remove(a)
    if len(s)>=len(old):raise RuntimeError(f"{slug}: not a subtractive edit")
    # Existing Gutenberg defects must not be made worse.
    for p in ('<!-- wp:','<!-- /wp:'):
        before=old.count(p);after=s.count(p)
        if after>before:raise RuntimeError(f"{slug}: extra block token")
    print("PROPOSED",pid,slug,"chars",len(old),"->",len(s),"removed",len(old)-len(s),
          "A8",len(old_ads),"->",len(new_ads),"changes",json.dumps(applied,ensure_ascii=False),flush=True)
    return s

def req(path,auth,data=None):
    hdr={"Authorization":auth,"Accept":"application/json","User-Agent":"tsurikue-subtractive-five/1"}
    if data is not None:hdr["Content-Type"]="application/json; charset=utf-8"
    q=urllib.request.Request(SITE+path,data=json.dumps(data,ensure_ascii=False).encode() if data is not None else None,
          headers=hdr,method="POST" if data is not None else "GET")
    with urllib.request.urlopen(q,timeout=60) as r:return json.load(r)
def get(pid,auth):
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,content,featured_media,categories,author"})
    return req(f"/wp-json/wp/v2/posts/{pid}?{q}",auth)
def execute(mode):
    user=os.getenv("TSURIKUE_WP_USER");password=os.getenv("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:raise RuntimeError("WordPress credentials absent")
    auth="Basic "+base64.b64encode((user+":"+password).encode()).decode()
    ready=[]
    for pid,slug in POSTS.items():
        row=get(pid,auth)
        if (row["id"],row["slug"],row["status"])!=(pid,slug,"publish"):
            raise RuntimeError(f"{slug}: unexpected post identity or status")
        old=row["content"]["raw"]
        new=transform(old,pid,slug)
        ready.append((pid,slug,row,old,new,sha(old)))
    print("READ_ONLY_PREFLIGHT_OK",len(ready),flush=True)
    if mode=="check":return
    done=[]
    try:
        for pid,slug,row,old,new,digest in ready:
            latest=get(pid,auth)
            if sha(latest["content"]["raw"])!=digest:
                raise RuntimeError(f"{slug}: concurrent human WP edit, stop without overwriting")
            done.append((pid,slug,old,new))  # includes uncertain write for conditional rollback
            req(f"/wp-json/wp/v2/posts/{pid}",auth,{"content":new})
            saved=get(pid,auth)
            for k in ("id","slug","status","title","featured_media","categories","author"):
                if saved[k]!=row[k]:raise RuntimeError(f"{slug}: protected {k} changed")
            if saved["content"]["raw"]!=new:raise RuntimeError(f"{slug}: body not applied")
            print("LIVE_VERIFIED",pid,slug,sha(new),flush=True)
        print("FINAL_SUCCESS",len(done),flush=True)
    except Exception:
        for pid,slug,old,new in reversed(done):
            try:
                current=get(pid,auth)
                if sha(current["content"]["raw"])==sha(new):
                    req(f"/wp-json/wp/v2/posts/{pid}",auth,{"content":old})
                    print("ROLLBACK",pid,slug,flush=True)
            except Exception as e:print("ROLLBACK_FAILED",pid,slug,str(e),flush=True)
        raise

if __name__=="__main__":
    mode=sys.argv[1] if len(sys.argv)>1 else "check"
    if mode not in ("check","apply"):raise SystemExit("usage: check|apply")
    execute(mode)
