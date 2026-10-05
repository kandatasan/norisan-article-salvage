#!/usr/bin/env python3
"""Guarded creator/updater for one WordPress editorial draft package."""
from __future__ import annotations
import argparse, base64, hashlib, html, json, os, re, urllib.parse, urllib.request
from pathlib import Path
from typing import Any

SITE_URL = "https://tsurikue.com"
USER_AGENT = "tsurikue-editorial-draft-once/1.3"

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
    v = row.get(key) or {}
    if isinstance(v, dict): return v.get("raw") or v.get("rendered") or ""
    return str(v)

def load_package(config_path: Path):
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    content = (config_path.parent / cfg["content_file"]).read_text(encoding="utf-8").strip() + "\n"
    full = cfg["salvage_marker"] + "\n" + cfg["editorial_marker"] + "\n" + content
    return cfg, full

def fetch_post(cfg, authorization):
    q = urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,link,title,content,featured_media"})
    row, _ = get_json(f"{SITE_URL}/wp-json/wp/v2/posts/{cfg['post_id']}?{q}", authorization)
    return row

def fetch_post_by_id(post_id: int, authorization):
    q = urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,link,title,content,featured_media,categories"})
    row, _ = get_json(f"{SITE_URL}/wp-json/wp/v2/posts/{post_id}?{q}", authorization)
    return row

def slug_matches(endpoint: str, slug: str, authorization):
    q = urllib.parse.urlencode({"context":"edit","slug":slug,"status":"any","per_page":"100","_fields":"id,slug,status,link"})
    rows, _ = get_json(f"{SITE_URL}/wp-json/wp/v2/{endpoint}?{q}", authorization)
    return rows if isinstance(rows, list) else []

def count_published(endpoint, authorization):
    q = urllib.parse.urlencode({"context":"edit","status":"publish","per_page":"1","_fields":"id"})
    _, h = get_json(f"{SITE_URL}/wp-json/wp/v2/{endpoint}?{q}", authorization)
    return int(h.get("X-WP-Total","0"))

def public_counts(authorization):
    p = count_published("posts", authorization); g = count_published("pages", authorization)
    return {"published_posts":p,"published_pages":g,"published_total":p+g}

def validate_media(cfg, authorization):
    expected = {int(k):v for k,v in (cfg.get("expected_media") or {}).items()}
    featured = int(cfg.get("featured_media") or 0)
    if featured and featured not in expected:
        raise RuntimeError("non-zero featured_media must be one of expected_media")
    for media_id, path in expected.items():
        q = urllib.parse.urlencode({"context":"edit","_fields":"id,status,source_url"})
        row, _ = get_json(f"{SITE_URL}/wp-json/wp/v2/media/{media_id}?{q}", authorization)
        actual = urllib.parse.unquote(urllib.parse.urlparse(row.get("source_url") or "").path).casefold()
        if actual != path.casefold(): raise RuntimeError(f"media mismatch id={media_id}: {actual}")
    return len(expected)

def validate_target(row, cfg, full):
    if row.get("id") != cfg["post_id"] or row.get("slug") != cfg["slug"]: raise RuntimeError("post id/slug mismatch")
    if row.get("status") != "draft": raise RuntimeError("target is not draft; refusing update")
    current = raw_field(row, "content")
    featured = int(cfg.get("featured_media") or 0)
    current_title = html.unescape(raw_field(row, "title"))
    current_featured = int(row.get("featured_media") or 0)
    if cfg["editorial_marker"] in current:
        if current.strip() == full.strip() and current_title == cfg["title"] and current_featured == featured: return "ALREADY_UP_TO_DATE"
        expected_current = (cfg.get("expected_current_content_sha256") or "").strip().casefold()
        expected_current_featured = int(cfg.get("expected_current_featured_media", featured) or 0)
        expected_current_title = html.unescape(str(cfg.get("expected_current_title", cfg["title"])))
        if expected_current and hashlib.sha256(current.encode()).hexdigest().casefold() == expected_current and current_title == expected_current_title and current_featured == expected_current_featured:
            return "UPDATE"
        raise RuntimeError("editorial marker exists but content/title/featured_media differs; refusing overwrite")
    if cfg["salvage_marker"] not in current: raise RuntimeError("salvage marker missing; refusing update")
    return "UPDATE"

def validate_create_package(cfg, full):
    if cfg.get("operation") != "create": raise RuntimeError("create package requires operation=create")
    if cfg.get("status", "draft") != "draft": raise RuntimeError("new post status must be draft")
    if cfg.get("post_id") not in (None, ""): raise RuntimeError("create package must not set post_id")
    slug = str(cfg.get("slug") or "").strip(); title = str(cfg.get("title") or "").strip()
    if not slug or not title: raise RuntimeError("create package requires slug and title")
    categories = cfg.get("categories") or []
    if not isinstance(categories, list) or any(not isinstance(x, int) or x <= 0 for x in categories): raise RuntimeError("categories must be a list of positive integer IDs")
    if "wp-image-0" in full or "/wp-json/" in full: raise RuntimeError("unsafe image/reference marker in create content")
    expected = {int(k) for k in (cfg.get("expected_media") or {}).keys()}
    used = {int(x) for x in re.findall(r"\bwp-image-(\d+)\b", full)}
    if 0 in used: raise RuntimeError("wp-image-0 is not allowed")
    missing = used - expected
    if missing: raise RuntimeError(f"inline media not confirmed: {sorted(missing)}")
    for src in re.findall(r'<img\b[^>]*\bsrc=["\']([^"\']+)["\']', full, flags=re.I):
        parsed = urllib.parse.urlparse(src)
        if parsed.scheme not in ("http", "https") or parsed.netloc.casefold() != "tsurikue.com": raise RuntimeError(f"external/invalid image URL: {src}")
    return len(used)

def write_report(cfg, row, before_counts, after_counts, action, checked, write_count, report_suffix):
    featured = int(cfg.get("featured_media") or 0); post_id = int(row["id"])
    report = {"action":action,"post_id":post_id,"slug":cfg["slug"],"status":"draft","title":cfg["title"],"featured_media":featured,"confirmed_media_checked":checked,"public_before":before_counts,"public_after":after_counts,"content_sha256":hashlib.sha256(raw_field(row,"content").encode()).hexdigest(),"wordpress_write_count":write_count,"publish_count":0,"media_upload_count":0}
    out = Path("reports") / f"{cfg['slug']}-{report_suffix}"; out.mkdir(parents=True, exist_ok=True)
    (out/"result.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines = [f"# {cfg['slug']} {report_suffix.replace('-', ' ')}","",f"- action: **{action}**",f"- post_id: **{post_id}**","- status: **draft**",f"- title: {cfg['title']}",f"- featured_media: **{featured}**",f"- confirmed_media_checked: **{checked}**",f"- public_before: **{before_counts['published_total']}**",f"- public_after: **{after_counts['published_total']}**",f"- content_sha256: `{report['content_sha256']}`"]
    (out/"summary.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2)); return report

def apply_update(cfg, full, auth):
    featured = int(cfg.get("featured_media") or 0)
    before_counts = public_counts(auth); before = fetch_post(cfg, auth); action = validate_target(before, cfg, full); checked = validate_media(cfg, auth)
    if action == "UPDATE":
        payload = {"title":cfg["title"],"slug":cfg["slug"],"content":full,"status":"draft","featured_media":featured}
        response = post_json(f"{SITE_URL}/wp-json/wp/v2/posts/{cfg['post_id']}", auth, payload)
        if response.get("id") != cfg["post_id"] or response.get("slug") != cfg["slug"] or response.get("status") != "draft" or int(response.get("featured_media") or 0) != featured: raise RuntimeError("update response validation failed")
    after = fetch_post(cfg, auth); after_counts = public_counts(auth)
    if after_counts != before_counts: raise RuntimeError("published counts changed")
    if after.get("status") != "draft" or after.get("slug") != cfg["slug"] or int(after.get("featured_media") or 0) != featured: raise RuntimeError("post-update state mismatch")
    if html.unescape(raw_field(after,"title")) != cfg["title"] or raw_field(after,"content").strip() != full.strip(): raise RuntimeError("post-update content/title mismatch")
    return write_report(cfg, after, before_counts, after_counts, action, checked, 1 if action == "UPDATE" else 0, "draft-update")

def apply_create(cfg, full, auth):
    validate_create_package(cfg, full); before_counts = public_counts(auth)
    duplicates = slug_matches("posts", cfg["slug"], auth) + slug_matches("pages", cfg["slug"], auth)
    if duplicates:
        brief = [{"id":r.get("id"),"slug":r.get("slug"),"status":r.get("status")} for r in duplicates]
        raise RuntimeError(f"slug already exists; refusing create: {brief}")
    checked = validate_media(cfg, auth); featured = int(cfg.get("featured_media") or 0)
    payload = {"title":cfg["title"],"slug":cfg["slug"],"content":full,"status":"draft","featured_media":featured}
    if cfg.get("categories"): payload["categories"] = cfg["categories"]
    response = post_json(f"{SITE_URL}/wp-json/wp/v2/posts", auth, payload); post_id = int(response.get("id") or 0)
    if not post_id or response.get("slug") != cfg["slug"] or response.get("status") != "draft": raise RuntimeError("create response validation failed")
    if int(response.get("featured_media") or 0) != featured: raise RuntimeError("create featured_media mismatch")
    after = fetch_post_by_id(post_id, auth); after_counts = public_counts(auth)
    if after_counts != before_counts: raise RuntimeError("published counts changed")
    if after.get("status") != "draft" or after.get("slug") != cfg["slug"] or int(after.get("featured_media") or 0) != featured: raise RuntimeError("post-create state mismatch")
    if html.unescape(raw_field(after,"title")) != cfg["title"] or raw_field(after,"content").strip() != full.strip(): raise RuntimeError("post-create content/title mismatch")
    if cfg.get("categories"):
        actual_categories = sorted(int(x) for x in (after.get("categories") or []))
        if actual_categories != sorted(cfg["categories"]): raise RuntimeError("post-create categories mismatch")
    return write_report(cfg, after, before_counts, after_counts, "CREATE", checked, 1, "draft-create")

def apply(config_path: Path):
    user = os.environ.get("TSURIKUE_WP_USER"); password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password: raise SystemExit("BLOCKED_MISSING_SECRETS")
    cfg, full = load_package(config_path); auth = auth_header(user, password)
    if cfg.get("operation") == "create": return apply_create(cfg, full, auth)
    return apply_update(cfg, full, auth)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--config", required=True); args = ap.parse_args(); apply(Path(args.config)); return 0
if __name__ == "__main__": raise SystemExit(main())
