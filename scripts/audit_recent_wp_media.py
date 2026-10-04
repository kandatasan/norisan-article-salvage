#!/usr/bin/env python3
from __future__ import annotations
import base64, io, json, os, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw

SITE_URL = "https://tsurikue.com"
USER_AGENT = "tsurikue-recent-media-audit/1.1"


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def get_bytes(url: str, authorization: str | None = None, timeout: int = 15) -> tuple[bytes, dict]:
    headers = {"User-Agent": USER_AGENT}
    if authorization:
        headers["Authorization"] = authorization
        headers["Accept"] = "application/json"
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), dict(r.headers)


def main() -> int:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    auth = auth_header(user, password)

    params = urllib.parse.urlencode({
        "context": "edit",
        "per_page": "24",
        "orderby": "date",
        "order": "desc",
        "media_type": "image",
        "_fields": "id,date,slug,title,source_url,media_details,alt_text,caption",
    })
    raw, _ = get_bytes(f"{SITE_URL}/wp-json/wp/v2/media?{params}", auth, timeout=20)
    rows = json.loads(raw.decode())
    if not isinstance(rows, list):
        raise RuntimeError("unexpected media response")

    out = Path("reports/recent-wp-media")
    out.mkdir(parents=True, exist_ok=True)
    (out / "recent-media.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    cell_w, cell_h = 360, 300
    cols = 4
    cards = []
    report_lines = ["# Recent WordPress media", ""]
    for row in rows:
        mid = int(row.get("id") or 0)
        url = row.get("source_url") or ""
        title = ((row.get("title") or {}).get("raw") or (row.get("title") or {}).get("rendered") or "").strip()
        details = row.get("media_details") or {}
        w = details.get("width")
        h = details.get("height")
        date = row.get("date") or ""
        filename = urllib.parse.unquote(urllib.parse.urlparse(url).path.rsplit("/", 1)[-1])
        report_lines.append(f"- id={mid} | {date} | {w}x{h} | {filename} | {title}")
        try:
            img_bytes, _ = get_bytes(url, timeout=10)
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            img.thumbnail((cell_w - 20, cell_h - 70))
        except Exception as e:
            img = Image.new("RGB", (cell_w - 20, cell_h - 70), "white")
            d = ImageDraw.Draw(img)
            d.text((8, 8), f"download failed\n{type(e).__name__}", fill="black")
        card = Image.new("RGB", (cell_w, cell_h), "white")
        x = (cell_w - img.width) // 2
        card.paste(img, (x, 8))
        d = ImageDraw.Draw(card)
        label = f"ID {mid} | {w}x{h}\n{filename[:45]}\n{date[:19]}"
        d.multiline_text((8, cell_h - 58), label, fill="black", spacing=2)
        cards.append(card)

    rows_n = (len(cards) + cols - 1) // cols
    sheet = Image.new("RGB", (cell_w * cols, cell_h * max(rows_n, 1)), "#dddddd")
    for i, card in enumerate(cards):
        sheet.paste(card, ((i % cols) * cell_w, (i // cols) * cell_h))
    sheet.save(out / "contact-sheet.jpg", quality=88)
    (out / "summary.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(f"MEDIA_COUNT={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
