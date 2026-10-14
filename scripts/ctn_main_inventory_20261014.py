#!/usr/bin/env python3
"""GET-only WordPress CTA inventory. Never writes to WP or clicks affiliate links."""
import os,base64,json,re,urllib.parse,urllib.request,hashlib,html
from pathlib import Path
IDS={
2222:"ux-resale",2240:"ux-mitsumori",2329:"ux300h",2517:"ux-koukai",2948:"lexus-ux-used",
2956:"lexus-ux-price",2962:"lexus-ux-discount",3570:"lexus-ux-emotional-explorer",
3601:"lexus-ux250h-used-vs-ux300h",3604:"lexus-ux-vs-nx",3606:"lexus-ux-vs-lbx",
3608:"lexus-lbx-regret",3611:"lexus-lbx-options",3614:"car-sell-high",
3835:"goodbuy",3863:"lexus-lbx-cheap",3936:"lexus-lbx-price",3767:"landcruiser-fj-price",
3816:"landcruiser-fj-cheap",3774:"landcruiser-fj-review",3777:"landcruiser-fj-rear-seat",
3778:"landcruiser-fj-drawbacks",4004:"tanto-model-history",3945:"lexus-lbx-used",
3965:"tanto-6years-review",3973:"tanto-used-best-year"
}
path=Path("reports/cta-ctn-main-20261014")
path.mkdir(parents=True,exist_ok=True)
u=os.environ["TSURIKUE_WP_USER"];p=os.environ["TSURIKUE_WP_APP_PASSWORD"]
auth="Basic "+base64.b64encode((u+":"+p).encode()).decode()
data=[]
for pid,slug in IDS.items():
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,content,featured_media"})
    req=urllib.request.Request(f"https://tsurikue.com/wp-json/wp/v2/posts/{pid}?{q}",
        headers={"Authorization":auth,"User-Agent":"tsurikue-cta-inventory/20261014"})
    with urllib.request.urlopen(req,timeout=55) as r:post=json.load(r)
    if (post["id"],post["slug"],post["status"])!=(pid,slug,"publish"):
        raise RuntimeError(f"identity mismatch {pid} {slug}")
    raw=post["content"]["raw"]
    ps=[]
    for m in re.finditer(r'\[blog_parts id="(2184|3788|2846)"\]',raw):
        start=max(0,m.start()-900);end=min(len(raw),m.end()+320)
        context=raw[start:end]
        txt=re.sub(r'<[^>]*>',' ',context)
        txt=re.sub(r'<!--.*?-->',' ',txt,flags=re.S)
        txt=html.unescape(re.sub(r'\s+',' ',txt)).strip()
        blocks=re.findall(r'<!-- wp:(?:html|paragraph)[^\n]*-->.*?<!-- /wp:(?:html|paragraph) -->',raw[max(0,m.start()-600):m.start()],flags=re.S)
        ps.append({"part":int(m.group(1)),"offset":round(m.start()/len(raw),2),"context":txt[-430:],
                   "previous_block":blocks[-1][-650:] if blocks else ""})
    obj={"id":pid,"slug":slug,"sha":hashlib.sha256(raw.encode()).hexdigest(),"ctn":ps,
         "ctn_tail":raw.count("tsq-ctn-last-20261014"),
         "cta_micro":raw.count("tsq-cta-microcopy"),
         "gulliver_micro":raw.count("tsq-gulliver-micro-20261014")}
    data.append(obj)
    print("CTN_INVENTORY",json.dumps(obj,ensure_ascii=False),flush=True)
(path/"inventory.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
print("INVENTORY_OK",len(data),"CTN buttons",sum(len(x["ctn"]) for x in data),flush=True)
