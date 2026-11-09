#!/usr/bin/env python3
"""Read-only public verification of all 23 CTN-revised pages and official 002 button."""
from __future__ import annotations
import html,json,re,urllib.request
from pathlib import Path

POSTS=[
("ux-resale",1),("ux-mitsumori",1),("ux300h",0),("ux-koukai",1),
("lexus-ux-used",1),("lexus-ux-price",1),("lexus-ux-discount",1),
("lexus-ux-emotional-explorer",1),("lexus-ux250h-used-vs-ux300h",1),
("lexus-ux-vs-nx",1),("lexus-ux-vs-lbx",1),("lexus-lbx-regret",0),
("lexus-lbx-options",1),("car-sell-high",1),("goodbuy",1),
("lexus-lbx-cheap",1),("lexus-lbx-price",1),("lexus-lbx-used",1),
("tanto-6years-review",0),("tanto-used-best-year",1),
("tanto-model-history",0),("landcruiser-fj-price",1),("landcruiser-fj-cheap",1)
]
OUT=Path("reports/ctn-official-002-20261110")
def main():
    rows=[]
    for slug,count in POSTS:
        u="https://tsurikue.com/"+slug+"/?tsq_ctn_002=20261110"
        h={"User-Agent":"Mozilla/5.0 (tsurikue-ctn-002-qa)","Cache-Control":"no-cache","Pragma":"no-cache"}
        with urllib.request.urlopen(urllib.request.Request(u,headers=h),timeout=40) as r:
            raw=r.read().decode("utf-8","replace")
            status=r.status
        s=html.unescape(raw)
        # CSS stylesheet repeats the class selector. Count the actual wrapper opening, not the CSS selector.
        wrappers=len(re.findall(r'<div class="tsq-ctn-official-002-20261110">',s))
        urls=len(re.findall(r'<a href="https://px\.a8\.net/svt/ejp\?a8mat=3Z8YF4\+7VEGL6\+5I4S\+5YRHE" rel="nofollow">【CTN一括車査定】</a>',s))
        pixels=len(re.findall(r'src="https://www11\.a8\.net/0\.gif\?a8mat=3Z8YF4\+7VEGL6\+5I4S\+5YRHE"',s))
        top=len(re.findall(r'<div class="tsq-ctn-cta-20261110 top"',s))
        bottom=len(re.findall(r'<div class="tsq-ctn-cta-20261110 bottom"',s))
        frees=len(re.findall(r'<div class="tsq-ctn-free-lead">無料で試してみる</div>',s))
        old_blogparts='[blog_parts id="2184"]' in s or '[blog_parts id="3788"]' in s
        ok=(status==200 and wrappers==urls==pixels==top==bottom==frees==count and not old_blogparts)
        rows.append({"slug":slug,"expected":count,"wrappers":wrappers,"links":urls,"pixels":pixels,
                     "top":top,"bottom":bottom,"free":frees,"status":status,"ok":ok})
        print("CTN_002_PUBLIC_OK" if ok else "CTN_002_PUBLIC_FAILED",slug,flush=True)
    OUT.mkdir(parents=True,exist_ok=True)
    report={"checked":len(rows),"passed":sum(x["ok"] for x in rows),"cta_count":sum(x["expected"] for x in rows),
            "rows":rows}
    (OUT/"public.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if report["passed"]!=len(rows):raise RuntimeError("Public CTN official 002 QA failed")
    print("CTN_002_PUBLIC_ALL_OK",report["passed"],flush=True)
if __name__=="__main__":main()
