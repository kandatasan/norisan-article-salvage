#!/usr/bin/env python3
"""Read-only smoke-test of public CTA placement after PR #876; never writes WordPress."""
from __future__ import annotations
import html, json, re, urllib.request, urllib.parse, time
from pathlib import Path

POSTS={
"ux-resale":1,"ux-mitsumori":1,"ux300h":0,"ux-koukai":1,
"lexus-ux-used":1,"lexus-ux-price":1,"lexus-ux-discount":1,
"lexus-ux-emotional-explorer":1,"lexus-ux250h-used-vs-ux300h":1,
"lexus-ux-vs-nx":1,"lexus-ux-vs-lbx":1,"lexus-lbx-regret":0,
"lexus-lbx-options":1,"car-sell-high":1,"goodbuy":1,
"lexus-lbx-cheap":1,"lexus-lbx-price":1,"lexus-lbx-used":1,
"tanto-6years-review":0,"tanto-used-best-year":1,
"tanto-model-history":0,"landcruiser-fj-price":1,"landcruiser-fj-cheap":1
}
OUT=Path("reports/ctn-natural-flow-20261110")
def run():
  rows=[]
  for slug,expected in POSTS.items():
    url="https://tsurikue.com/"+slug+"/?tsq_ctn_audit=20261110"
    headers={"User-Agent":"Mozilla/5.0 (tsurikue-readonly-ctn-audit/20261110)",
             "Cache-Control":"no-cache","Pragma":"no-cache"}
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req,timeout=35) as r:
      raw=r.read().decode("utf-8","replace")
      status=r.status
    text=html.unescape(raw)
    top=text.count("tsq-ctn-cta-20261110 top")
    bottom=text.count("tsq-ctn-cta-20261110 bottom")
    has_top="お試しだけでもOK！" in text
    has_bottom="電話ラッシュなし！連絡は最大3社だけ" in text
    ok=(status==200 and top==expected and bottom==expected
        and (has_top==bool(expected)) and (has_bottom==bool(expected)))
    if slug=="ux-koukai" and expected:
      p=text.find("以前使った一般の一括査定では")
      old=text.find("ディーラー査定350万円は驚いた")
      follow=text.find("売却までの流れや")
      ok=ok and old>=0 and old<p<follow
    rows.append({"slug":slug,"status":status,"top":top,"bottom":bottom,"expected":expected,
                 "visible_top":has_top,"visible_bottom":has_bottom,"ok":ok,"bytes":len(raw)})
    print("PUBLIC_CTN_VERIFIED" if ok else "PUBLIC_CTN_MISMATCH",slug,"expected",expected,
          "top",top,"bottom",bottom,"status",status,flush=True)
  OUT.mkdir(parents=True,exist_ok=True)
  report={"checked":len(rows),"passed":sum(r["ok"] for r in rows),
          "total_cta_expected":sum(POSTS.values()),"results":rows}
  (OUT/"public-render.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
  if report["passed"]!=len(rows):raise RuntimeError("PUBLIC CTN SMOKE TEST DID NOT PASS")
  print("PUBLIC_CTN_RENDER_ALL_OK",report["passed"],flush=True)
if __name__=="__main__":run()
