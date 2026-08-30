#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

SITE = "https://tsurikue.com"
OUT = Path("reports/recent-ux-media-inspection")
MAX_MEDIA = 30


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def get_json(url: str, auth: str):
    req = urllib.request.Request(
        url,
        headers={"Accept":"application/json", "Authorization":auth, "User-Agent":"tsurikue-recent-media-inspector/1.0"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode())


def download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent":"tsurikue-recent-media-inspector/1.0"}, method="GET")
    with urllib.request.urlopen(req, timeout=60) as r:
        dest.write_bytes(r.read())


def main() -> None:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    auth = auth_header(user, password)

    params = {
        "context":"edit",
        "per_page":str(MAX_MEDIA),
        "page":"1",
        "orderby":"date",
        "order":"desc",
        "media_type":"image",
        "_fields":"id,date,slug,source_url,alt_text,caption,media_details",
    }
    rows = get_json(f"{SITE}/wp-json/wp/v2/media?{urllib.parse.urlencode(params)}", auth)

    OUT.mkdir(parents=True, exist_ok=True)
    img_dir = OUT / "images"
    img_dir.mkdir(exist_ok=True)
    manifest = []

    for row in rows:
        src = row.get("source_url") or ""
        if not src:
            continue
        filename = Path(urllib.parse.urlparse(src).path).name
        safe = f"{row.get('id')}_{filename}"
        path = img_dir / safe
        try:
            download(src, path)
            download_status = "ok"
        except Exception as exc:
            download_status = f"error:{type(exc).__name__}"
        details = row.get("media_details") or {}
        caption = row.get("caption") or {}
        manifest.append({
            "id": row.get("id"),
            "date": row.get("date"),
            "slug": row.get("slug"),
            "filename": filename,
            "source_url": src,
            "alt_text": row.get("alt_text") or "",
            "caption": (caption.get("raw") or caption.get("rendered") or "") if isinstance(caption, dict) else str(caption),
            "width": details.get("width"),
            "height": details.get("height"),
            "artifact_file": str(path),
            "download": download_status,
        })

    result = {
        "mode":"READ_ONLY",
        "wordpress_write_count":0,
        "media_scanned":len(rows),
        "downloaded":sum(1 for x in manifest if x["download"] == "ok"),
        "items":manifest,
    }
    (OUT / "manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Recent UX media inspection",
        "",
        "- mode: **READ ONLY**",
        "- wordpress_write_count: **0**",
        f"- media_scanned: **{len(rows)}**",
        f"- downloaded: **{result['downloaded']}**",
        "",
        "## Recent media",
    ]
    for x in manifest:
        lines += [
            f"- #{x['id']} `{x['filename']}` | {x['date']} | {x['width']}x{x['height']} | alt: {x['alt_text'] or '(empty)'} | {x['download']}",
        ]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
