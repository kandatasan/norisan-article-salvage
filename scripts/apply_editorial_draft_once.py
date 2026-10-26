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
    q = urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,link,title,content,featured_media,categories,author"})
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


def build_published_insertion(current: str, cfg: dict[str, Any], fragment: str) -> tuple[str, str]:
    """Only insert a new block before the uniquely specified existing heading."""
    marker = str(cfg["marker"])
    anchor = str(cfg["anchor_before"])
    shortcode = str(cfg["existing_shortcode"])
    section_heading = str(cfg["section_heading"])
    if current.count(anchor) != 1 and cfg.get("anchor_heading_text"):
        # Accept Gutenberg's harmless heading attributes without changing text or blocks.
        heading = str(cfg["anchor_heading_text"])
        pattern = re.compile(r"<!-- wp:heading(?: [^\n]*)? -->\s*<h2[^>]*>\s*" +
                             re.escape(heading) + r"\s*</h2>\s*<!-- /wp:heading -->", re.S)
        heading_matches = list(pattern.finditer(current))
        if len(heading_matches) == 1:
            anchor = heading_matches[0].group(0)
    if not marker or not anchor or not shortcode or not section_heading:
        raise RuntimeError("published insertion config incomplete")
    if current.count(anchor) != 1 or current.count(section_heading) != 1:
        found_h2 = [re.sub(r"<[^>]*>", "", h).strip() for h in re.findall(r"<h2[^>]*>.*?</h2>", current, re.S)]
        heading_matches = list(re.finditer(r"<h2[^>]*>.*?</h2>", current, re.S))
        section_ctas = []
        for i, m in enumerate(heading_matches):
            section_body = current[m.end():(heading_matches[i+1].start() if i+1 < len(heading_matches) else len(current))]
            section_ctas.append({
                "h2": re.sub(r"<[^>]*>", "", m.group(0)).strip(),
                "blog_parts": re.findall(r'\[blog_parts id=["\x27](\d+)["\x27]\]', section_body),
                "direct_a8_links": len(re.findall(r"px\.a8\.net/svt/ejp", section_body)),
            })
        raise RuntimeError(f"published insertion headings drifted; anchor={current.count(anchor)}, section={current.count(section_heading)}, live_sections={section_ctas[:20]!r}")
    n = current.count(shortcode)
    if not 1 <= n <= 3:
        raise RuntimeError(f"existing CTA shortcodes unexpected: {n}")
    if fragment.count(marker) != 1 or fragment.count(shortcode) != 1:
        raise RuntimeError("insertion must contain one unique marker and one original CTA shortcode")
    if "<!-- wp:" not in fragment or "<!-- /wp:" not in fragment:
        raise RuntimeError("insertion must be Gutenberg blocks")
    section_begin = current.find(section_heading)
    anchor_pos = current.find(anchor)
    if section_begin >= anchor_pos:
        raise RuntimeError("destination is not after the expected appraisal section")
    section_text = current[section_begin:anchor_pos]
    if any(t not in section_text for t in cfg.get("required_section_text", [])):
        raise RuntimeError("appraisal section no longer matches verified copy")
    if shortcode in section_text:
        raise RuntimeError("appraisal section already contains CTN advertising")
    if marker in current:
        raise RuntimeError("unique CTA marker already present; refusing duplicate")
    rendered_fragment = fragment.strip() + "\n\n"
    new = current[:anchor_pos] + rendered_fragment + current[anchor_pos:]
    if new.replace(rendered_fragment, "", 1) != current:
        raise RuntimeError("not a pure insertion")
    if new.count(shortcode) != n + 1:
        raise RuntimeError("CTA count did not increase by exactly one")
    if new.count("<!-- wp:") != current.count("<!-- wp:") + fragment.count("<!-- wp:"):
        raise RuntimeError("Gutenberg block count unexpected")
    return new, marker

def apply_published_insertion(config_path: Path, cfg: dict[str, Any], auth: str):
    """Opt-in guarded update of a published article; all other editorial operations unchanged."""
    pid = int(cfg["post_id"])
    if pid <= 0 or not cfg.get("slug") or not cfg.get("title"):
        raise RuntimeError("post identity is incomplete")
    fragment = (config_path.parent / cfg["insertion_file"]).read_text(encoding="utf-8").strip()
    if not fragment or not fragment.startswith("<!-- wp:") or not fragment.endswith("-->"):
        raise RuntimeError("invalid published insertion fragment")
    before_counts = public_counts(auth)
    original = fetch_post_by_id(pid, auth)
    before_title = html.unescape(raw_field(original, "title"))
    keys = ("id", "slug", "status", "featured_media", "categories", "author")
    if (original.get("id"), original.get("slug"), original.get("status")) != (pid, cfg["slug"], "publish"):
        raise RuntimeError("post id, slug or publish status mismatch")
    accepted_titles = cfg.get("accepted_titles") or [cfg["title"]]
    if before_title not in accepted_titles:
        raise RuntimeError(f"live title mismatch; refusing published edit: {before_title!r}")
    expected_media = cfg.get("expected_featured_media")
    if expected_media is not None and int(original.get("featured_media") or 0) != int(expected_media):
        raise RuntimeError("featured media mismatch")
    current = raw_field(original, "content")
    marker = str(cfg["marker"])
    if marker in current:
        if current.count(marker) == 1 and fragment in current:
            print("PUBLISHED_INSERT_ALREADY_PRESENT", pid, cfg["slug"])
            return {"action": "ALREADY_PRESENT", "post_id": pid, "status": "publish"}
        raise RuntimeError("duplicate marker or edited insertion; refusing update")
    new, marker = build_published_insertion(current, cfg, fragment)
    old_sha = hashlib.sha256(current.encode()).hexdigest()
    new_sha = hashlib.sha256(new.encode()).hexdigest()
    report_dir = Path("reports") / f"{cfg['slug']}-published-insertion"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "preflight.json").write_text(json.dumps({
        "post_id": pid, "slug": cfg["slug"], "source_sha256": old_sha, "target_sha256": new_sha,
        "published_before": before_counts, "existing_ctn_count": current.count(cfg["existing_shortcode"]),
        "target_ctn_count": new.count(cfg["existing_shortcode"]),
        "insertion_marker": marker
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PUBLISHED_INSERT_PREFLIGHT_OK", pid, old_sha, flush=True)
    # A second live fetch prevents overwriting a human edit between reading and applying.
    latest = fetch_post_by_id(pid, auth)
    if any(latest.get(k) != original.get(k) for k in keys) or (
        html.unescape(raw_field(latest, "title")) != before_title or raw_field(latest, "content") != current
    ):
        raise RuntimeError("concurrent WordPress edit; refusing update")
    wrote = False
    try:
        response = post_json(f"{SITE_URL}/wp-json/wp/v2/posts/{pid}", auth, {"content": new})
        wrote = True
        if response.get("id") != pid or response.get("status") != "publish":
            raise RuntimeError("WordPress update response identity mismatch")
        after = fetch_post_by_id(pid, auth)
        after_counts = public_counts(auth)
        if any(after.get(k) != original.get(k) for k in keys):
            raise RuntimeError("post metadata changed during insertion")
        if html.unescape(raw_field(after, "title")) != before_title:
            raise RuntimeError("published title changed")
        if raw_field(after, "content") != new:
            raise RuntimeError("saved content differs from pure insertion")
        if after_counts != before_counts:
            raise RuntimeError("published post/page counts changed")
        if marker not in raw_field(after, "content") or new.count(cfg["existing_shortcode"]) != current.count(cfg["existing_shortcode"]) + 1:
            raise RuntimeError("insertion or CTA verification failed")
        # Also confirm that the microcopy is present in WordPress's rendered output.
        if cfg["rendered_phrase"] not in (after.get("content") or {}).get("rendered", ""):
            raise RuntimeError("inserted copy absent from WordPress rendered content")
        result = {"action":"SUCCESS", "post_id":pid, "slug":cfg["slug"], "status":"publish",
                  "title":before_title, "featured_media":after.get("featured_media"),
                  "old_sha256":old_sha, "new_sha256":new_sha,
                  "existing_ctn_count":current.count(cfg["existing_shortcode"]),
                  "after_ctn_count":new.count(cfg["existing_shortcode"]),
                  "published_before":before_counts, "published_after":after_counts,
                  "wordpress_write_count":1}
        (report_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (report_dir / "summary.md").write_text(
            f"# Published insertion {cfg['slug']}\n\n- result: SUCCESS\n- post_id: {pid}\n"
            f"- slug: {cfg['slug']}\n- status: publish\n- title: {before_title}\n"
            f"- CTA shortcodes: {result['existing_ctn_count']} → {result['after_ctn_count']}\n"
            f"- before: {old_sha}\n- after: {new_sha}\n- WordPress write count: 1\n",
            encoding="utf-8")
        print("PUBLISHED_INSERT_VERIFIED", pid, cfg["slug"], flush=True)
        return result
    except Exception:
        if wrote:
            try:
                now = fetch_post_by_id(pid, auth)
                if raw_field(now, "content") == new and all(
                    now.get(k) == original.get(k) for k in keys
                ):
                    post_json(f"{SITE_URL}/wp-json/wp/v2/posts/{pid}", auth, {"content": current})
                    print("PUBLISHED_INSERT_ROLLBACK", pid, flush=True)
                else:
                    print("PUBLISHED_INSERT_ROLLBACK_SKIPPED_DRIFT", pid, flush=True)
            except Exception as rollback_error:
                print("PUBLISHED_INSERT_ROLLBACK_FAILED", repr(rollback_error), flush=True)
        raise


def build_existing_table_cell_update(current: str, cfg: dict[str, Any]):
    """Replace exactly one data cell in one identified HTML table row."""
    label = str(cfg["target_row_label"])
    if current.count(label) != 1:
        raise RuntimeError("table row label not unique in the current WordPress content")
    at = current.index(label)
    start = current.rfind("<tr>", 0, at)
    close = current.find("</tr>", at)
    if start < 0 or close < 0:
        raise RuntimeError("table row boundaries missing")
    end = close + len("</tr>")
    row = current[start:end]
    if row.count(label) != 1:
        raise RuntimeError("row label mismatch")
    thend = row.find("</th>")
    if thend < 0:
        raise RuntimeError("table header cell missing")
    thend += len("</th>")
    cells = list(re.finditer(r"<td\b[^>]*>[^<]*</td>", row[thend:]))
    n = int(cfg["expected_columns"])
    index = int(cfg["target_column_index"])
    if n <= 0 or len(cells) != n or not (0 <= index < n):
        raise RuntimeError("table column count or index differs")
    cell = cells[index].group(0)
    before_value, after_value = str(cfg["expected_old_value"]), str(cfg["new_value"])
    before_style, after_style = str(cfg["expected_old_style"]), str(cfg["new_style"])
    if cell.count(">" + after_value + "</td>") == 1 and cell.count(after_style) == 1:
        return current, "ALREADY_PRESENT"
    if cell.count(">" + before_value + "</td>") != 1 or cell.count(before_style) != 1:
        raise RuntimeError("target cell changed; refusing content overwrite")
    new_cell = cell.replace(before_style, after_style, 1).replace(
        ">" + before_value + "</td>", ">" + after_value + "</td>", 1
    )
    if new_cell == cell:
        raise RuntimeError("no table cell replacement made")
    updated_row = row[:thend] + row[thend:].replace(cell, new_cell, 1)
    updated = current[:start] + updated_row + current[end:]
    if len(re.findall(r"<td\b", updated_row)) != n:
        raise RuntimeError("target row column count changed")
    return updated, "UPDATE"


def apply_existing_table_cell_replacement(config_path: Path, cfg: dict[str, Any], auth: str):
    """An opt-in, content-only patch for draft or published posts with strict guards."""
    post_id = int(cfg["post_id"])
    slug = str(cfg["slug"])
    if post_id <= 0 or not slug or cfg.get("content_file") is None:
        raise RuntimeError("missing post identity or canonical content")
    before_counts = public_counts(auth)
    original = fetch_post_by_id(post_id, auth)
    if original.get("id") != post_id or original.get("slug") != slug:
        raise RuntimeError("post identity mismatch")
    if original.get("status") not in cfg.get("accept_status", ["draft"]):
        raise RuntimeError("post status differs; refusing patch")
    title = html.unescape(raw_field(original, "title"))
    if title != cfg["title"]:
        raise RuntimeError("post title changed; refusing patch")
    old = raw_field(original, "content")
    if cfg.get("salvage_marker") not in old or cfg.get("editorial_marker") not in old:
        raise RuntimeError("original post markers missing")
    updated, action = build_existing_table_cell_update(old, cfg)
    # The updated row should match the intended canonical GitHub source.
    wanted = (config_path.parent / cfg["content_file"]).read_text(encoding="utf-8")
    label = cfg["target_row_label"]
    idx = wanted.index(label) if wanted.count(label) == 1 else -1
    if idx < 0:
        raise RuntimeError("canonical target row absent")
    target_row = wanted[wanted.rfind("<tr>", 0, idx):wanted.find("</tr>", idx) + len("</tr>")]
    current_idx = updated.index(label)
    updated_row = updated[updated.rfind("<tr>", 0, current_idx):updated.find("</tr>", current_idx) + len("</tr>")]
    if target_row != updated_row:
        raise RuntimeError("saved target row does not match canonical GitHub row")
    if old.count('[blog_parts id="2843"]') != updated.count('[blog_parts id="2843"]'):
        raise RuntimeError("affiliate changed unexpectedly")
    keys = ("id", "slug", "status", "featured_media", "categories", "author")
    report_dir = Path("reports") / (slug + "-hud-correction")
    report_dir.mkdir(parents=True, exist_ok=True)
    print("TABLE_CELL_PREFLIGHT_OK", post_id, slug, original["status"], action, flush=True)
    latest = fetch_post_by_id(post_id, auth)
    if any(original.get(k) != latest.get(k) for k in keys) or (
        html.unescape(raw_field(latest, "title")) != title or raw_field(latest, "content") != old
    ):
        raise RuntimeError("concurrent WordPress edit; refusing table cell patch")
    if action == "UPDATE":
        response = post_json(f"{SITE_URL}/wp-json/wp/v2/posts/{post_id}", auth, {"content": updated})
        if response.get("id") != post_id or response.get("status") != original.get("status"):
            raise RuntimeError("WordPress patch response does not preserve post identity/status")
    after = fetch_post_by_id(post_id, auth)
    after_counts = public_counts(auth)
    if any(original.get(k) != after.get(k) for k in keys):
        raise RuntimeError("post identity or metadata changed")
    if html.unescape(raw_field(after, "title")) != title or raw_field(after, "content") != updated:
        raise RuntimeError("WordPress saved content differs from exact table cell correction")
    if before_counts != after_counts:
        raise RuntimeError("published page/post counts changed")
    result = {
        "action": action, "post_id": post_id, "slug": slug,
        "status": after["status"], "featured_media": after.get("featured_media"),
        "before_sha256": hashlib.sha256(old.encode()).hexdigest(),
        "after_sha256": hashlib.sha256(updated.encode()).hexdigest(),
        "old_cell_value": cfg["expected_old_value"], "new_cell_value": cfg["new_value"],
        "wordpress_write_count": int(action == "UPDATE"),
        "publish_count": 0, "before_public": before_counts, "after_public": after_counts
    }
    (report_dir/"result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print("TABLE_CELL_VERIFIED", json.dumps(result, ensure_ascii=False), flush=True)
    return result

def apply(config_path: Path):
    user = os.environ.get("TSURIKUE_WP_USER"); password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password: raise SystemExit("BLOCKED_MISSING_SECRETS")
    auth = auth_header(user, password)
    raw_cfg = json.loads(config_path.read_text(encoding="utf-8"))
    if raw_cfg.get("operation") == "insert_published_block":
        return apply_published_insertion(config_path, raw_cfg, auth)
    if raw_cfg.get("operation") == "replace_existing_table_cell":
        return apply_existing_table_cell_replacement(config_path, raw_cfg, auth)
    cfg, full = load_package(config_path)
    if cfg.get("operation") == "create": return apply_create(cfg, full, auth)
    return apply_update(cfg, full, auth)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--config", required=True); args = ap.parse_args(); apply(Path(args.config)); return 0
if __name__ == "__main__": raise SystemExit(main())
