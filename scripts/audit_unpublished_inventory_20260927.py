#!/usr/bin/env python3
from __future__ import annotations

import base64
import html
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SITE = "https://tsurikue.com"
REPORT_DIR = Path("reports/unpublished-inventory-20260927")
UA = "tsurikue-unpublished-inventory-audit/1.0"

STATUSES = ["draft", "pending", "private", "future"]
POST_TYPES = ["posts", "pages"]

INCOMPLETE_PATTERNS = [
    r"PHOTO[_ -]?SLOT",
    r"TODO",
    r"FIXME",
    r"未完成",
    r"準備中",
    r"あとで(?:追加|修正|確認)",
    r"写真(?:を)?(?:ここ|後で)",
    r"画像(?:を)?(?:ここ|後で)",
    r"tsurikue:photo-slot",
    r"placeholder",
    r"仮置き",
    r"要確認",
]

EXPERIMENT_PATTERNS = [
    r"(?:^|[-_/])test(?:$|[-_/])",
    r"(?:^|[-_/])lab(?:$|[-_/])",
    r"experiment",
    r"experimental",
    r"sandbox",
    r"検証用",
    r"テスト",
]


def auth_header() -> str:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def get_json(url: str, auth: str):
    req = urllib.request.Request(
        url,
        headers={"Authorization": auth, "Accept": "application/json", "User-Agent": UA},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8")), dict(resp.headers)


def raw(row, key: str) -> str:
    v = row.get(key) or {}
    if isinstance(v, dict):
        return v.get("raw") or v.get("rendered") or ""
    return str(v)


def plain(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"<script\b.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_all(endpoint: str, status: str, auth: str):
    rows = []
    page = 1
    while True:
        params = urllib.parse.urlencode(
            {
                "context": "edit",
                "status": status,
                "per_page": 100,
                "page": page,
                "orderby": "modified",
                "order": "desc",
                "_fields": "id,slug,status,title,content,featured_media,categories,tags,modified,date,link",
            }
        )
        try:
            batch, headers = get_json(f"{SITE}/wp-json/wp/v2/{endpoint}?{params}", auth)
        except urllib.error.HTTPError as e:
            if e.code == 400 and page > 1:
                break
            raise
        rows.extend(batch)
        total_pages = int(headers.get("X-WP-TotalPages", "1"))
        if page >= total_pages:
            break
        page += 1
    return rows


def analyze(row, post_type: str):
    content = raw(row, "content")
    visible = plain(content)
    title = plain(raw(row, "title"))
    slug = row.get("slug") or ""

    incomplete_hits = []
    for pat in INCOMPLETE_PATTERNS:
        if re.search(pat, content, flags=re.I):
            incomplete_hits.append(pat)

    experiment_hits = []
    haystack = f"{slug}\n{title}\n{content[:1000]}"
    for pat in EXPERIMENT_PATTERNS:
        if re.search(pat, haystack, flags=re.I):
            experiment_hits.append(pat)

    img_count = len(re.findall(r"<img\b", content, flags=re.I))
    image_block_count = len(re.findall(r"<!--\s*wp:image\b", content, flags=re.I))
    blog_parts_count = len(re.findall(r"\[blog_parts\s+id=", content, flags=re.I))
    h1_count = len(re.findall(r"<h1\b", content, flags=re.I))
    h2_count = len(re.findall(r"<h2\b", content, flags=re.I))
    open_blocks = len(re.findall(r"<!--\s*wp:[^>]+-->", content))
    close_blocks = len(re.findall(r"<!--\s*/wp:[^>]+-->", content))
    block_balance_ok = open_blocks == close_blocks

    categories = row.get("categories") or []
    tags = row.get("tags") or []
    featured = int(row.get("featured_media") or 0)
    visible_len = len(visible)

    reasons = []
    if incomplete_hits:
        reasons.append("未完マーカーあり")
    if visible_len < 900:
        reasons.append("本文が短い")
    if not block_balance_ok:
        reasons.append("Gutenbergブロック数不一致")
    if h1_count:
        reasons.append("本文H1あり")
    if post_type == "post" and not categories:
        reasons.append("カテゴリ未設定")
    if experiment_hits:
        reasons.append("実験/テスト系の語あり")

    if experiment_hits:
        bucket = "実験・保留候補"
    elif incomplete_hits or visible_len < 900 or not block_balance_ok:
        bucket = "未完成・要修正"
    else:
        bucket = "公開候補"

    return {
        "id": row.get("id"),
        "type": post_type,
        "slug": slug,
        "status": row.get("status"),
        "title": title,
        "modified": row.get("modified"),
        "date": row.get("date"),
        "featured_media": featured,
        "categories": categories,
        "tags": tags,
        "visible_chars": visible_len,
        "raw_chars": len(content),
        "img_count": img_count,
        "image_block_count": image_block_count,
        "blog_parts_count": blog_parts_count,
        "h1_count": h1_count,
        "h2_count": h2_count,
        "block_balance_ok": block_balance_ok,
        "incomplete_hits": incomplete_hits,
        "experiment_hits": experiment_hits,
        "bucket": bucket,
        "reasons": reasons,
        "link": row.get("link"),
    }


def main():
    auth = auth_header()
    items = []
    totals = {}

    for endpoint in POST_TYPES:
        post_type = "post" if endpoint == "posts" else "page"
        for status in STATUSES:
            rows = fetch_all(endpoint, status, auth)
            totals[f"{post_type}:{status}"] = len(rows)
            items.extend(analyze(r, post_type) for r in rows)

    # Newest first within each bucket.
    order = {"公開候補": 0, "未完成・要修正": 1, "実験・保留候補": 2}
    items.sort(key=lambda x: (order.get(x["bucket"], 9), x["modified"] or ""), reverse=False)

    report = {
        "mode": "GET_ONLY",
        "wordpress_write_count": 0,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "totals": totals,
        "items": items,
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    counts = {}
    for x in items:
        counts[x["bucket"]] = counts.get(x["bucket"], 0) + 1

    lines = [
        "# Current unpublished inventory audit 2026-09-27",
        "",
        "- mode: **GET ONLY**",
        "- wordpress_write_count: **0**",
        f"- unpublished posts: **{sum(totals.get(f'post:{s}', 0) for s in STATUSES)}**",
        f"- unpublished pages: **{sum(totals.get(f'page:{s}', 0) for s in STATUSES)}**",
        f"- 公開候補: **{counts.get('公開候補', 0)}**",
        f"- 未完成・要修正: **{counts.get('未完成・要修正', 0)}**",
        f"- 実験・保留候補: **{counts.get('実験・保留候補', 0)}**",
        "",
        "※分類は機械的な一次判定。公開操作は行っていません。",
        "",
    ]

    for bucket in ["公開候補", "未完成・要修正", "実験・保留候補"]:
        lines += [f"## {bucket}", "", "|ID|種別|status|slug|更新|文字数|画像|アイキャッチ|H2|理由|タイトル|", "|---:|---|---|---|---|---:|---:|---:|---:|---|---|"]
        rows = [x for x in items if x["bucket"] == bucket]
        if not rows:
            lines.append("|—|—|—|—|—|—|—|—|—|—|該当なし|")
        for x in rows:
            reason = " / ".join(x["reasons"]) if x["reasons"] else "目立つ未完サインなし"
            title = (x["title"] or "").replace("|", "｜")
            slug = (x["slug"] or "").replace("|", "｜")
            lines.append(
                f"|{x['id']}|{x['type']}|{x['status']}|{slug}|{x['modified']}|{x['visible_chars']}|{x['img_count']}|{x['featured_media']}|{x['h2_count']}|{reason}|{title}|"
            )
        lines.append("")

    (REPORT_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
