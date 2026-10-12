#!/usr/bin/env python3
"""Read-only final QA of 23 published CTN articles: exact WP content and live rendering.
Screenshots: desktop/mobile top plus up to two CTN regions. NEVER clicks an affiliate.
"""
from __future__ import annotations
import base64, difflib, hashlib, html, json, os, re, time, urllib.parse, urllib.request
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

SITE="https://tsurikue.com"
TARGETS={
2222:"ux-resale",2240:"ux-mitsumori",2329:"ux300h",2517:"ux-koukai",
2948:"lexus-ux-used",2956:"lexus-ux-price",2962:"lexus-ux-discount",
3570:"lexus-ux-emotional-explorer",3601:"lexus-ux250h-used-vs-ux300h",
3604:"lexus-ux-vs-nx",3606:"lexus-ux-vs-lbx",3608:"lexus-lbx-regret",
3611:"lexus-lbx-options",3614:"car-sell-high",3835:"goodbuy",
3863:"lexus-lbx-cheap",3936:"lexus-lbx-price",3767:"landcruiser-fj-price",
3816:"landcruiser-fj-cheap",3774:"landcruiser-fj-review",
3777:"landcruiser-fj-rear-seat",3778:"landcruiser-fj-drawbacks",
4004:"tanto-model-history"}
OUT=Path("reports/ctn-visual-final-20261012")
OUT.mkdir(parents=True,exist_ok=True)
CONTROLS={2184:"CTN SWELL button",2846:"CTN banner",3788:"FJ CTN SWELL",2890:"CTN/Gulliver combo",2843:"Gulliver"}
CTN_LINK_FRAGMENT="3Z8YF4"
def wp_fetch(pid,auth):
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,content,featured_media"})
    url=f"{SITE}/wp-json/wp/v2/posts/{pid}?{q}"
    for attempt in range(3):
        try:
            req=urllib.request.Request(url,headers={"Authorization":auth,"Accept":"application/json","User-Agent":"tsurikue-ctn-final-render-audit/1.0"})
            with urllib.request.urlopen(req,timeout=35) as res:return json.load(res)
        except Exception:
            if attempt==2:raise
            time.sleep(2+attempt)
def normalize(txt):
    return re.sub(r"\s+"," ",html.unescape(BeautifulSoup(txt,"html.parser").get_text(" ",strip=True))).strip()
def collect_sections(raw):
    heads=list(re.finditer(r"<h2\b[^>]*>.*?</h2>",raw,flags=re.S|re.I))
    sections=[]
    boundaries=[(m.end(),heads[i+1].start() if i+1<len(heads) else len(raw),normalize(m.group(0))) for i,m in enumerate(heads)]
    boundaries=[(0,heads[0].start() if heads else len(raw),"導入")] + boundaries
    for start,end,heading in boundaries:
        block=raw[start:end]
        ids=[int(x) for x in re.findall(r'\[blog_parts id="(\d+)"\]',block)]
        a8links=re.findall(r'<a\b[^>]*href=["\']([^"\']*px\.a8\.net[^"\']*)',block,re.I)
        direct_ctn=[url for url in a8links if CTN_LINK_FRAGMENT in url]
        ctn_blocks=[x for x in ids if x in (2184,2846,3788,2890)]
        if ctn_blocks or a8links or any(x==2843 for x in ids):
            snippet=normalize(block)
            paragraphs=[]
            for match in re.finditer(r'<p(?:\s+[^>]*)?>.*?</p>',block,re.I|re.S):
                t=normalize(match.group(0))
                if t and len(t)>=14:paragraphs.append(t[:250])
            sections.append({"heading":heading,"blog_parts":ids,"ctn_parts":ctn_blocks,"direct_ctn_links":len(direct_ctn),"a8_links":len(a8links),"snippet":snippet[:1350],"paragraphs":paragraphs[:28]})
    return sections
def repeated_near_ctn(sections):
    # Conservative: only flag exceptionally similar long paragraphs across different affiliate sections.
    ps=[(s["heading"],t) for s in sections for t in s["paragraphs"] if len(t)>55]
    matches=[]
    for i,(h1,t1) in enumerate(ps):
        for h2,t2 in ps[i+1:]:
            if h1==h2:continue
            score=difflib.SequenceMatcher(None,t1,t2,autojunk=False).ratio()
            if score>=0.78:matches.append({"heading_1":h1,"heading_2":h2,"ratio":round(score,2),"text_1":t1[:140],"text_2":t2[:140]})
    return sorted(matches,key=lambda x:-x["ratio"])[:8]
def browser_check(browser,record,viewport,is_mobile):
    slug=record["slug"]
    kind="mobile" if is_mobile else "desktop"
    page=browser.new_page(viewport=viewport,device_scale_factor=1,is_mobile=is_mobile,has_touch=is_mobile,locale="ja-JP")
    result={"viewport":kind,"opened":False,"errors":[],"ctn_anchor_count":0,"screenshots":[]}
    page.on("pageerror",lambda err:result["errors"].append(str(err)[:160]))
    try:
        response=page.goto(f"{SITE}/{slug}/",wait_until="domcontentloaded",timeout=50000)
        result["http_status"]=response.status if response else None
        page.wait_for_timeout(1100)
        result["opened"]=result["http_status"]==200
        dims=page.evaluate("""() => ({innerWidth:window.innerWidth, bodyScrollWidth:document.body.scrollWidth, htmlScrollWidth:document.documentElement.scrollWidth, h1:document.querySelector('h1')?.innerText?.slice(0,150) || '', mainWidth:document.querySelector('main')?.getBoundingClientRect().width ?? null})""")
        result.update(dims)
        result["horizontal_overflow"]=max(dims["bodyScrollWidth"],dims["htmlScrollWidth"])>dims["innerWidth"]+6
        directory=OUT/"screenshots"/slug
        directory.mkdir(parents=True,exist_ok=True)
        page.screenshot(path=str(directory/f"{kind}-top.png"),animations="disabled",timeout=25000)
        result["screenshots"].append(f"screenshots/{slug}/{kind}-top.png")
        ctn=page.locator('a[href*="px.a8.net"][href*="3Z8YF4"]')
        result["ctn_anchor_count"]=ctn.count()
        geometries=[]
        for idx in range(min(ctn.count(),2)):
            node=ctn.nth(idx)
            if not node.is_visible():
                result["errors"].append(f"CTN anchor {idx} not visible")
                continue
            node.scroll_into_view_if_needed(timeout=12000)
            page.wait_for_timeout(250)
            bbox=node.bounding_box()
            if bbox:
                geometries.append({"x":round(bbox["x"],1),"y":round(bbox["y"],1),"width":round(bbox["width"],1),"height":round(bbox["height"],1)})
                if bbox["width"]<40 or bbox["height"]<12:
                    result["errors"].append(f"CTA {idx} unexpectedly small {bbox}")
                if bbox["x"]<-8 or bbox["x"]+bbox["width"]>viewport["width"]+8:
                    result["errors"].append(f"CTA {idx} outside viewport")
            page.screenshot(path=str(directory/f"{kind}-ctn-{idx+1}.png"),animations="disabled",timeout=25000)
            result["screenshots"].append(f"screenshots/{slug}/{kind}-ctn-{idx+1}.png")
        result["ctn_boxes"]=geometries
        result["screenshots"].sort()
    except Exception as ex:
        result["errors"].append(f"browser: {type(ex).__name__}: {str(ex)[:220]}")
    finally:
        page.close()
    return result
def main():
    user=os.getenv("TSURIKUE_WP_USER");pwd=os.getenv("TSURIKUE_WP_APP_PASSWORD")
    if not user or not pwd:raise RuntimeError("Missing WP GET-only secrets")
    auth="Basic "+base64.b64encode((user+":"+pwd).encode()).decode()
    audit=[]
    for pid,slug in TARGETS.items():
        row=wp_fetch(pid,auth)
        raw=row["content"]["raw"]
        sections=collect_sections(raw)
        all_aff_sections=[s for s in sections if (s["blog_parts"] or s["a8_links"])]
        ctn_sections=[s for s in sections if s["ctn_parts"] or s["direct_ctn_links"]]
        record={"id":pid,"slug":slug,"title":normalize(row["title"]["rendered"]),"status":row["status"],"featured_media":row["featured_media"],
          "raw_sha256":hashlib.sha256(raw.encode()).hexdigest(),"wp_identity_ok":row["id"]==pid and row["slug"]==slug and row["status"]=="publish",
          "affiliate_h2_sections":len([x for x in all_aff_sections if x["heading"]!="導入"]),
          "ctn_h2_sections":len([x for x in ctn_sections if x["heading"]!="導入"]),
          "ctn_shortcodes":len(re.findall(r'\[blog_parts id="(?:2184|2846|3788|2890)"\]',raw)),
          "affiliate_sections":all_aff_sections,
          "repeated_paragraphs":repeated_near_ctn(all_aff_sections)}
        audit.append(record)
        print(f'WP_OK {pid} {slug} affiliate_h2={record["affiliate_h2_sections"]} ctn_h2={record["ctn_h2_sections"]} sections={[s["heading"][:22] for s in all_aff_sections]}',flush=True)
    (OUT/"wp-audit.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding="utf-8")
    # Read-only automated visual check, never click real affiliate links.
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        for record in audit:
            record["visual"]=[]
            for viewport,is_mobile in [({"width":1366,"height":900},False),({"width":390,"height":844},True)]:
                result=browser_check(browser,record,viewport,is_mobile)
                record["visual"].append(result)
                print(f'RENDER {record["id"]} {result["viewport"]} http={result.get("http_status")} ctn_links={result["ctn_anchor_count"]} overflow={result.get("horizontal_overflow")} errors={result["errors"]}',flush=True)
        browser.close()
    (OUT/"final-results.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# CTN23記事・最終ブラウザQA","",
      "PC=1366px / スマホ=390px。WordPress現在本文と公開ページを読み取り専用で照合。実クリック・広告計測は発生させない。","",
      "| 記事 | H2広告区間 | CTN区間 | PC | スマホ | 文章重複候補 |","|---|---:|---:|---|---|---:|"]
    failures=[]
    for r in audit:
        pc,m=r["visual"]
        def display(v):
            return "OK" if v.get("opened") and not v.get("horizontal_overflow") and not v["errors"] else "要確認"
        if not r["wp_identity_ok"] or r["affiliate_h2_sections"]>3 or any(display(v)!="OK" for v in r["visual"]):failures.append(r["slug"])
        lines.append(f'| {r["slug"]} | {r["affiliate_h2_sections"]} | {r["ctn_h2_sections"]} | {display(pc)} | {display(m)} | {len(r["repeated_paragraphs"])} |')
    lines.extend(["","## 要確認",", ".join(failures) if failures else "機械判定で重大な崩れを確認せず。目視の違和感は別途確認が必要。","","## 広告区間と周辺文章"])
    for r in audit:
        lines.extend(["",f'### {r["slug"]} (post {r["id"]})'])
        for s in r["affiliate_sections"]:
            lines.append(f'- **{s["heading"][:65]}**｜parts={s["blog_parts"]}, A8={s["a8_links"]}')
            lines.append(f'  - {s["snippet"][:360]}')
        for p in r["repeated_paragraphs"][:3]:
            lines.append(f'- 重複候補 {p["ratio"]}: {p["text_1"]} ⇄ {p["text_2"]}')
    (OUT/"report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(f'FINISHED_BROWSER_AUDIT reviewed={len(audit)} cautions={len(failures)} report={OUT}/report.md',flush=True)
    if len(audit)!=23 or any(not r["wp_identity_ok"] for r in audit):
        raise SystemExit("WordPress identity check failure")
if __name__=="__main__":main()
