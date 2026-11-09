#!/usr/bin/env python3
"""Chromium mobile/desktop smoke for scoped official CTN buttons (no link clicks)."""
from pathlib import Path
import asyncio,json
from playwright.async_api import async_playwright

OUT=Path("reports/ctn-official-002-20261110/screenshots")
URLS=["ux-koukai","lexus-ux-used","landcruiser-fj-price"]
async def main():
    OUT.mkdir(parents=True,exist_ok=True)
    checked=[]
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(headless=True)
        for viewport in (375,1280):
            context=await browser.new_context(viewport={"width":viewport,"height":812},device_scale_factor=1)
            for slug in URLS:
                page=await context.new_page()
                await page.goto("https://tsurikue.com/"+slug+"/?tsq_ctn_browser=20261110",
                                wait_until="domcontentloaded",timeout=60000)
                box=page.locator(".tsq-ctn-official-002-20261110")
                assert await box.count()==1, f"{slug}: button wrapper absent"
                a=box.locator(":scope > a")
                assert await a.count()==1, f"{slug}: anchor absent"
                await a.scroll_into_view_if_needed()
                rect=await a.bounding_box()
                assert rect, f"{slug}: button not visible"
                assert rect["width"]>=min(300,viewport-40),f"{slug}: CTA unexpectedly narrow {rect}"
                assert rect["x"]>=-2 and rect["x"]+rect["width"]<=viewport+2,f"{slug}: CTA horizontal overflow {rect}"
                color=await a.evaluate("(a)=>getComputedStyle(a).backgroundColor")
                assert color=="rgb(23, 134, 76)",f"{slug}: wrong CTA color {color}"
                href=await a.get_attribute("href")
                assert href=="https://px.a8.net/svt/ejp?a8mat=3Z8YF4+7VEGL6+5I4S+5YRHE"
                assert (await a.inner_text()).strip()=="【CTN一括車査定】"
                assert (await box.locator(".tsq-ctn-free-lead").inner_text()).strip()=="無料で試してみる"
                await box.screenshot(path=str(OUT/f"{slug}-{viewport}.png"))
                checked.append({"slug":slug,"width":viewport,"rect":rect,"background":color,"ok":True})
                print("CTN_002_BROWSER_OK",slug,viewport,flush=True)
                await page.close()
            await context.close()
        await browser.close()
    (OUT.parent/"browser.json").write_text(json.dumps(checked,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("CTN_002_BROWSER_ALL_OK",len(checked),flush=True)
if __name__=="__main__":asyncio.run(main())
