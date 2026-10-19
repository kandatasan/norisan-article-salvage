#!/usr/bin/env python3
"""Create one guarded, unpublished WordPress page for river atlas preview."""
import base64
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

API="https://tsurikue.com/wp-json/wp/v2"
SLUG="river-atlas-watershed-preview"
MARKER="tsurikue-river-atlas:watershed-switcher-v01"
ROOT=Path(__file__).resolve().parent
OUTPUT=ROOT/"watershed-switcher-v01"
REPORT=OUTPUT/"wp-draft-result.json"

def request(path,auth,method="GET",payload=None):
    data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode("utf-8")
    headers={"Authorization":auth,"Accept":"application/json","User-Agent":"tsurikue-river-atlas-draft/1.0"}
    if data is not None:headers["Content-Type"]="application/json; charset=utf-8"
    with urllib.request.urlopen(urllib.request.Request(API+path,data=data,headers=headers,method=method),timeout=90) as response:
        return json.loads(response.read().decode("utf-8")),dict(response.headers)

def main():
    user=os.getenv("TSURIKUE_WP_USER")
    password=os.getenv("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:raise RuntimeError("WP credentials not configured")
    auth="Basic "+base64.b64encode((user+":"+password).encode()).decode()
    html=(OUTPUT/"standalone.html").read_text(encoding="utf-8")
    if "window.RIVER_ATLAS=" not in html or "8707090029" not in html:raise RuntimeError("Real data missing")
    # The editor receives a Gutenberg custom HTML block. Never create a published page.
    body="<!-- "+MARKER+" -->\n<!-- wp:html -->\n"+html+"\n<!-- /wp:html -->"
    q=urllib.parse.urlencode({"context":"edit","slug":SLUG,"status":"any","per_page":20})
    existing,_=request("/pages?"+q,auth)
    if existing:raise RuntimeError("Existing page with same slug: refuse overwrite")
    payload={"title":"【確認用】日本の河川大図鑑｜全国水系検索","slug":SLUG,"status":"draft","content":body,"comment_status":"closed"}
    page,_=request("/pages",auth,"POST",payload)
    pid=page.get("id")
    if not pid or page.get("status")!="draft":raise RuntimeError("Draft create response invalid")
    check,_=request("/pages/"+str(pid)+"?context=edit",auth)
    raw=check.get("content",{}).get("raw","")
    result={"id":pid,"status":check.get("status"),"slug":check.get("slug"),"edit_url":f"https://tsurikue.com/wp-admin/post.php?post={pid}&action=edit","preview_url":check.get("link","")+"?preview=true","marker_preserved":MARKER in raw,"script_preserved":"window.RIVER_ATLAS=" in raw,"river_preserved":"8707090029" in raw}
    REPORT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False))
    if result["status"]!="draft" or not all(result[k] for k in ("marker_preserved","script_preserved","river_preserved")):
        raise RuntimeError("Draft exists but HTML stripped: inspect report, do not publish")

if __name__=="__main__":main()
