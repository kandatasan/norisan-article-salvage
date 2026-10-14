#!/usr/bin/env python3
"""Post-deploy read-only CTN mobile and desktop visual geometry QA. Never clicks ads."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
SLUGS=[
"ux-mitsumori","lexus-ux-used","lexus-ux-price","lexus-ux-discount",
"lexus-ux-emotional-explorer","lexus-ux250h-used-vs-ux300h",
"lexus-ux-vs-nx","lexus-ux-vs-lbx","lexus-lbx-options","goodbuy",
"lexus-lbx-cheap","lexus-lbx-price","landcruiser-fj-price","landcruiser-fj-cheap",
]
OUT=Path("reports/cta-ctn-main-20261014/render")
OUT.mkdir(parents=True,exist_ok=True)
results=[]
with sync_playwright() as playwright:
    browser=playwright.chromium.launch(headless=True,args=["--no-sandbox"])
    for slug in SLUGS:
        for device,width in (("mobile",390),("desktop",1366)):
            page=browser.new_page(viewport={"width":width,"height":880},locale="ja-JP",
                device_scale_factor=1,is_mobile=device=="mobile",has_touch=device=="mobile")
            errors=[]
            try:
                resp=page.goto("https://tsurikue.com/"+slug+"/",wait_until="domcontentloaded",timeout=60000)
                page.wait_for_timeout(650)
                top=page.locator(".tsq-ctn-primary-20261014.top")
                bottom=page.locator(".tsq-ctn-primary-20261014.bottom")
                if not resp or resp.status!=200:errors.append("HTTP status not 200")
                if top.count()!=1 or bottom.count()!=1:
                    errors.append(f"CTA microcopy wrapper count top={top.count()} bottom={bottom.count()}")
                for name,loc in (("top",top),("bottom",bottom)):
                    if loc.count()!=1:continue
                    if loc.locator("span").count()!=2:errors.append(name+" has missing phrase segmentation")
                    if not loc.is_visible():errors.append(name+" is hidden")
                    loc.scroll_into_view_if_needed()
                    bounds=loc.bounding_box()
                    if not bounds or bounds["width"]<120:errors.append(name+" bounds are invalid")
                    for idx in range(loc.locator("span").count()):
                        span=loc.locator("span").nth(idx)
                        sb=span.bounding_box()
                        if sb and (sb["x"]< -4 or sb["x"]+sb["width"]>width+4):
                            errors.append(f"{name}: phrase {idx} horizontally clipped {sb}")
                page.locator(".tsq-ctn-primary-20261014.top").scroll_into_view_if_needed()
                page.wait_for_timeout(300)
                if device=="mobile" or slug in ("ux-mitsumori","landcruiser-fj-price"):
                    page.screenshot(path=str(OUT/f"{slug}-{device}.png"),animations="disabled")
                results.append({"slug":slug,"device":device,"width":width,"status":resp.status if resp else None,"errors":errors})
                print("CTN_RENDER",slug,device,"PASS" if not errors else "FAIL",errors,flush=True)
            except Exception as e:
                errors.append(repr(e))
                results.append({"slug":slug,"device":device,"width":width,"errors":errors})
                print("CTN_RENDER",slug,device,"ERROR",repr(e),flush=True)
            finally:page.close()
    browser.close()
(OUT/"result.json").write_text(json.dumps(results,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
passed=sum(1 for x in results if not x["errors"])
print("CTN_RENDER_QA",passed,"/",len(results),flush=True)
if passed!=len(results):raise SystemExit("RESPONSIVE_CTA_QA_FAILED")
