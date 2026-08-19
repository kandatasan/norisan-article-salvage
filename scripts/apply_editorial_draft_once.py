#!/usr/bin/env python3
"""Guarded updater for one salvaged WordPress editorial draft package."""
from __future__ import annotations
import argparse, base64, hashlib, html, json, os, urllib.parse, urllib.request
from pathlib import Path
from typing import Any

SITE_URL = "https://tsurikue.com"
USER_AGENT = "tsurikue-editorial-draft-once/1.1"

def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"

def get_json(url: str, authorization: str):
    req = urllib.request.Request(url, headers={"Accept":"application/json","Authorization":authorization,"User-Agent":USER_AGENT}, method="GET")
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode()), dict(r.headers)

def post_json(url: str, authorization: str, payload: dict[str, Any]):
    req = urllib.request.Request(url, data=json.dumps(payload, ensure_ascii=False).encode(), headers={"Accept":"application/json","Content-Type":"application/json; charset=utf-8","Authorization":authorization,"User-Agent":USER_AGENT}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

def raw_field(row: dict[str, Any], key: str) -> str:
    v=row.get(key) or {}
    if isinstance(v,dict): return v.get("raw") or v.get("rendered") or ""
    return str(v)

def load_package(config_path: Path):
    cfg=json.loads(config_path.read_text(encoding="utf-8"))
    content=(config_path.parent/cfg["content_file"]).read_text(encoding="utf-8").strip()+"\n"
    full=cfg["salvage_marker"]+"\n"+cfg["editorial_marker"]+"\n"+content
    return cfg, full

def fetch_post(cfg, authorization):
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,link,title,content,featured_media"})
    row,_=get_json(f"{SITE_URL}/wp-json/wp/v2/posts/{cfg['post_id']}?{q}",authorization)
    return row

def count_published(endpoint, authorization):
    q=urllib.parse.urlencode({"context":"edit","status":"publish","per_page":"1","_fields":"id"})
    _,h=get_json(f"{SITE_URL}/wp-json/wp/v2/{endpoint}?{q}",authorization)
    return int(h.get("X-WP-Total","0"))

def public_counts(authorization):
    p=count_published("posts",authorization); g=count_published("pages",authorization)
    return {"published_posts":p,"published_pages":g,"published_total":p+g}

def validate_media(cfg, authorization):
    expected={int(k):v for k,v in (cfg.get("expected_media") or {}).items()}
    featured=int(cfg.get("featured_media") or 0)
    if featured and featured not in expected:
        raise RuntimeError("non-zero featured_media must be one of expected_media")
    for media_id,path in expected.items():
        q=urllib.parse.urlencode({"context":"edit","_fields":"id,status,source_url"})
        row,_=get_json(f"{SITE_URL}/wp-json/wp/v2/media/{media_id}?{q}",authorization)
        actual=urllib.parse.unquote(urllib.parse.urlparse(row.get("source_url") or "").path).casefold()
        if actual != path.casefold(): raise RuntimeError(f"media mismatch id={media_id}: {actual}")
    return len(expected)

def validate_target(row,cfg,full):
    if row.get("id")!=cfg["post_id"] or row.get("slug")!=cfg["slug"]: raise RuntimeError("post id/slug mismatch")
    if row.get("status")!="draft": raise RuntimeError("target is not draft; refusing update")
    current=raw_field(row,"content")
    featured=int(cfg.get("featured_media") or 0)
    if cfg["editorial_marker"] in current:
        if current.strip()==full.strip() and html.unescape(raw_field(row,"title"))==cfg["title"] and int(row.get("featured_media") or 0)==featured: return "ALREADY_UP_TO_DATE"
        raise RuntimeError("editorial marker exists but content/title/featured_media differs; refusing overwrite")
    if cfg["salvage_marker"] not in current: raise RuntimeError("salvage marker missing; refusing update")
    return "UPDATE"

def apply(config_path: Path):
    user=os.environ.get("TSURIKUE_WP_USER"); password=os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password: raise SystemExit("BLOCKED_MISSING_SECRETS")
    cfg,full=load_package(config_path); auth=auth_header(user,password)
    featured=int(cfg.get("featured_media") or 0)
    before_counts=public_counts(auth); before=fetch_post(cfg,auth); action=validate_target(before,cfg,full); checked=validate_media(cfg,auth)
    if action=="UPDATE":
        payload={"title":cfg["title"],"slug":cfg["slug"],"content":full,"status":"draft","featured_media":featured}
        response=post_json(f"{SITE_URL}/wp-json/wp/v2/posts/{cfg['post_id']}",auth,payload)
        if response.get("id")!=cfg["post_id"] or response.get("slug")!=cfg["slug"] or response.get("status")!="draft" or int(response.get("featured_media") or 0)!=featured: raise RuntimeError("update response validation failed")
    after=fetch_post(cfg,auth); after_counts=public_counts(auth)
    if after_counts!=before_counts: raise RuntimeError("published counts changed")
    if after.get("status")!="draft" or after.get("slug")!=cfg["slug"] or int(after.get("featured_media") or 0)!=featured: raise RuntimeError("post-update state mismatch")
    if html.unescape(raw_field(after,"title"))!=cfg["title"] or raw_field(after,"content").strip()!=full.strip(): raise RuntimeError("post-update content/title mismatch")
    report={"action":action,"post_id":cfg["post_id"],"slug":cfg["slug"],"status":"draft","title":cfg["title"],"featured_media":featured,"confirmed_media_checked":checked,"public_before":before_counts,"public_after":after_counts,"content_sha256":hashlib.sha256(raw_field(after,"content").encode()).hexdigest(),"wordpress_write_count":1 if action=="UPDATE" else 0,"publish_count":0,"media_upload_count":0}
    out=Path("reports")/f"{cfg['slug']}-draft-update"; out.mkdir(parents=True,exist_ok=True)
    (out/"result.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=[f"# {cfg['slug']} draft editorial update","",f"- action: **{action}**",f"- post_id: **{cfg['post_id']}**",f"- status: **draft**",f"- title: {cfg['title']}",f"- featured_media: **{featured}**",f"- confirmed_media_checked: **{checked}**",f"- public_before: **{before_counts['published_total']}**",f"- public_after: **{after_counts['published_total']}**",f"- content_sha256: `{report['content_sha256']}`"]
    (out/"summary.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return report

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--config",required=True); args=ap.parse_args(); apply(Path(args.config)); return 0
if __name__=="__main__": raise SystemExit(main())
