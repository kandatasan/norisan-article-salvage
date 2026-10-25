#!/usr/bin/env python3
"""Guarded, three-post, content-only update for the 2026-10-25 entry-MSRP additions.

Only the new price segment is inserted; all other live WordPress bytes are retained.
Never modifies publication status, title, categories, images, links, or user edits.
"""
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
USER_AGENT = "tsurikue-three-entry-msrp-20261025/1.0"
TARGETS = [
    (4256, "lexus-ux-rival-suv", "editorial/lexus-ux-rival-suv-20261025/content.html", 0, 6),
    (4261, "landcruiser-fj-rivals", "editorial/landcruiser-fj-rivals-20261025/content.html", 0, 6),
    (4264, "tanto-rival-cars", "editorial/tanto-rival-4-cars-20261025/content.html", 3954, 5),
]
PRICE_LABELS = {
    "landcruiser-fj-rivals": ("車両本体価格<br>（税込）", 6),
    "tanto-rival-cars": ("新車価格<br>（万円）", 5),
}
UX_ANCHOR = (
    "<!-- wp:paragraph -->\n"
    "<p>UXとCX-30は全高1,540mmで同じ。<br>"
    "クロストレックは全長がUXより15mm短いだけ。</p>"
)
UX_HEADING = (
    '<!-- wp:heading {"level":3} -->\n'
    '<h3 class="wp-block-heading">オプションなしの新車は何円から？</h3>'
)
PARAGRAPH_PREFIXES = {
    "landcruiser-fj-rivals": (
        "価格は各メーカーの希望小売価格（税込・車両本体）で、オプション・諸費用は別。<br>僕のFJで",
        "元の「車両本体価格」は<strong>装備比較の基準グレード</strong>、新しい「最安新車価格」は<strong>車種ごとのエントリーグレード</strong>。<br>2026年10月25日時点の税込希望小売価格で、オプション・有料色・諸費用は別。<br>フォレスター最安はターボのTouring、デリカD:5最安はG。○△×は上級比較グレードの装備です。<br>僕のFJで",
    ),
    "tanto-rival-cars": (
        "<p>車両本体価格にはカーナビなどのオプションや諸費用は含みません。<br>見積もり総額は別で比べたいですね。</p>",
        "<p>元の新車価格は<strong>装備比較に使ったターボ車</strong>、追加した最安新車価格は<strong>車種ごとのエントリーグレード</strong>。<br>2026年10月25日時点の税込希望小売価格で、オプション・有料色・諸費用は別。<br>最安グレードはNA車も含むので、装備の○△×を当てはめないでください。</p>",
    ),
}


def unique_replace(text, old, new, context):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{context}: expected one anchor, got {count}")
    return text.replace(old, new, 1)


def price_row_re(label, columns):
    return re.compile(
        r'<tr><th scope="row"[^>]*>' + re.escape(label) +
        r'</th>(?:<td[^>]*>[^<]*</td>){' + str(columns) + r'}</tr>'
    )


def build_insert(current, desired, slug, expected_price_count):
    if slug == "lexus-ux-rival-suv":
        start = desired.find(UX_HEADING)
        end = desired.find(UX_ANCHOR, start)
        if start < 0 or end < 0:
            raise RuntimeError("UX desired pricing section not found")
        fragment = desired[start:end]
        if fragment.count('id="ux-entry-prices"') != 1:
            raise RuntimeError("UX pricing section marker mismatch")
        if 'id="ux-entry-prices"' in current:
            if fragment in current:
                return current, "ALREADY_PRESENT"
            raise RuntimeError("UX live pricing differs: refusing overwrite")
        return unique_replace(current, UX_ANCHOR, fragment + UX_ANCHOR, "UX insertion"), "UPDATE"
    label, columns = PRICE_LABELS[slug]
    rx = price_row_re(label, columns)
    desired_row = rx.search(desired)
    current_row = rx.search(current)
    if not desired_row or not current_row or len(rx.findall(current)) != 1:
        raise RuntimeError(f"{slug}: price row missing or ambiguous")
    if current_row.group(0) != desired_row.group(0):
        raise RuntimeError(f"{slug}: price row was edited; refusing overwrite")
    tail = desired[desired_row.end():]
    first = re.match(r"\s*<tr>[\s\S]*?</tr>", tail)
    if not first:
        raise RuntimeError(f"{slug}: first entry-price row absent")
    second = re.match(r"\s*<tr>[\s\S]*?</tr>", tail[first.end():])
    if not second:
        raise RuntimeError(f"{slug}: second entry-price row absent")
    additions = tail[:first.end() + second.end()]
    if additions.count("最安グレード<br>（別仕様）") != 1 or additions.count("最安新車価格<br>（OPなし・税込）") != 1:
        raise RuntimeError(f"{slug}: expected two pricing rows")
    if additions.count("<tr>") != 2 or additions.count("</tr>") != 2:
        raise RuntimeError(f"{slug}: pricing rows malformed")
    old_copy, new_copy = PARAGRAPH_PREFIXES[slug]
    existing = current.count("最安グレード<br>（別仕様）")
    if existing:
        if existing == 1 and additions in current and new_copy in current:
            return current, "ALREADY_PRESENT"
        raise RuntimeError(f"{slug}: partial pricing section already exists")
    changed = unique_replace(current, current_row.group(0), current_row.group(0) + additions, f"{slug} price rows")
    changed = unique_replace(changed, old_copy, new_copy, f"{slug} price explanation")
    return changed, "UPDATE"


def request(path, auth, payload=None):
    url = SITE + path
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST" if payload is not None else "GET",
        headers={
            "Authorization": auth,
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    with urllib.request.urlopen(req, timeout=90) as res:
        return json.loads(res.read().decode("utf-8")), dict(res.headers.items())


def get_post(pid, auth):
    params = urllib.parse.urlencode({
        "context": "edit",
        "_fields": "id,slug,status,title,content,featured_media,categories,author,excerpt",
    })
    return request(f"/wp-json/wp/v2/posts/{pid}?{params}", auth)[0]


def raw(row, key):
    x = row.get(key) or {}
    return x.get("raw") or x.get("rendered") or "" if isinstance(x, dict) else str(x)


def snapshot(row):
    return (
        row.get("id"), row.get("slug"), row.get("status"),
        html.unescape(raw(row, "title")), row.get("featured_media"),
        sorted(row.get("categories") or []), row.get("author"), raw(row, "excerpt"),
    )


def public_counts(auth):
    result = {}
    for resource in ("posts", "pages"):
        q = urllib.parse.urlencode({"context": "edit", "status": "publish", "per_page": 1, "_fields": "id"})
        _, headers = request(f"/wp-json/wp/v2/{resource}?{q}", auth)
        result[resource] = int(headers.get("X-WP-Total", "0"))
    return result


def preflight(auth):
    counts = public_counts(auth)
    planned = []
    for pid, slug, path, media_id, expected_prices in TARGETS:
        row = get_post(pid, auth)
        before = raw(row, "content")
        if row.get("id") != pid or row.get("slug") != slug:
            raise RuntimeError(f"{slug}: ID/slug does not match")
        if row.get("status") not in ("publish", "draft"):
            raise RuntimeError(f"{slug}: unexpected status {row.get('status')}")
        if int(row.get("featured_media") or 0) != media_id:
            raise RuntimeError(f"{slug}: featured_media mismatch")
        if "<!-- tsurikue-new-article:v1 slug=" + slug + " -->" not in before:
            raise RuntimeError(f"{slug}: original content marker missing")
        desired = Path(path).read_text(encoding="utf-8")
        updated, action = build_insert(before, desired, slug, expected_prices)
        if before.count('[blog_parts id="2843"]') != 1 or updated.count('[blog_parts id="2843"]') != 1:
            raise RuntimeError(f"{slug}: affiliate shortcode unexpectedly changed")
        for typ in ("paragraph", "heading", "list", "image", "html", "table", "shortcode"):
            before_open = len(re.findall(r"<!-- wp:" + typ + r"(?= | -->)", before))
            before_close = before.count("<!-- /wp:" + typ + " -->")
            after_open = len(re.findall(r"<!-- wp:" + typ + r"(?= | -->)", updated))
            after_close = updated.count("<!-- /wp:" + typ + " -->")
            if before_open != before_close or after_open != after_close:
                raise RuntimeError(f"{slug}: unbalanced {typ} Gutenberg blocks")
        # The newly added price entries must be complete, not a partial user edit.
        if action == "UPDATE" and (len(updated) - len(before)) < 700:
            raise RuntimeError(f"{slug}: insertion unexpectedly short")
        planned.append((pid, slug, row, before, updated, action))
        print("ENTRY_MSRP_PREFLIGHT_OK", pid, slug, row["status"], action, hashlib.sha256(before.encode()).hexdigest(), flush=True)
    return planned, counts


def run():
    username = os.environ["TSURIKUE_WP_USER"]
    password = os.environ["TSURIKUE_WP_APP_PASSWORD"]
    auth = "Basic " + base64.b64encode(f"{username}:{password}".encode()).decode()
    planned, before_counts = preflight(auth)  # no writes until all three pass
    results = []
    for pid, slug, original, before, updated, action in planned:
        latest = get_post(pid, auth)
        if snapshot(latest) != snapshot(original) or raw(latest, "content") != before:
            raise RuntimeError(f"{slug}: concurrent WordPress edit; refusing update")
        if action == "UPDATE":
            response, _ = request(f"/wp-json/wp/v2/posts/{pid}", auth, {"content": updated})
            if response.get("id") != pid or response.get("status") != original.get("status"):
                raise RuntimeError(f"{slug}: WP response mismatch")
        after = get_post(pid, auth)
        if snapshot(after) != snapshot(original) or raw(after, "content") != updated:
            raise RuntimeError(f"{slug}: saved content/metadata mismatch")
        if public_counts(auth) != before_counts:
            raise RuntimeError(f"{slug}: published article counts changed")
        results.append({
            "post_id": pid, "slug": slug, "status": after.get("status"), "action": action,
            "before_sha256": hashlib.sha256(before.encode()).hexdigest(),
            "after_sha256": hashlib.sha256(updated.encode()).hexdigest(),
            "write_count": int(action == "UPDATE"),
        })
        print("ENTRY_MSRP_VERIFIED", pid, slug, after.get("status"), action, flush=True)
    Path("reports/three-entry-msrp").mkdir(parents=True, exist_ok=True)
    result = {"results": results, "public_before": before_counts, "public_after": public_counts(auth)}
    Path("reports/three-entry-msrp/result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    run()
