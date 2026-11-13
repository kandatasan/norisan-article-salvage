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


def build_published_affiliate_swap(current: str, cfg: dict[str, Any]) -> tuple[str, str]:
    """Replace one verified banner shortcode with an existing managed button."""
    old_sc = str(cfg["old_shortcode"])
    new_sc = str(cfg["new_shortcode"])
    if old_sc != '[blog_parts id="2843"]' or new_sc != '[blog_parts id="4172"]':
        raise RuntimeError("only the verified Gulliver banner -> managed button swap is allowed")
    old_count, new_count = current.count(old_sc), current.count(new_sc)
    expected_heading = str(cfg["nearest_heading"])
    if old_count == 0 and new_count == 1:
        new_copy = str(cfg.get("new_copy") or "")
        if new_copy and current.count(new_copy) != 1:
            raise RuntimeError("already swapped but microcopy is inconsistent")
        return current, "ALREADY_PRESENT"
    if old_count != 1 or new_count != 0:
        raise RuntimeError(f"unexpected Gulliver shortcode counts {old_count}/{new_count}")
    at = current.index(old_sc)
    headings = list(re.finditer(r"<h[23]\b[^>]*>.*?</h[23]>", current[:at], re.S))
    if not headings:
        raise RuntimeError("heading before Gulliver CTA not found")
    nearest = html.unescape(re.sub(r"<[^>]+>", "", headings[-1].group(0)).strip())
    if nearest != expected_heading:
        raise RuntimeError(f"CTA section drifted: {nearest!r} != {expected_heading!r}")
    old_copy = str(cfg.get("old_copy") or "")
    new_copy = str(cfg.get("new_copy") or "")
    if bool(old_copy) != bool(new_copy):
        raise RuntimeError("microcopy old/new must be paired")
    updated = current
    if old_copy:
        if current.count(old_copy) != 1 or new_copy in current:
            raise RuntimeError("microcopy is missing or already changed")
        copy_at = current.index(old_copy)
        if not 0 < at - copy_at <= 350:
            raise RuntimeError("microcopy is not immediately before the banner")
        updated = updated.replace(old_copy, new_copy, 1)
    updated = updated.replace(old_sc, new_sc, 1)
    if updated.count(old_sc) != 0 or updated.count(new_sc) != 1:
        raise RuntimeError("shortcode replacement did not produce exactly one managed button")
    if updated.count("<!-- wp:") != current.count("<!-- wp:"):
        raise RuntimeError("Gutenberg blocks unexpectedly modified")
    if re.findall(r"\bwp-image-\d+\b", updated) != re.findall(r"\bwp-image-\d+\b", current):
        raise RuntimeError("inline images unexpectedly changed")
    if re.findall(r'https?://[^\s"<]+', updated) != re.findall(r'https?://[^\s"<]+', current):
        raise RuntimeError("article URLs unexpectedly changed")
    return updated, "UPDATE"


def apply_published_affiliate_swap(cfg: dict[str, Any], auth: str):
    """Content-only, guarded per-article Gulliver conversion improvement."""
    pid = int(cfg["post_id"])
    before_counts = public_counts(auth)
    original = fetch_post_by_id(pid, auth)
    title = html.unescape(raw_field(original, "title"))
    if (original.get("id"), original.get("slug"), original.get("status")) != (
        pid, cfg["slug"], "publish"
    ):
        raise RuntimeError("published affiliate target identity/status mismatch")
    if title != cfg["title"]:
        raise RuntimeError("title changed since the article was audited")
    if int(original.get("featured_media") or 0) != int(cfg["expected_featured_media"]):
        raise RuntimeError("featured media differs from the WordPress export")
    keys = ("id", "slug", "status", "featured_media", "categories", "author")
    old = raw_field(original, "content")
    updated, action = build_published_affiliate_swap(old, cfg)
    old_sha = hashlib.sha256(old.encode()).hexdigest()
    new_sha = hashlib.sha256(updated.encode()).hexdigest()
    report_dir = Path("reports") / (cfg["slug"] + "-gulliver-cta-20261104")
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir/"preflight.json").write_text(json.dumps({
        "post_id": pid, "slug": cfg["slug"], "action": action,
        "old_sha256": old_sha, "new_sha256": new_sha,
        "old_banner_count": old.count(cfg["old_shortcode"]),
        "new_button_count": updated.count(cfg["new_shortcode"])
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    latest = fetch_post_by_id(pid, auth)
    if any(latest.get(k) != original.get(k) for k in keys) or (
        html.unescape(raw_field(latest, "title")) != title or raw_field(latest, "content") != old
    ):
        raise RuntimeError("concurrent WordPress edit; refusing affiliate swap")
    wrote = False
    try:
        if action == "UPDATE":
            response = post_json(f"{SITE_URL}/wp-json/wp/v2/posts/{pid}", auth, {"content": updated})
            wrote = True
            if response.get("id") != pid or response.get("status") != "publish":
                raise RuntimeError("WordPress response changed post identity/status")
        after = fetch_post_by_id(pid, auth)
        after_counts = public_counts(auth)
        if any(after.get(k) != original.get(k) for k in keys):
            raise RuntimeError("WordPress metadata drifted during affiliate swap")
        if html.unescape(raw_field(after, "title")) != title or raw_field(after, "content") != updated:
            raise RuntimeError("WordPress did not save the exact targeted affiliate change")
        if before_counts != after_counts:
            raise RuntimeError("published post/page counts changed")
        result = {
            "action": action, "post_id": pid, "slug": cfg["slug"],
            "status": "publish", "title": title,
            "featured_media": original.get("featured_media"),
            "old_sha256": old_sha, "new_sha256": new_sha,
            "banner_count_after": updated.count(cfg["old_shortcode"]),
            "managed_button_count_after": updated.count(cfg["new_shortcode"]),
            "wordpress_write_count": int(action == "UPDATE")
        }
        (report_dir/"result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        (report_dir/"summary.md").write_text(
            f"# Gulliver CTA {cfg['slug']}\n\n- action: {action}\n- post_id: {pid}\n"
            f"- status: publish\n- featured media: {original.get('featured_media')}\n"
            f"- old banner: 1 → 0 (or already 0)\n- managed button: 0 → 1 (or already 1)\n"
            f"- before: {old_sha}\n- after: {new_sha}\n", encoding="utf-8")
        print("GULLIVER_CTA_VERIFIED", json.dumps(result, ensure_ascii=False), flush=True)
        return result
    except Exception:
        if wrote:
            try:
                now = fetch_post_by_id(pid, auth)
                if raw_field(now, "content") == updated and all(
                    now.get(k) == original.get(k) for k in keys
                ):
                    post_json(f"{SITE_URL}/wp-json/wp/v2/posts/{pid}", auth, {"content": old})
                    print("GULLIVER_CTA_ROLLBACK", pid, flush=True)
                else:
                    print("GULLIVER_CTA_ROLLBACK_SKIPPED_DRIFT", pid, flush=True)
            except Exception as error:
                print("GULLIVER_CTA_ROLLBACK_FAILED", repr(error), flush=True)
        raise



def build_published_gulliver_context_ctas(current: str, cfg: dict[str, Any]) -> tuple[str, str]:
    """Add one quiet banner plus 0–2 contextual buttons to an existing published article."""
    banner = '[blog_parts id="2843"]'
    button = '[blog_parts id="4172"]'
    slots = cfg["button_slots"]
    if not isinstance(slots, list) or len(slots) > 2:
        raise RuntimeError("only zero to two extra buttons allowed (max three total)")
    if len(set(x["before_heading"] for x in slots)) != len(slots):
        raise RuntimeError("button anchors not unique")
    if any(not x.get("copy") or "<" in x["copy"] or ">" in x["copy"] for x in slots):
        raise RuntimeError("invalid CTA copy")
    if cfg["banner_before_heading"] in {x["before_heading"] for x in slots}:
        raise RuntimeError("banner and button cannot be placed directly together")

    if current.count(banner) == 1 and current.count(button) == 1 + len(slots):
        if all(current.count(x["copy"]) == 1 for x in slots):
            return current, "ALREADY_PRESENT"
        raise RuntimeError("affiliate counts match but contextual microcopy drifted")
    if current.count(banner) != 0 or current.count(button) != 1:
        raise RuntimeError("expected one managed button and no banner before rebalance")

    def insert_before_heading(source: str, heading_text: str, fragment: str) -> str:
        pat = re.compile(
            r'<!-- wp:heading(?: [^\n]*)? -->\s*<h2\b[^>]*>.*?</h2>\s*<!-- /wp:heading -->',
            re.S
        )
        matches = []
        for m in pat.finditer(source):
            text_only = html.unescape(re.sub(r"<[^>]+>", "", m.group(0)).strip())
            if text_only == heading_text:
                matches.append(m)
        if len(matches) != 1:
            raise RuntimeError(f"heading anchor count is {len(matches)}: {heading_text!r}")
        pos = matches[0].start()
        return source[:pos] + fragment + "\n\n" + source[pos:]

    updated = insert_before_heading(
        current, cfg["banner_before_heading"],
        '<!-- wp:shortcode -->\n' + banner + '\n<!-- /wp:shortcode -->'
    )
    for slot in slots:
        fragment = ('<!-- wp:paragraph -->\n<p>' + slot["copy"] +
                    '</p>\n<!-- /wp:paragraph -->\n\n'
                    '<!-- wp:shortcode -->\n' + button + '\n<!-- /wp:shortcode -->')
        if slot["copy"] in updated:
            raise RuntimeError("CTA microcopy already exists")
        updated = insert_before_heading(updated, slot["before_heading"], fragment)
    if updated.count(banner) != 1 or updated.count(button) != 1 + len(slots):
        raise RuntimeError("Gulliver CTA counts after rebalance are invalid")
    if updated.count(button) > 3:
        raise RuntimeError("more than three Gulliver buttons")
    if re.findall(r"\bwp-image-\d+\b", updated) != re.findall(r"\bwp-image-\d+\b", current):
        raise RuntimeError("WordPress media IDs changed")
    if re.findall(r'https?://[^\s"<]+', updated) != re.findall(r'https?://[^\s"<]+', current):
        raise RuntimeError("article links changed")
    if updated.count("<h2") != current.count("<h2") or updated.count("<h3") != current.count("<h3"):
        raise RuntimeError("article headings changed")
    return updated, "UPDATE"


def apply_published_gulliver_context_ctas(cfg: dict[str, Any], auth: str):
    """Guarded WordPress-only content insertion; preserve every existing article block."""
    pid = int(cfg["post_id"])
    before_counts = public_counts(auth)
    original = fetch_post_by_id(pid, auth)
    title = html.unescape(raw_field(original, "title"))
    if (original.get("id"), original.get("slug"), original.get("status")) != (
        pid, cfg["slug"], "publish"
    ):
        raise RuntimeError("published Gulliver target identity/status mismatch")
    if title != cfg["title"]:
        raise RuntimeError("post title drifted")
    if int(original.get("featured_media") or 0) != int(cfg["expected_featured_media"]):
        raise RuntimeError("post thumbnail drifted")
    old = raw_field(original, "content")
    expected_sha = cfg["expected_current_content_sha256"]
    action = "UPDATE"
    if hashlib.sha256(old.encode()).hexdigest() != expected_sha:
        # Only allow an exact, already-applied result; do not overwrite later WP edits.
        if old.count('[blog_parts id="2843"]') == 1 and old.count('[blog_parts id="4172"]') == 1 + len(cfg["button_slots"]) and all(
            old.count(x["copy"]) == 1 for x in cfg["button_slots"]
        ):
            action = "ALREADY_PRESENT"
            updated = old
        else:
            raise RuntimeError("post content differs from verified previous CTA release")
    else:
        updated, action = build_published_gulliver_context_ctas(old, cfg)
    keys = ("id", "slug", "status", "featured_media", "categories", "author")
    newest = fetch_post_by_id(pid, auth)
    if any(newest.get(k) != original.get(k) for k in keys) or (
        html.unescape(raw_field(newest, "title")) != title or raw_field(newest, "content") != old
    ):
        raise RuntimeError("WordPress content or metadata changed between reads")
    wrote = False
    report_dir = Path("reports") / (cfg["slug"] + "-gulliver-context-20261104")
    report_dir.mkdir(parents=True, exist_ok=True)
    try:
        if action == "UPDATE":
            response = post_json(f"{SITE_URL}/wp-json/wp/v2/posts/{pid}", auth, {"content": updated})
            wrote = True
            if response.get("id") != pid or response.get("slug") != cfg["slug"] or response.get("status") != "publish":
                raise RuntimeError("WordPress update response invalid")
        after = fetch_post_by_id(pid, auth)
        after_counts = public_counts(auth)
        if any(after.get(k) != original.get(k) for k in keys) or (
            html.unescape(raw_field(after, "title")) != title
        ):
            raise RuntimeError("post metadata changed after contextual CTA insertion")
        if raw_field(after, "content") != updated:
            raise RuntimeError("WordPress saved content is not the intended insertion")
        if before_counts != after_counts:
            raise RuntimeError("published post/page totals changed")
        result = {
            "action": action, "post_id": pid, "slug": cfg["slug"],
            "title": title, "status": "publish",
            "featured_media": after.get("featured_media"),
            "banner_count": updated.count('[blog_parts id="2843"]'),
            "button_count": updated.count('[blog_parts id="4172"]'),
            "old_sha256": hashlib.sha256(old.encode()).hexdigest(),
            "new_sha256": hashlib.sha256(updated.encode()).hexdigest(),
            "wordpress_write_count": int(wrote),
        }
        (report_dir/"result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        (report_dir/"summary.md").write_text(
            f"# Gulliver context CTA {cfg['slug']}\n\n"
            f"- action: {action}\n- post_id: {pid}\n- status: publish\n"
            f"- banner: {result['banner_count']}, buttons: {result['button_count']}\n"
            f"- featured_media: {after.get('featured_media')}\n"
            f"- old SHA: {result['old_sha256']}\n- new SHA: {result['new_sha256']}\n",
            encoding="utf-8"
        )
        print("GULLIVER_CONTEXT_CTA_VERIFIED", json.dumps(result, ensure_ascii=False), flush=True)
        return result
    except Exception:
        if wrote:
            try:
                now = fetch_post_by_id(pid, auth)
                if raw_field(now, "content") == updated and all(
                    now.get(k) == original.get(k) for k in keys
                ):
                    post_json(f"{SITE_URL}/wp-json/wp/v2/posts/{pid}", auth, {"content": old})
                    print("GULLIVER_CONTEXT_CTA_ROLLBACK", pid, flush=True)
                else:
                    print("GULLIVER_CONTEXT_CTA_ROLLBACK_SKIPPED_DRIFT", pid, flush=True)
            except Exception as error:
                print("GULLIVER_CONTEXT_CTA_ROLLBACK_FAILED", repr(error), flush=True)
        raise



def build_published_gulliver_extra_buttons(current: str, cfg: dict[str, Any]) -> tuple[str, str]:
    """Insert up to two context-specific Gulliver buttons without touching the small banner."""
    banner = '[blog_parts id="2843"]'
    button = '[blog_parts id="4172"]'
    slots = cfg["button_slots"]
    if not isinstance(slots, list) or not 1 <= len(slots) <= 2:
        raise RuntimeError("one or two contextual Gulliver buttons required")
    anchors = [str(x["before_heading"]) for x in slots]
    copies = [str(x["copy"]) for x in slots]
    if len(set(anchors)) != len(anchors) or len(set(copies)) != len(copies):
        raise RuntimeError("duplicate anchors or copy")
    if any(not copy or "<" in copy or ">" in copy for copy in copies):
        raise RuntimeError("invalid CTA copy")
    if current.count(banner) != 1:
        raise RuntimeError("existing small Gulliver banner must remain exactly once")
    if current.count(button) == len(slots):
        if all(current.count(copy) == 1 for copy in copies):
            return current, "ALREADY_PRESENT"
        raise RuntimeError("Gulliver buttons exist with unexpected copy")
    if current.count(button) != 0:
        raise RuntimeError("article has a pre-existing Gulliver button; review manually")

    heading_pattern = re.compile(
        r'<!-- wp:heading(?: [^\n]*)? -->\s*<h2\b[^>]*>.*?</h2>\s*<!-- /wp:heading -->',
        re.S
    )
    updated = current
    inserted = []
    for slot in slots:
        heading = str(slot["before_heading"])
        copy = str(slot["copy"])
        if copy in updated:
            raise RuntimeError("microcopy already present")
        matches = [
            m for m in heading_pattern.finditer(updated)
            if html.unescape(re.sub(r"<[^>]+>", "", m.group(0)).strip()) == heading
        ]
        if len(matches) != 1:
            raise RuntimeError(f"heading anchor count unexpected {heading!r}: {len(matches)}")
        insert_at = matches[0].start()
        shortcode_at = updated.index(banner)
        # Do not stack the new button directly on an existing banner.
        if abs(insert_at - shortcode_at) < 700:
            raise RuntimeError("contextual button would be too close to the small banner")
        injected = (
            '<!-- wp:paragraph -->\n<p>' + html.escape(copy, quote=False) +
            '</p>\n<!-- /wp:paragraph -->\n\n'
            '<!-- wp:shortcode -->\n' + button + '\n<!-- /wp:shortcode -->'
        )
        updated = updated[:insert_at] + injected + "\n\n" + updated[insert_at:]
        inserted.append(injected)

    if updated.count(button) != len(slots) or updated.count(banner) != 1:
        raise RuntimeError("button/banner count changed unexpectedly")
    if updated.count(button) > 3:
        raise RuntimeError("more than three Gulliver buttons")
    if updated.count("<!-- wp:") != current.count("<!-- wp:") + len(slots)*2:
        raise RuntimeError("unexpected Gutenberg block count")
    if updated.count("<h2") != current.count("<h2") or updated.count("<h3") != current.count("<h3"):
        raise RuntimeError("article headings were modified")
    if re.findall(r"\bwp-image-\d+\b", updated) != re.findall(r"\bwp-image-\d+\b", current):
        raise RuntimeError("inline WordPress media changed")
    if re.findall(r"https?://[^\s\"<]+", updated) != re.findall(r"https?://[^\s\"<]+", current):
        raise RuntimeError("article URLs changed")
    for injected in reversed(inserted):
        if updated.count(injected + "\n\n") != 1:
            raise RuntimeError("inserted fragment is not unique")
        updated = updated.replace(injected + "\n\n", "", 1)
    if updated != current:
        raise RuntimeError("not a pure addition; original content would be changed")
    updated = current
    for slot in slots:
        heading = str(slot["before_heading"])
        matches = [
            m for m in heading_pattern.finditer(updated)
            if html.unescape(re.sub(r"<[^>]+>", "", m.group(0)).strip()) == heading
        ]
        pos = matches[0].start()
        block = ('<!-- wp:paragraph -->\n<p>' + html.escape(slot["copy"], quote=False) +
                 '</p>\n<!-- /wp:paragraph -->\n\n<!-- wp:shortcode -->\n' +
                 button + '\n<!-- /wp:shortcode -->')
        updated = updated[:pos] + block + "\n\n" + updated[pos:]
    return updated, "UPDATE"


def apply_published_gulliver_extra_buttons(cfg: dict[str, Any], auth: str):
    """Safely add contextual affiliate buttons to a published post with an existing banner."""
    post_id = int(cfg["post_id"])
    before_counts = public_counts(auth)
    original = fetch_post_by_id(post_id, auth)
    old = raw_field(original, "content")
    original_title = html.unescape(raw_field(original, "title"))
    if (original.get("id"), original.get("slug"), original.get("status")) != (
        post_id, cfg["slug"], "publish"
    ):
        raise RuntimeError("WordPress post ID/slug/status drifted")
    if original_title != cfg["title"]:
        raise RuntimeError("WordPress post title drifted")
    if int(original.get("featured_media") or 0) != int(cfg["expected_featured_media"]):
        raise RuntimeError("WordPress featured media drifted")
    original_sha = hashlib.sha256(old.encode()).hexdigest()
    if original_sha != cfg["expected_current_content_sha256"]:
        if old.count('[blog_parts id="2843"]') == 1 and old.count('[blog_parts id="4172"]') == len(cfg["button_slots"]) and all(
            old.count(str(x["copy"])) == 1 for x in cfg["button_slots"]
        ):
            updated, action = old, "ALREADY_PRESENT"
        else:
            raise RuntimeError("WordPress content has changed since the verified export; refuse overwrite")
    else:
        updated, action = build_published_gulliver_extra_buttons(old, cfg)

    keys = ("id", "slug", "status", "featured_media", "categories", "author")
    latest = fetch_post_by_id(post_id, auth)
    if any(latest.get(k) != original.get(k) for k in keys) or (
        html.unescape(raw_field(latest, "title")) != original_title or
        raw_field(latest, "content") != old
    ):
        raise RuntimeError("WordPress edit occurred during the preflight")
    wrote = False
    report_dir = Path("reports") / f"{cfg['slug']}-gulliver-extra-20261104"
    report_dir.mkdir(parents=True, exist_ok=True)
    try:
        if action == "UPDATE":
            response = post_json(f"{SITE_URL}/wp-json/wp/v2/posts/{post_id}", auth, {"content":updated})
            wrote = True
            if response.get("id") != post_id or response.get("slug") != cfg["slug"] or response.get("status") != "publish":
                raise RuntimeError("WordPress response identity/status mismatch")
        after = fetch_post_by_id(post_id, auth)
        after_counts = public_counts(auth)
        if any(after.get(k) != original.get(k) for k in keys):
            raise RuntimeError("WordPress metadata changed during Gulliver CTA update")
        if html.unescape(raw_field(after, "title")) != original_title or raw_field(after, "content") != updated:
            raise RuntimeError("WordPress did not save exact target content")
        if after_counts != before_counts:
            raise RuntimeError("public post/page count changed unexpectedly")
        result = {
            "action": action, "post_id":post_id, "slug":cfg["slug"],
            "title": original_title, "status": "publish",
            "featured_media":after.get("featured_media"),
            "banner_count":updated.count('[blog_parts id="2843"]'),
            "button_count":updated.count('[blog_parts id="4172"]'),
            "ctn_count": len(re.findall(r'\[blog_parts id="(?:2184|3788)"\]',updated)),
            "old_sha256":original_sha,
            "new_sha256":hashlib.sha256(updated.encode()).hexdigest(),
            "wordpress_write_count":int(wrote)
        }
        (report_dir/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        (report_dir/"summary.md").write_text(
            f"# Gulliver extra buttons: {cfg['slug']}\n\n"
            f"- action: {action}\n- post_id: {post_id}\n- status: publish\n"
            f"- banner_count: {result['banner_count']}\n- button_count: {result['button_count']}\n"
            f"- ctn_count: {result['ctn_count']}\n- featured_media: {after.get('featured_media')}\n"
            f"- before_sha: {original_sha}\n- after_sha: {result['new_sha256']}\n",
            encoding="utf-8"
        )
        print("GULLIVER_EXTRA_BUTTON_VERIFIED", json.dumps(result,ensure_ascii=False),flush=True)
        return result
    except Exception:
        if wrote:
            try:
                current = fetch_post_by_id(post_id, auth)
                if raw_field(current,"content") == updated and all(
                    current.get(k) == original.get(k) for k in keys
                ):
                    post_json(f"{SITE_URL}/wp-json/wp/v2/posts/{post_id}",auth,{"content":old})
                    print("GULLIVER_EXTRA_BUTTON_ROLLBACK",post_id,flush=True)
                else:
                    print("GULLIVER_EXTRA_BUTTON_ROLLBACK_SKIPPED_DRIFT",post_id,flush=True)
            except Exception as rollback_error:
                print("GULLIVER_EXTRA_BUTTON_ROLLBACK_FAILED",repr(rollback_error),flush=True)
        raise



def build_published_affiliate_copy_replacements(current: str, cfg: dict[str, Any]) -> str:
    """A text-only, fixed-before/after revision of published WordPress content."""
    edits = cfg["replacements"]
    if not isinstance(edits, list) or not 1 <= len(edits) <= 8:
        raise RuntimeError("affiliate copy revision requires 1-8 explicit replacements")
    result = current
    old_values = set()
    new_values = set()
    for index, edit in enumerate(edits):
        before = str(edit["before"])
        after = str(edit["after"])
        if not before or not after or before == after:
            raise RuntimeError(f"empty/unchanged affiliate copy edit {index}")
        if any(char in before + after for char in "<>&[]"):
            raise RuntimeError(f"affiliate copy edit {index} contains HTML or shortcode syntax")
        if before in old_values or after in new_values:
            raise RuntimeError("duplicate affiliate copy replacement")
        old_values.add(before); new_values.add(after)
        if result.count(before) != 1 or after in result:
            raise RuntimeError(f"affiliate copy source drifted, edit {index}")
        result = result.replace(before, after, 1)
    # Every edit must be reversible as an exact text-only change.
    reversed_result = result
    for edit in reversed(edits):
        if reversed_result.count(edit["after"]) != 1:
            raise RuntimeError("affiliate copy reverse-match is not unique")
        reversed_result = reversed_result.replace(edit["after"], edit["before"], 1)
    if reversed_result != current:
        raise RuntimeError("affiliate copy is not a pure, reversible replacement")
    # WordPress block structure, all HTML tags (and attributes), links and ads are immutable.
    if re.findall(r"<[^>]*>", result, flags=re.S) != re.findall(r"<[^>]*>", current, flags=re.S):
        raise RuntimeError("affiliate copy unexpectedly modified HTML or Gutenberg blocks")
    if re.findall(r'\[blog_parts id=["\x27]\d+["\x27]\]', result) != re.findall(
        r'\[blog_parts id=["\x27]\d+["\x27]\]', current
    ):
        raise RuntimeError("affiliate shortcodes changed")
    if hashlib.sha256(result.encode()).hexdigest() != cfg["expected_after_sha256"]:
        raise RuntimeError("affiliate copy target hash does not match reviewed version")
    return result


def apply_published_affiliate_copy_replacements(cfg: dict[str, Any], auth: str):
    """One safe published WordPress update, only if its exact audited body is still live."""
    post_id = int(cfg["post_id"])
    counts_before = public_counts(auth)
    original = fetch_post_by_id(post_id, auth)
    expected_status = "publish"
    title = html.unescape(raw_field(original, "title"))
    if (original.get("id"), original.get("slug"), original.get("status")) != (
        post_id, cfg["slug"], expected_status
    ):
        raise RuntimeError("affiliate copy target ID/slug/status mismatch")
    if title != cfg["title"]:
        raise RuntimeError("affiliate copy target title mismatch")
    if int(original.get("featured_media") or 0) != int(cfg["expected_featured_media"]):
        raise RuntimeError("affiliate copy target featured media mismatch")
    old = raw_field(original, "content")
    old_sha = hashlib.sha256(old.encode()).hexdigest()
    if old_sha == cfg["expected_after_sha256"]:
        # Repeated Actions runs are read-only; verify the intended copy exists.
        if not all(old.count(edit["after"]) == 1 for edit in cfg["replacements"]):
            raise RuntimeError("already-applied article does not contain expected copy")
        updated, action = old, "ALREADY_PRESENT"
    elif old_sha == cfg["expected_current_content_sha256"]:
        updated = build_published_affiliate_copy_replacements(old, cfg)
        action = "UPDATE"
    else:
        raise RuntimeError("published article changed since the reviewed copy; refuse overwrite")

    keys = ("id", "slug", "status", "featured_media", "categories", "author")
    latest = fetch_post_by_id(post_id, auth)
    if any(latest.get(key) != original.get(key) for key in keys) or (
        html.unescape(raw_field(latest, "title")) != title or raw_field(latest, "content") != old
    ):
        raise RuntimeError("WordPress article changed during affiliate copy preflight")

    report_dir = Path("reports") / (cfg["slug"] + "-gulliver-copy-20261104")
    report_dir.mkdir(parents=True, exist_ok=True)
    wrote = False
    try:
        if action == "UPDATE":
            response = post_json(
                f"{SITE_URL}/wp-json/wp/v2/posts/{post_id}", auth, {"content": updated}
            )
            wrote = True
            if (response.get("id"), response.get("slug"), response.get("status")) != (
                post_id, cfg["slug"], expected_status
            ):
                raise RuntimeError("WordPress affiliate copy response did not preserve identity")
        after = fetch_post_by_id(post_id, auth)
        counts_after = public_counts(auth)
        if any(after.get(key) != original.get(key) for key in keys):
            raise RuntimeError("article metadata changed during affiliate copy update")
        if html.unescape(raw_field(after, "title")) != title:
            raise RuntimeError("article title changed during affiliate copy update")
        if raw_field(after, "content") != updated:
            raise RuntimeError("saved article differs from exact reviewed affiliate copy")
        if counts_before != counts_after:
            raise RuntimeError("published post/page count unexpectedly changed")
        if hashlib.sha256(raw_field(after, "content").encode()).hexdigest() != cfg["expected_after_sha256"]:
            raise RuntimeError("WordPress final affiliate copy hash mismatch")
        if action == "UPDATE":
            rendered = (after.get("content") or {}).get("rendered", "")
            # Replacements in microcopy can be split by markup; raw content is the source of truth.
            if not rendered:
                raise RuntimeError("WordPress rendered content empty")
        result = {
            "action": action, "post_id": post_id, "slug": cfg["slug"], "status": expected_status,
            "title": title, "featured_media": after.get("featured_media"),
            "copy_replacements": len(cfg["replacements"]),
            "gulliver_banner_count": updated.count('[blog_parts id="2843"]'),
            "gulliver_button_count": updated.count('[blog_parts id="4172"]'),
            "old_sha256": old_sha,
            "new_sha256": cfg["expected_after_sha256"],
            "wordpress_write_count": int(wrote),
            "published_before": counts_before, "published_after": counts_after,
        }
        (report_dir/"result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8"
        )
        (report_dir/"summary.md").write_text(
            f"# Gulliver benefit/copy update: {cfg['slug']}\n\n"
            f"- action: {action}\n- post_id: {post_id}\n- status: publish\n"
            f"- copy replacements: {len(cfg['replacements'])}\n"
            f"- small banner: {result['gulliver_banner_count']}, buttons: {result['gulliver_button_count']}\n"
            f"- featured_media: {after.get('featured_media')}\n"
            f"- source_sha: {old_sha}\n- saved_sha: {result['new_sha256']}\n",
            encoding="utf-8"
        )
        print("GULLIVER_COPY_VERIFIED", json.dumps(result, ensure_ascii=False), flush=True)
        return result
    except Exception:
        if wrote:
            try:
                now = fetch_post_by_id(post_id, auth)
                if raw_field(now, "content") == updated and all(
                    now.get(key) == original.get(key) for key in keys
                ):
                    post_json(f"{SITE_URL}/wp-json/wp/v2/posts/{post_id}", auth, {"content": old})
                    print("GULLIVER_COPY_ROLLBACK", post_id, flush=True)
                else:
                    print("GULLIVER_COPY_ROLLBACK_SKIPPED_DRIFT", post_id, flush=True)
            except Exception as rollback_error:
                print("GULLIVER_COPY_ROLLBACK_FAILED", repr(rollback_error), flush=True)
        raise



def build_ux_purchase_funnel_target(current: str, target: dict[str, Any], funnel: str) -> tuple[str, str]:
    """Replace one verified legacy UX purchase CTA with 4505 + a native copy of blog-part 4507."""
    marker = str(target["marker"])
    if marker in current:
        if current.count(marker) == 1 and '[blog_parts id="4505"]' in current and 'swell-block-button -html green_' in current:
            return current, "ALREADY_PRESENT"
        raise RuntimeError(f"UX funnel marker drifted for {target['slug']}")

    source_sha = hashlib.sha256(current.encode()).hexdigest()
    if source_sha != str(target["expected_current_content_sha256"]):
        raise RuntimeError(f"UX funnel source hash drifted for {target['slug']}: {source_sha}")

    anchor = str(target["anchor_heading"])
    heading_pattern = re.compile(
        r'<!-- wp:heading(?: [^\n]*)? -->\s*<h2[^>]*>\s*' + re.escape(anchor) +
        r'\s*</h2>\s*<!-- /wp:heading -->',
        re.S,
    )
    headings = list(heading_pattern.finditer(current))
    if len(headings) != 1:
        raise RuntimeError(f"UX funnel anchor heading drifted for {target['slug']}: {len(headings)}")
    heading_start = headings[0].start()
    prefix = current[:heading_start]

    mode = str(target["mode"])
    removed_native_button_count = 0
    if mode == "legacy_gulliver_triplet":
        pattern = re.compile(
            r'<!-- wp:html -->\s*'
            r'<div class="tsq-gulliver-micro-20261014 top".*?<!-- /wp:html -->\s*'
            r'<!-- wp:paragraph -->\s*'
            r'<p><a href="https://px\.a8\.net/svt/ejp\?a8mat=4B65SD\+8DUSHE\+9QU\+NVHCY"'
            r'.*?<!-- /wp:paragraph -->\s*'
            r'<!-- wp:html -->\s*'
            r'<div class="tsq-gulliver-micro-20261014 bottom".*?<!-- /wp:html -->\s*$',
            re.S,
        )
        matches = list(pattern.finditer(prefix))
        if len(matches) != 1:
            raise RuntimeError(f"legacy Gulliver triplet drifted for {target['slug']}: {len(matches)}")
        m = matches[0]
        source = m.group(0).rstrip()
        removed_native_button_count = source.count('swell-block-button -html green_')
        required = str(target.get("legacy_top_phrase") or "")
        if required and required not in source:
            raise RuntimeError(f"legacy Gulliver copy drifted for {target['slug']}")
        start, end = m.start(), m.end()
    elif mode == "legacy_gulliver_native_triplet":
        pattern = re.compile(
            r'<!-- wp:html -->\s*'
            r'<div class="tsq-gulliver-micro-20261014 top".*?<!-- /wp:html -->\s*'
            r'<!-- wp:loos/button(?: [^\n]*)? -->\s*'
            r'<div class="swell-block-button -html green_[^"]*".*?<!-- /wp:loos/button -->\s*'
            r'<!-- wp:html -->\s*'
            r'<div class="tsq-gulliver-micro-20261014 bottom".*?<!-- /wp:html -->\s*$',
            re.S,
        )
        matches = list(pattern.finditer(prefix))
        if len(matches) != 1:
            raise RuntimeError(
                f"legacy native Gulliver triplet drifted for {target['slug']}: {len(matches)}"
            )
        m = matches[0]
        source = m.group(0).rstrip()
        removed_native_button_count = source.count('swell-block-button -html green_')
        required = str(target.get("legacy_top_phrase") or "")
        if required and required not in source:
            raise RuntimeError(f"legacy native Gulliver copy drifted for {target['slug']}")
        start, end = m.start(), m.end()
    elif mode == "legacy_shortcode_4172":
        paragraph = str(target["legacy_paragraph"])
        source = (
            '<!-- wp:paragraph -->\n<p>' + paragraph + '</p>\n<!-- /wp:paragraph -->\n\n'
            '<!-- wp:shortcode -->\n[blog_parts id="4172"]\n<!-- /wp:shortcode -->'
        )
        removed_native_button_count = source.count('swell-block-button -html green_')
        tail = re.search(re.escape(source) + r'\s*$', prefix, re.S)
        if not tail:
            raise RuntimeError(f"legacy 4172 block drifted for {target['slug']}")
        start, end = tail.start(), tail.end()
    elif mode == "insert_before_block":
        anchor_block = str(target["anchor_block"])
        if current.count(anchor_block) != 1:
            raise RuntimeError(
                f"UX funnel anchor block drifted for {target['slug']}: {current.count(anchor_block)}"
            )
        start = current.find(anchor_block)
        end = start
    elif mode == "insert_before_heading":
        before_heading = str(target["before_heading"])
        heading_level = int(target.get("before_heading_level") or 2)
        if heading_level not in (2, 3):
            raise RuntimeError("UX funnel before_heading_level must be 2 or 3")
        heading_before_pattern = re.compile(
            r'<!-- wp:heading(?: [^\n]*)? -->\s*<h' + str(heading_level) + r'[^>]*>\s*' +
            re.escape(before_heading) + r'\s*</h' + str(heading_level) + r'>\s*<!-- /wp:heading -->',
            re.S,
        )
        before_matches = list(heading_before_pattern.finditer(current))
        if len(before_matches) != 1:
            raise RuntimeError(
                f"UX funnel before heading drifted for {target['slug']}: {len(before_matches)}"
            )
        start = before_matches[0].start()
        end = start
    else:
        raise RuntimeError(f"unknown UX funnel replacement mode: {mode}")

    lead = str(target.get("lead_paragraph") or "").strip()
    pieces = [marker]
    if lead:
        pieces.append(
            '<!-- wp:paragraph -->\n<p><strong>' + html.escape(lead, quote=False) +
            '</strong></p>\n<!-- /wp:paragraph -->'
        )
    pieces += [
        '<!-- wp:shortcode -->\n[blog_parts id="4505"]\n<!-- /wp:shortcode -->',
        funnel.strip(),
    ]
    replacement = "\n\n".join(pieces)
    updated = current[:start] + replacement + "\n\n" + current[end:]

    if updated.count(marker) != 1:
        raise RuntimeError("UX funnel marker count invalid")
    if updated.count('[blog_parts id="4505"]') != current.count('[blog_parts id="4505"]') + 1:
        raise RuntimeError("UX price checker count did not increase by one")
    expected_native_buttons = (
        current.count('swell-block-button -html green_') + 1 - removed_native_button_count
    )
    if updated.count('swell-block-button -html green_') != expected_native_buttons:
        raise RuntimeError(
            f"native SWELL button count unexpected: {updated.count('swell-block-button -html green_')} != {expected_native_buttons}"
        )
    if updated.count('a8mat=4B65SD+8DUSHE+9QU+NVHCY') < 2:
        raise RuntimeError("Gulliver A8 link/pixel missing after replacement")
    return updated, "UPDATE"


def apply_published_ux_purchase_funnels(config_path: Path, cfg: dict[str, Any], auth: str):
    """Guarded multi-post UX funnel replacement. Preflight all posts before the first write."""
    funnel = (config_path.parent / cfg["funnel_file"]).read_text(encoding="utf-8").strip()
    expected_funnel_sha = str(cfg["expected_funnel_sha256"])
    actual_funnel_sha = hashlib.sha256(funnel.encode()).hexdigest()
    if actual_funnel_sha != expected_funnel_sha:
        raise RuntimeError(f"4507 copy source hash mismatch: {actual_funnel_sha}")

    targets = cfg.get("targets") or []
    if not isinstance(targets, list) or not targets:
        raise RuntimeError("UX funnel config has no targets")

    counts_before = public_counts(auth)
    plans = []
    keys = ("id", "slug", "status", "featured_media", "categories", "author")

    for target in targets:
        pid = int(target["post_id"])
        row = fetch_post_by_id(pid, auth)
        title = html.unescape(raw_field(row, "title"))
        if (row.get("id"), row.get("slug"), row.get("status")) != (pid, target["slug"], "publish"):
            raise RuntimeError(f"UX funnel identity/status drifted for {target['slug']}")
        if title != target["title"]:
            raise RuntimeError(f"UX funnel title drifted for {target['slug']}")
        current = raw_field(row, "content")
        updated, action = build_ux_purchase_funnel_target(current, target, funnel)
        plans.append({
            "target": target,
            "row": row,
            "title": title,
            "current": current,
            "updated": updated,
            "action": action,
        })

    for plan in plans:
        latest = fetch_post_by_id(int(plan["target"]["post_id"]), auth)
        if any(latest.get(k) != plan["row"].get(k) for k in keys):
            raise RuntimeError(f"UX funnel concurrent metadata edit: {plan['target']['slug']}")
        if html.unescape(raw_field(latest, "title")) != plan["title"] or raw_field(latest, "content") != plan["current"]:
            raise RuntimeError(f"UX funnel concurrent content edit: {plan['target']['slug']}")

    written = []
    report_dir = Path("reports") / "ux-purchase-funnel-wave1-20261111"
    report_dir.mkdir(parents=True, exist_ok=True)

    try:
        results = []
        for plan in plans:
            target = plan["target"]
            pid = int(target["post_id"])
            wrote = False
            if plan["action"] == "UPDATE":
                response = post_json(
                    f"{SITE_URL}/wp-json/wp/v2/posts/{pid}",
                    auth,
                    {"content": plan["updated"]},
                )
                wrote = True
                written.append(plan)
                if (response.get("id"), response.get("slug"), response.get("status")) != (
                    pid, target["slug"], "publish"
                ):
                    raise RuntimeError(f"UX funnel response mismatch: {target['slug']}")

            after = fetch_post_by_id(pid, auth)
            if any(after.get(k) != plan["row"].get(k) for k in keys):
                raise RuntimeError(f"UX funnel metadata changed: {target['slug']}")
            if html.unescape(raw_field(after, "title")) != plan["title"] or raw_field(after, "content") != plan["updated"]:
                raise RuntimeError(f"UX funnel saved content mismatch: {target['slug']}")

            rendered = (after.get("content") or {}).get("rendered", "")
            if "ガリバーで希望のUXを探してみる" not in rendered:
                raise RuntimeError(f"native Gulliver CTA absent after save: {target['slug']}")

            results.append({
                "action": plan["action"],
                "post_id": pid,
                "slug": target["slug"],
                "status": "publish",
                "title": plan["title"],
                "featured_media": after.get("featured_media"),
                "old_sha256": hashlib.sha256(plan["current"].encode()).hexdigest(),
                "new_sha256": hashlib.sha256(plan["updated"].encode()).hexdigest(),
                "wordpress_write_count": int(wrote),
            })

        counts_after = public_counts(auth)
        if counts_after != counts_before:
            raise RuntimeError("published post/page counts changed during UX funnel update")

        report = {
            "targets": results,
            "published_before": counts_before,
            "published_after": counts_after,
        }
        (report_dir / "result.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        lines = ["# UX purchase funnel wave 1", ""]
        for result in results:
            lines += [
                f"- {result['slug']} ({result['post_id']}): **{result['action']}**",
                "  - status: publish",
                f"  - content: {result['old_sha256']} -> {result['new_sha256']}",
            ]
        (report_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("UX_PURCHASE_FUNNEL_VERIFIED", json.dumps(report, ensure_ascii=False), flush=True)
        return report
    except Exception:
        for plan in reversed(written):
            try:
                target = plan["target"]
                pid = int(target["post_id"])
                now = fetch_post_by_id(pid, auth)
                if raw_field(now, "content") == plan["updated"] and all(
                    now.get(k) == plan["row"].get(k) for k in keys
                ):
                    post_json(
                        f"{SITE_URL}/wp-json/wp/v2/posts/{pid}",
                        auth,
                        {"content": plan["current"]},
                    )
                    print("UX_PURCHASE_FUNNEL_ROLLBACK", target["slug"], flush=True)
                else:
                    print("UX_PURCHASE_FUNNEL_ROLLBACK_SKIPPED_DRIFT", target["slug"], flush=True)
            except Exception as rollback_error:
                print(
                    "UX_PURCHASE_FUNNEL_ROLLBACK_FAILED",
                    plan["target"]["slug"],
                    repr(rollback_error),
                    flush=True,
                )
        raise

def apply(config_path: Path):
    user = os.environ.get("TSURIKUE_WP_USER"); password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password: raise SystemExit("BLOCKED_MISSING_SECRETS")
    auth = auth_header(user, password)
    raw_cfg = json.loads(config_path.read_text(encoding="utf-8"))
    if raw_cfg.get("operation") == "add_ux_resale_actual_negotiation_20261113":
        from add_ux_resale_actual_negotiation_20261113 import apply_negotiation
        return apply_negotiation(config_path, raw_cfg, auth, (fetch_post_by_id, raw_field, public_counts, post_json, SITE_URL))
    if raw_cfg.get("operation") == "rewrite_published_ux_resale_20261113":
        from rewrite_ux_resale_20261113 import apply_revision
        return apply_revision(config_path, raw_cfg, auth, (fetch_post_by_id, raw_field, public_counts, post_json, SITE_URL))
    if raw_cfg.get("operation") == "add_published_ux_used_two_owner_photos_20261113":
        from add_ux_used_owner_photos_20261113 import apply_photos
        return apply_photos(config_path, raw_cfg, auth, (fetch_post_by_id, raw_field, public_counts, post_json, SITE_URL))
    if raw_cfg.get("operation") == "refine_published_ux_used_voice_breaks_20261113":
        from refine_ux_used_voice_breaks_20261113 import apply_revision
        return apply_revision(config_path, raw_cfg, auth, (fetch_post_by_id, raw_field, public_counts, post_json, SITE_URL))
    if raw_cfg.get("operation") == "rewrite_published_lexus_ux_used_20261113":
        from rewrite_ux_used_20261113 import apply_rewrite
        return apply_rewrite(config_path, raw_cfg, auth, (fetch_post_by_id, raw_field, public_counts, post_json, SITE_URL))
    if raw_cfg.get("operation") == "replace_published_ux_purchase_funnels":
        return apply_published_ux_purchase_funnels(config_path, raw_cfg, auth)
    if raw_cfg.get("operation") == "replace_published_affiliate_copy":
        return apply_published_affiliate_copy_replacements(raw_cfg, auth)
    if raw_cfg.get("operation") == "insert_gulliver_extra_buttons":
        return apply_published_gulliver_extra_buttons(raw_cfg, auth)
    if raw_cfg.get("operation") == "insert_gulliver_context_ctas":
        return apply_published_gulliver_context_ctas(raw_cfg, auth)
    if raw_cfg.get("operation") == "replace_published_gulliver_banner":
        return apply_published_affiliate_swap(raw_cfg, auth)
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
