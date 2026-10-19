#!/usr/bin/env python3
"""Update ONLY existing unpublished WP page 4230 to v02, iframe-free Shadow DOM."""
import base64
import json
import os
import re
import urllib.request
from pathlib import Path

API="https://tsurikue.com/wp-json/wp/v2"
PAGE_ID=4230
SLUG="river-atlas-watershed-preview"
OLD_MARKER="tsurikue-river-atlas:watershed-switcher-v01"
NEW_MARKER="tsurikue-river-atlas:watershed-switcher-v02"
HERE=Path(__file__).resolve().parent
OUT=HERE/"watershed-switcher-v02"

def request(path,auth,method="GET",payload=None):
    data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode()
    headers={"Authorization":auth,"Accept":"application/json","User-Agent":"tsurikue-river-atlas-v02-draft/1.0"}
    if data is not None:headers["Content-Type"]="application/json; charset=utf-8"
    with urllib.request.urlopen(urllib.request.Request(API+path,data=data,headers=headers,method=method),timeout=90) as resp:
        return json.loads(resp.read().decode())

def wp_content():
    page=(OUT/"standalone.html").read_text(encoding="utf-8")
    css=re.search(r"<style>(.*?)</style>",page,re.S).group(1)
    markup=re.search(r"(<main id=\"river-atlas\">.*?</main>)",page,re.S).group(1)
    app=page.rsplit("<script>",1)[1].split("</script>")[0]
    app=app.replace('document.getElementById("river-atlas")','shadow.getElementById("river-atlas")')
    datajs=(OUT/"data.js").read_text(encoding="utf-8")
    assert "8707090029" in datajs and "<iframe" not in markup
    # Shadow DOM isolates atlas styles from SWELL and requires no iframe.
    bootstrap="""(function(){
const host=document.getElementById("tsurikue-river-atlas-v02");
if(!host)return;
const shadow=host.attachShadow({mode:"open"});
const style=document.createElement("style");style.textContent=CSS_TEXT;
shadow.append(style);
const shell=document.createElement("div");shell.innerHTML=ATLAS_HTML;
while(shell.firstChild)shadow.append(shell.firstChild);
APP_JS
})();"""
    # App IIFE runs within bootstrap lexical scope and sees shadow.
    js=bootstrap.replace("CSS_TEXT",json.dumps(css,ensure_ascii=False)).replace("ATLAS_HTML",json.dumps(markup,ensure_ascii=False)).replace("APP_JS",datajs+"\n"+app)
    return "<!-- "+NEW_MARKER+" -->\n<!-- wp:html -->\n<div id=\"tsurikue-river-atlas-v02\"></div>\n<script>\n"+js+"\n</script>\n<!-- /wp:html -->"

def main():
    user=os.getenv("TSURIKUE_WP_USER");pw=os.getenv("TSURIKUE_WP_APP_PASSWORD")
    if not user or not pw:raise RuntimeError("WP secrets unavailable")
    auth="Basic "+base64.b64encode((user+":"+pw).encode()).decode()
    before=request(f"/pages/{PAGE_ID}?context=edit",auth)
    raw=before.get("content",{}).get("raw","")
    if before.get("status")!="draft" or before.get("slug")!=SLUG or OLD_MARKER not in raw:
        raise RuntimeError("Draft identity/status/old marker mismatch: abort")
    if NEW_MARKER in raw:raise RuntimeError("v02 already installed: abort")
    body=wp_content()
    assert "<iframe" not in body and "window.RIVER_ATLAS=" in body
    changed=request(f"/pages/{PAGE_ID}",auth,"POST",{"status":"draft","content":body})
    after=request(f"/pages/{PAGE_ID}?context=edit",auth)
    stored=after.get("content",{}).get("raw","")
    report={"id":PAGE_ID,"status":after.get("status"),"slug":after.get("slug"),"marker_preserved":NEW_MARKER in stored,"no_iframe":"<iframe" not in stored,"river_data_preserved":"8707090029" in stored,"script_preserved":"attachShadow" in stored,"edit_url":f"https://tsurikue.com/wp-admin/post.php?post={PAGE_ID}&action=edit"}
    (OUT/"wp-draft-update-result.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))
    if report["status"]!="draft" or not all(report[k] for k in ("marker_preserved","no_iframe","river_data_preserved","script_preserved")):
        raise RuntimeError("WP v02 stored content verification failed")
if __name__=="__main__":main()
