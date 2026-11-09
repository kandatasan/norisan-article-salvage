#!/usr/bin/env python3
"""Read-only public QA for CTN official material 002 after successful WordPress save.

A page can contain tracking URL twice in rendered markup (src/data-src or plugins);
do not equate that URL count with the number of visible CTN buttons.
"""
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
OUT=Path("reports/ctn-official-002-postdeploy-20261110")
def main():
    result=[]
    for slug,count in POSTS:
        u="https://tsurikue.com/"+slug+"/?ctn002_postdeploy_check=20261110"
        headers={"User-Agent":"Mozilla/5.0 (tsurikue-ctn-002-public-read-only)",
                 "Cache-Control":"no-cache","Pragma":"no-cache"}
        with urllib.request.urlopen(urllib.request.Request(u,headers=headers),timeout=40) as res:
            raw=res.read().decode("utf-8","replace")
            status=res.status
        s=html.unescape(raw)
        wrapper=len(re.findall(r'<div class="tsq-ctn-official-002-20261110">',s))
        links=len(re.findall(r'<a href="https://px\.a8\.net/svt/ejp\?a8mat=3Z8YF4\+7VEGL6\+5I4S\+5YRHE" rel="nofollow">【CTN一括車査定】</a>',s))
        pixels=s.count("https://www11.a8.net/0.gif?a8mat=3Z8YF4+7VEGL6+5I4S+5YRHE")
        top=len(re.findall(r'<div class="tsq-ctn-cta-20261110 top"',s))
        bottom=len(re.findall(r'<div class="tsq-ctn-cta-20261110 bottom"',s))
        free=len(re.findall(r'<div class="tsq-ctn-free-lead">無料で試してみる</div>',s))
        styles='.tsq-ctn-official-002-20261110 > a{' in s
        ok=status==200 and wrapper==links==top==bottom==free==count and (pixels>=1 if count else pixels==0) and (styles if count else not styles)
        row={"slug":slug,"expected":count,"wrapper":wrapper,"links":links,"pixel_url_occurrences":pixels,
             "top":top,"bottom":bottom,"free":free,"styles":styles,"status":status,"ok":ok}
        result.append(row)
        print("CTN_002_PUBLIC_VERIFIED" if ok else "CTN_002_PUBLIC_MISMATCH",json.dumps(row,ensure_ascii=False),flush=True)
    OUT.mkdir(parents=True,exist_ok=True)
    data={"checked":len(result),"passed":sum(x["ok"] for x in result),"visible_ctas":sum(x["links"] for x in result),"results":result}
    (OUT/"public.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if data["passed"]!=len(POSTS):raise RuntimeError("CTN public verification failed")
    print("CTN_002_ALL_PUBLIC_VERIFIED",data["passed"],flush=True)
if __name__=="__main__":main()
