#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, hashlib, html, json, os, re, urllib.parse, urllib.request
from pathlib import Path

SITE_URL = "https://tsurikue.com"
USER_AGENT = "tsurikue-editorial-rollback-inspector/1.0"
REPORT_ROOT = Path("reports/editorial-rollback-inspect")


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def get_json(url: str, authorization: str):
    req = urllib.request.Request(url, headers={"Accept":"application/json","Authorization":authorization,"User-Agent":USER_AGENT}, method="GET")
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode("utf-8")), dict(r.headers)


def raw_field(row, key):
    v = row.get(key) or {}
    if isinstance(v, dict):
        return v.get("raw") or v.get("rendered") or ""
    return str(v)


def media_ids(content: str) -> list[int]:
    out=[]
    for m in re.finditer(r"wp-image-(\d+)|\"id\"\s*:\s*(\d+)", content):
        mid=int(m.group(1) or m.group(2))
        if mid not in out: out.append(mid)
    return out


def inspect(config_path: Path):
    cfg=json.loads(config_path.read_text(encoding="utf-8"))
    user=os.environ.get("TSURIKUE_WP_USER"); password=os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password: raise SystemExit("BLOCKED_MISSING_SECRETS")
    auth=auth_header(user,password)
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,content,featured_media"})
    post,_=get_json(f"{SITE_URL}/wp-json/wp/v2/posts/{cfg['post_id']}?{q}",auth)
    current=raw_field(post,"content")
    current_title=html.unescape(raw_field(post,"title"))
    if post.get("id")!=cfg["post_id"] or post.get("slug")!=cfg["slug"] or post.get("status")!="draft": raise RuntimeError("target mismatch or not draft")
    if current_title!=cfg["current_title"]: raise RuntimeError("current title mismatch")
    if cfg["editorial_marker"] not in current: raise RuntimeError("current editorial marker missing")
    current_sha=hashlib.sha256(current.encode()).hexdigest()
    if current_sha!=cfg["current_content_sha256"]: raise RuntimeError(f"current content sha mismatch: {current_sha}")

    rq=urllib.parse.urlencode({"context":"edit","per_page":"100","_fields":"id,parent,date,title,content"})
    revs,_=get_json(f"{SITE_URL}/wp-json/wp/v2/posts/{cfg['post_id']}/revisions?{rq}",auth)
    candidates=[]
    for rev in revs:
        content=raw_field(rev,"content")
        title=html.unescape(raw_field(rev,"title"))
        if cfg["salvage_marker"] not in content: continue
        if cfg["editorial_marker"] in content: continue
        if title!=cfg["restore_title"]: continue
        ids=media_ids(content)
        if ids!=cfg["restore_media_ids"]: continue
        candidates.append({"revision_id":rev.get("id"),"date":rev.get("date"),"title":title,"content_sha256":hashlib.sha256(content.encode()).hexdigest(),"content_length":len(content),"media_ids":ids})
    if not candidates: raise RuntimeError("no matching pre-editorial revision found")
    candidates.sort(key=lambda x:(x.get("date") or "", int(x.get("revision_id") or 0)), reverse=True)
    chosen=candidates[0]
    report={"mode":"READ_ONLY","wordpress_write_count":0,"post_id":post.get("id"),"slug":post.get("slug"),"status":post.get("status"),"current_title":current_title,"current_featured_media":int(post.get("featured_media") or 0),"current_content_sha256":current_sha,"matching_revision_count":len(candidates),"restore_revision":chosen}
    out=REPORT_ROOT/cfg["slug"]; out.mkdir(parents=True,exist_ok=True)
    (out/"result.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=[f"# {cfg['slug']} rollback revision inspection","",f"- mode: **READ ONLY**",f"- wordpress_write_count: **0**",f"- post_id: **{report['post_id']}**",f"- status: **{report['status']}**",f"- current_title: {report['current_title']}",f"- matching_revision_count: **{report['matching_revision_count']}**",f"- restore_revision_id: **{chosen['revision_id']}**",f"- restore_revision_date: {chosen['date']}",f"- restore_title: {chosen['title']}",f"- restore_media_ids: **{', '.join(map(str,chosen['media_ids']))}**",f"- restore_content_sha256: `{chosen['content_sha256']}`",f"- restore_content_length: **{chosen['content_length']}**"]
    (out/"summary.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--config",required=True); args=ap.parse_args(); inspect(Path(args.config)); return 0

if __name__=="__main__": raise SystemExit(main())
