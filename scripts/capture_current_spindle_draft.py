#!/usr/bin/env python3
"""Read-only capture of the current spindle-grille draft for safe diffing."""
import base64, hashlib, json, os, urllib.parse, urllib.request
from pathlib import Path

SITE_URL = "https://tsurikue.com"
POST_ID = 2530
OUT = Path("reports/spindle-current-capture")


def auth_header(user, password):
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


def get_json(url, auth):
    req = urllib.request.Request(url, headers={"Accept":"application/json","Authorization":auth,"User-Agent":"tsurikue-spindle-current-capture/1.0"}, method="GET")
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode("utf-8"))


def raw(row, key):
    value = row.get(key) or {}
    return value.get("raw") or value.get("rendered") or "" if isinstance(value, dict) else str(value)


def main():
    user=os.environ.get("TSURIKUE_WP_USER"); password=os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password: raise SystemExit("BLOCKED_MISSING_SECRETS")
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,content,featured_media,modified"})
    row=get_json(f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}?{q}", auth_header(user,password))
    content=raw(row,"content")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/"current-content.html").write_text(content, encoding="utf-8")
    result={"mode":"read-only","wordpress_write_count":0,"id":row.get("id"),"slug":row.get("slug"),"status":row.get("status"),"title":raw(row,"title"),"featured_media":int(row.get("featured_media") or 0),"modified":row.get("modified"),"content_length":len(content),"content_sha256":hashlib.sha256(content.encode()).hexdigest()}
    (OUT/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
