#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

SITE = "https://tsurikue.com"
UA = "tsurikue-audit-3104-affiliate-20260915/1.0"
REPORT = Path("reports/3104-affiliate-audit-20260915")
BLOG_PART_ID = 2184
FJ_SLUGS = [
    "landcruiser-fj-review",
    "landcruiser-fj-price",
    "landcruiser-fj-rear-seat",
    "landcruiser-fj-drawbacks",
]

def auth_header() -> str:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise RuntimeError("missing WordPress secrets")
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"

AUTH = None

def req(path: str):
    global AUTH
    if AUTH is None:
        AUTH = auth_header()
    url = SITE + path
    r = urllib.request.Request(url, headers={
        "Authorization": AUTH,
        "Accept": "application/json",
        "User-Agent": UA,
    })
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))

def raw_field(row: dict, key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)

def sha256(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()

def find_blog_part_endpoint(types: dict) -> tuple[str, dict]:
    candidates = []
    for type_key, spec in types.items():
        hay = " ".join([
            str(type_key),
            str(spec.get("name") or ""),
            str(spec.get("slug") or ""),
            str(spec.get("rest_base") or ""),
        ]).lower()
        if any(x in hay for x in ["blog_parts", "blog-parts", "blog parts", "swell", "parts"]):
            candidates.append((type_key, spec))
    # Prefer exact-looking SWELL blog-parts types first.
    candidates.sort(key=lambda x: (
        0 if "blog" in (str(x[1].get("rest_base") or "") + str(x[0])).lower() and "part" in (str(x[1].get("rest_base") or "") + str(x[0])).lower() else 1,
        x[0]
    ))
    errors = []
    for type_key, spec in candidates:
        rest_base = spec.get("rest_base") or type_key
        try:
            row = req(f"/wp-json/wp/v2/{urllib.parse.quote(str(rest_base))}/{BLOG_PART_ID}?context=edit")
            if int(row.get("id") or 0) == BLOG_PART_ID:
                return str(rest_base), row
        except Exception as exc:
            errors.append(f"{rest_base}: {type(exc).__name__}: {exc}")
    for rest_base in ["blog_parts", "blog-parts", "swell_parts", "wp_block"]:
        try:
            row = req(f"/wp-json/wp/v2/{rest_base}/{BLOG_PART_ID}?context=edit")
            if int(row.get("id") or 0) == BLOG_PART_ID:
                return rest_base, row
        except Exception as exc:
            errors.append(f"{rest_base}: {type(exc).__name__}: {exc}")
    raise RuntimeError("could not resolve blog part endpoint; " + " | ".join(errors[-8:]))

def inspect_fj_posts():
    rows = []
    for slug in FJ_SLUGS:
        q = urllib.parse.urlencode({
            "context": "edit",
            "slug": slug,
            "status": "any",
            "per_page": 10,
            "_fields": "id,slug,status,title,content,author,modified,featured_media,link",
        })
        found = req(f"/wp-json/wp/v2/posts?{q}")
        if len(found) != 1:
            rows.append({"slug": slug, "error": f"expected 1 row, got {len(found)}"})
            continue
        row = found[0]
        content = raw_field(row, "content")
        ids = sorted(set(int(x) for x in re.findall(r'\[blog_parts id="(\d+)"\]', content)))
        rows.append({
            "id": int(row["id"]),
            "slug": row.get("slug"),
            "status": row.get("status"),
            "title": html.unescape(raw_field(row, "title")),
            "author": row.get("author"),
            "modified": row.get("modified"),
            "featured_media": row.get("featured_media"),
            "blog_part_ids": ids,
            "content_sha256": sha256(content),
        })
    return rows

def main():
    REPORT.mkdir(parents=True, exist_ok=True)
    types = req("/wp-json/wp/v2/types?context=edit")
    rest_base, part = find_blog_part_endpoint(types)
    part_content = raw_field(part, "content")
    part_title = html.unescape(raw_field(part, "title"))
    a8_urls = re.findall(r'https?://[^"\'\s<>]*a8\.net[^"\'\s<>]*', part_content, flags=re.I)
    a8mat_values = re.findall(r'a8mat=([^&"\'<>\s]+)', part_content, flags=re.I)
    id1_values = re.findall(r'[?&]id1=([^&"\'<>\s]+)', part_content, flags=re.I)

    fj = inspect_fj_posts()
    payload = {
        "result": "SUCCESS",
        "blog_part": {
            "id": BLOG_PART_ID,
            "rest_base": rest_base,
            "type": part.get("type"),
            "status": part.get("status"),
            "slug": part.get("slug"),
            "title": part_title,
            "content_sha256": sha256(part_content),
            "a8_url_count": len(a8_urls),
            "a8_urls": a8_urls,
            "a8mat_values": sorted(set(a8mat_values)),
            "id1_values": sorted(set(id1_values)),
        },
        "fj_posts": fj,
    }
    (REPORT / "result.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (REPORT / "blogpart-2184-content.txt").write_text(part_content, encoding="utf-8")
    # Keep only type names/rest bases for audit readability.
    (REPORT / "types-summary.json").write_text(json.dumps({
        k: {"name": v.get("name"), "slug": v.get("slug"), "rest_base": v.get("rest_base")}
        for k, v in types.items()
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# 3104 affiliate audit 2026-09-15",
        "",
        "- result: **SUCCESS**",
        f"- blog part ID: **{BLOG_PART_ID}**",
        f"- blog part title: **{part_title}**",
        f"- blog part status: **{part.get('status')}**",
        f"- blog part REST base: **{rest_base}**",
        f"- blog part content_sha256: **{sha256(part_content)}**",
        f"- A8 URL count in blog part: **{len(a8_urls)}**",
        f"- A8 URLs: **{a8_urls}**",
        f"- existing id1 values: **{sorted(set(id1_values))}**",
        "",
        "## FJ posts",
        "",
        "|ID|slug|status|author|blog parts|content sha256|modified|",
        "|---:|---|---|---:|---|---|---|",
    ]
    for row in fj:
        if row.get("error"):
            lines.append(f"|—|{row['slug']}|ERROR|—|{row['error']}|—|—|")
        else:
            lines.append(f"|{row['id']}|{row['slug']}|{row['status']}|{row['author']}|{row['blog_part_ids']}|{row['content_sha256']}|{row['modified']}|")
    (REPORT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))

if __name__ == "__main__":
    main()
