#!/usr/bin/env python3
"""Read-only rendered proof after CTN removal from three FJ owner-experience articles."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

POSTS={"landcruiser-fj-review":"landcruiser-fj-cheap",
       "landcruiser-fj-rear-seat":"landcruiser-fj-cheap",
       "landcruiser-fj-drawbacks":"landcruiser-fj-price"}
OUT=Path("reports/ctn-fj-postcleanup-render-20261012")
OUT.mkdir(parents=True,exist_ok=True)
passed=0
result=[]
with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True,args=["--no-sandbox"])
    for slug,linked_slug in POSTS.items():
        for view,width,height,mobile in [("desktop",1366,900,False),("mobile",390,844,True)]:
            page=browser.new_page(viewport={"width":width,"height":height},device_scale_factor=1,has_touch=mobile,is_mobile=mobile,locale="ja-JP")
            resp=page.goto(f"https://tsurikue.com/{slug}/",wait_until="domcontentloaded",timeout=55000)
            page.wait_for_timeout(700)
            main=page.locator(".post_content").first if page.locator(".post_content").count() else page.locator("article").first
            buttons=main.locator('a[href*="px.a8.net"][href*="3Z8YF4"]')
            internal=main.locator(f'a[href*="/{linked_slug}/"]')
            target=internal.last if internal.count() else main.locator("a").last
            target.scroll_into_view_if_needed(timeout=12000)
            page.wait_for_timeout(350)
            out=OUT/f"{slug}-{view}.png"
            page.screenshot(path=str(out),animations="disabled")
            bounds=page.evaluate("""() => ({width:innerWidth,document:document.documentElement.scrollWidth})""")
            info={"slug":slug,"view":view,"status":resp.status if resp else None,
                  "ctn_anchors_remaining":buttons.count(),"internal_link_count":internal.count(),
                  "overflow":bounds["document"]>bounds["width"]+6,"screenshot":str(out)}
            info["passed"]=info["status"]==200 and info["ctn_anchors_remaining"]==0 and info["internal_link_count"]>=1 and not info["overflow"]
            result.append(info)
            print("POST_CLEANUP_RENDER",json.dumps(info,ensure_ascii=False),flush=True)
            passed+=int(info["passed"])
            page.close()
    browser.close()
(OUT/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print("FINAL_FJ_BROWSER_QA",passed,"/",len(result),flush=True)
if passed!=6:raise SystemExit("POST_CLEANUP_BROWSER_QA_FAILED")
