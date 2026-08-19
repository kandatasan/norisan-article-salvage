#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, hashlib, html, json, os, re, urllib.parse, urllib.request
from pathlib import Path
from typing import Any

SITE_URL = "https://tsurikue.com"
USER_AGENT = "tsurikue-editorial-rollback/1.0"
REPORT_ROOT = Path("reports/editorial-rollback")


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def get_json(url: str, authorization: str):
    req=urllib.request.Request(url,headers={"Accept":"application/json","Authorization":authorization,"User-Agent":USER_AGENT},method="GET")
    with urllib.request.urlopen(req,timeout=45) as r:
        return json.loads(r.read().decode("utf-8")),dict(r.headers)


def post_json(url: str, authorization: str, payload: dict[str,Any]):
    req=urllib.request.Request(url,data=json.dumps(payload,ensure_ascii=False).encode("utf-8"),headers={"Accept":"application/json","Content-Type":"application/json; charset=utf-8","Authorization":authorization,"User-Agent":USER_AGENT},method="POST")
    with urllib.request.urlopen(req,timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def raw_field(row,key):
    v=row.get(key) or {}
    if isinstance(v,dict): return v.get("raw") or v.get("rendered") or ""
    return str(v)


def media_ids(content: str) -> list[int]:
    out=[]
    for m in re.finditer(r"wp-image-(\d+)|\"id\"\s*:\s*(\d+)",content):
        mid=int(m.group(1) or m.group(2))
        if mid not in out: out.append(mid)
    return out


def count_published(endpoint,auth):
    q=urllib.parse.urlencode({"context":"edit","status":"publish","per_page":"1","_fields":"id"})
    _,h=get_json(f"{SITE_URL}/wp-json/wp/v2/{endpoint}?{q}",auth)
    return int(h.get("X-WP-Total","0"))


def public_counts(auth):
    posts=count_published("posts",auth); pages=count_published("pages",auth)
    return {"published_posts":posts,"published_pages":pages,"published_total":posts+pages}


def fetch_post(cfg,auth):
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,content,featured_media"})
    row,_=get_json(f"{SITE_URL}/wp-json/wp/v2/posts/{cfg['post_id']}?{q}",auth)
    return row


def select_revision(cfg,auth):
    q=urllib.parse.urlencode({"context":"edit","per_page":"100","_fields":"id,parent,date,title,content"})
    revs,_=get_json(f"{SITE_URL}/wp-json/wp/v2/posts/{cfg['post_id']}/revisions?{q}",auth)
    candidates=[]
    for rev in revs:
        content=raw_field(rev,"content")
        title=html.unescape(raw_field(rev,"title"))
        if title!=cfg["restore_title"]: continue
        if cfg["salvage_marker"] not in content: continue
        if cfg["editorial_marker"] in content: continue
        if media_ids(content)!=cfg["restore_media_ids"]: continue
        if any(snippet not in content for snippet in cfg["required_restore_snippets"]): continue
        candidates.append((rev,content))
    if not candidates: raise RuntimeError("no safe pre-editorial revision matched")
    candidates.sort(key=lambda item:((item[0].get("date") or ""),int(item[0].get("id") or 0)),reverse=True)
    return candidates[0]


def apply(config_path: Path):
    cfg=json.loads(config_path.read_text(encoding="utf-8"))
    user=os.environ.get("TSURIKUE_WP_USER"); password=os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password: raise SystemExit("BLOCKED_MISSING_SECRETS")
    auth=auth_header(user,password)
    before_counts=public_counts(auth)
    before=fetch_post(cfg,auth)
    current=raw_field(before,"content")
    current_title=html.unescape(raw_field(before,"title"))
    current_sha=hashlib.sha256(current.encode()).hexdigest()
    if before.get("id")!=cfg["post_id"] or before.get("slug")!=cfg["slug"]: raise RuntimeError("post id/slug mismatch")
    if before.get("status")!="draft": raise RuntimeError("target is not draft")
    if int(before.get("featured_media") or 0)!=cfg["current_featured_media"]: raise RuntimeError("current featured_media mismatch")
    if current_title!=cfg["current_title"]: raise RuntimeError("current title mismatch")
    if cfg["editorial_marker"] not in current: raise RuntimeError("current editorial marker missing")
    if current_sha!=cfg["current_content_sha256"]: raise RuntimeError(f"current content sha mismatch: {current_sha}")

    revision,revision_content=select_revision(cfg,auth)
    original_revision_sha=hashlib.sha256(revision_content.encode()).hexdigest()
    restored_content=revision_content.rstrip()+"\n\n"+cfg["editorial_marker"]+"\n"+cfg["rollback_marker"]+"\n"
    payload={"title":cfg["restore_title"],"slug":cfg["slug"],"content":restored_content,"status":"draft","featured_media":cfg["restore_featured_media"]}
    response=post_json(f"{SITE_URL}/wp-json/wp/v2/posts/{cfg['post_id']}",auth,payload)
    if response.get("id")!=cfg["post_id"] or response.get("slug")!=cfg["slug"] or response.get("status")!="draft": raise RuntimeError("rollback response mismatch")

    after=fetch_post(cfg,auth); after_counts=public_counts(auth)
    if after_counts!=before_counts: raise RuntimeError("published counts changed")
    after_content=raw_field(after,"content")
    after_title=html.unescape(raw_field(after,"title"))
    if after.get("status")!="draft" or after.get("slug")!=cfg["slug"]: raise RuntimeError("post-rollback state mismatch")
    if after_title!=cfg["restore_title"] or int(after.get("featured_media") or 0)!=cfg["restore_featured_media"]: raise RuntimeError("post-rollback title/media mismatch")
    if after_content.strip()!=restored_content.strip(): raise RuntimeError("post-rollback content mismatch")
    if cfg["rollback_marker"] not in after_content or cfg["editorial_marker"] not in after_content: raise RuntimeError("rollback safety markers missing")

    report={"action":"ROLLBACK","post_id":cfg["post_id"],"slug":cfg["slug"],"status":"draft","title":after_title,"featured_media":int(after.get("featured_media") or 0),"restore_revision_id":revision.get("id"),"restore_revision_date":revision.get("date"),"restore_revision_content_sha256":original_revision_sha,"restored_content_sha256":hashlib.sha256(after_content.encode()).hexdigest(),"restored_media_ids":media_ids(after_content),"public_before":before_counts,"public_after":after_counts,"wordpress_write_count":1,"publish_count":0,"media_upload_count":0}
    out=REPORT_ROOT/cfg["slug"]; out.mkdir(parents=True,exist_ok=True)
    (out/"result.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=[f"# {cfg['slug']} editorial rollback","",f"- action: **ROLLBACK**",f"- post_id: **{report['post_id']}**",f"- status: **draft**",f"- title: {report['title']}",f"- featured_media: **{report['featured_media']}**",f"- restore_revision_id: **{report['restore_revision_id']}**",f"- restore_revision_date: {report['restore_revision_date']}",f"- restored_media_ids: **{', '.join(map(str,report['restored_media_ids']))}**",f"- public_before: **{before_counts['published_total']}**",f"- public_after: **{after_counts['published_total']}**",f"- wordpress_write_count: **1**",f"- publish_count: **0**",f"- restore_revision_content_sha256: `{original_revision_sha}`",f"- restored_content_sha256: `{report['restored_content_sha256']}`"]
    (out/"summary.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--config",required=True); args=ap.parse_args(); apply(Path(args.config)); return 0

if __name__=="__main__": raise SystemExit(main())
