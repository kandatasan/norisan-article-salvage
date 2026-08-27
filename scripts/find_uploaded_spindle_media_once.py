#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

SITE_URL = "https://tsurikue.com"
OUT = Path("reports/spindle-media-filename-lookup")
WANTED = ["IMG_2949.jpeg", "IMG_2950.jpeg", "IMG_2951.jpeg", "IMG_2750.jpeg", "IMG_2751.jpeg"]


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def get_json(url: str, authorization: str):
    req = urllib.request.Request(url, headers={"Accept":"application/json","Authorization":authorization,"User-Agent":"tsurikue-media-lookup/1.0"}, method="GET")
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode()), dict(r.headers)


def stem(name: str) -> str:
    s = Path(name).stem.casefold()
    s = re.sub(r"-\d+x\d+$", "", s)
    s = re.sub(r"-scaled$", "", s)
    return s


def main() -> None:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    auth = auth_header(user, password)

    params = {"context":"edit","per_page":"100","page":"1","_fields":"id,date,slug,source_url,alt_text,caption,media_details"}
    rows, headers = get_json(f"{SITE_URL}/wp-json/wp/v2/media?{urllib.parse.urlencode(params)}", auth)
    all_rows = list(rows)
    pages = int(headers.get("X-WP-TotalPages", "1"))
    for page in range(2, pages + 1):
        params["page"] = str(page)
        page_rows, _ = get_json(f"{SITE_URL}/wp-json/wp/v2/media?{urllib.parse.urlencode(params)}", auth)
        all_rows.extend(page_rows)

    wanted = {stem(x): x for x in WANTED}
    matches = []
    for row in all_rows:
        src = row.get("source_url") or ""
        filename = Path(urllib.parse.urlparse(src).path).name
        st = stem(filename)
        if st not in wanted:
            continue
        details = row.get("media_details") or {}
        caption = row.get("caption") or {}
        matches.append({
            "matched": wanted[st],
            "id": row.get("id"),
            "date": row.get("date"),
            "slug": row.get("slug"),
            "filename": filename,
            "source_url": src,
            "alt_text": row.get("alt_text") or "",
            "caption": caption.get("raw") or caption.get("rendered") or "" if isinstance(caption, dict) else str(caption),
            "width": details.get("width"),
            "height": details.get("height"),
        })

    OUT.mkdir(parents=True, exist_ok=True)
    result = {"mode":"read-only","wordpress_write_count":0,"wanted":WANTED,"media_count_scanned":len(all_rows),"match_count":len(matches),"matches":matches}
    (OUT / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    lines = ["# Spindle media filename lookup", "", "- mode: **READ ONLY**", "- wordpress_write_count: **0**", f"- media_count_scanned: **{len(all_rows)}**", f"- match_count: **{len(matches)}**", "", "## Matches"]
    if not matches:
        lines.append("(none)")
    for m in matches:
        lines += [f"### {m['matched']} -> media #{m['id']}", f"- filename: `{m['filename']}`", f"- date: {m['date']}", f"- size: {m['width']}x{m['height']}", f"- source_url: {m['source_url']}", f"- alt: {m['alt_text'] or '(empty)'}", ""]
    (OUT / "summary.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
