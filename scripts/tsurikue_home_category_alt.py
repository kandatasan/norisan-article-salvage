#!/usr/bin/env python3
"""Safely add alt text to the four linked category images on the tsurikue.com homepage."""
from __future__ import annotations

import argparse
import base64
import csv
import difflib
import html
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

SITE_URL = "https://tsurikue.com"
PAGE_ID = 2255
EXPECTED_URL = "https://tsurikue.com/"
ENDPOINT = "pages"
APPLY_CONFIRMATION = "APPLY-HOME-CATEGORY-ALT-20260711"

TARGETS = (
    (2298, "https://tsurikue.com/category/fishing/", "釣りカテゴリー"),
    (2297, "https://tsurikue.com/category/sightseeing-leisure/", "レジャー・観光カテゴリー"),
    (2299, "https://tsurikue.com/category/gourmet/", "グルメカテゴリー"),
    (2300, "https://tsurikue.com/category/car/", "車カテゴリー"),
)

FIGURE_RE = re.compile(r"<figure\b.*?</figure>", re.I | re.S)
IMG_RE = re.compile(r"<img\b[^>]*>", re.I | re.S)
BLANK_ALT_RE = re.compile(r"\balt\s*=\s*([\"'])\s*\1", re.I)


@dataclass
class Document:
    post_id: int
    title: str
    link: str
    content: str


@dataclass
class Action:
    image_id: int
    href: str
    alt: str
    before: str
    after: str


@dataclass
class Result:
    original: str
    updated: str
    actions: list[Action]
    blank_alts_before: int
    blank_alts_after: int


def request_json(url: str, *, method: str = "GET", auth_header: str | None = None, payload: dict | None = None) -> dict:
    headers = {"Accept": "application/json", "User-Agent": "tsurikue-home-category-alt/1.0"}
    data = None
    if auth_header:
        headers["Authorization"] = auth_header
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as error:
            last_error = error
            if attempt < 3:
                time.sleep(attempt * 3)
    assert last_error is not None
    raise last_error


def make_auth_header(user: str, app_password: str) -> str:
    token = base64.b64encode(f"{user}:{app_password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def endpoint_for(site_url: str) -> str:
    return f"{site_url.rstrip('/')}/wp-json/wp/v2/{ENDPOINT}/{PAGE_ID}"


def fetch_document(site_url: str, user: str, app_password: str) -> Document:
    fields = "id,status,link,title,content"
    query = urllib.parse.urlencode({"context": "edit", "_fields": fields})
    row = request_json(
        f"{endpoint_for(site_url)}?{query}",
        auth_header=make_auth_header(user, app_password),
    )
    if int(row.get("id", 0)) != PAGE_ID:
        raise ValueError(f"Requested ID {PAGE_ID} but received {row.get('id')}")
    if row.get("status") != "publish":
        raise ValueError("Homepage is not published")
    link = row.get("link", "")
    if link.rstrip("/") != EXPECTED_URL.rstrip("/"):
        raise ValueError(f"Homepage URL mismatch: {link}")
    content = (row.get("content") or {}).get("raw")
    if content is None:
        raise ValueError("content.raw was not returned")
    title = html.unescape((row.get("title") or {}).get("raw") or (row.get("title") or {}).get("rendered", ""))
    return Document(PAGE_ID, title, link, content)


def transform(content: str) -> Result:
    original_blank_alts = len(BLANK_ALT_RE.findall(content))
    replacements: list[tuple[int, int, str, Action]] = []

    figures = list(FIGURE_RE.finditer(content))
    for image_id, href, alt in TARGETS:
        matches = []
        token = f"wp-image-{image_id}"
        for figure_match in figures:
            figure = figure_match.group(0)
            if token in figure and f'href="{href}"' in figure:
                matches.append(figure_match)
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one figure for image {image_id}; found {len(matches)}")

        figure_match = matches[0]
        figure = figure_match.group(0)
        img_matches = [match for match in IMG_RE.finditer(figure) if token in match.group(0)]
        if len(img_matches) != 1:
            raise ValueError(f"Expected exactly one img tag for image {image_id}; found {len(img_matches)}")
        img_match = img_matches[0]
        img_tag = img_match.group(0)
        if not BLANK_ALT_RE.search(img_tag):
            raise ValueError(f"Image {image_id} does not have exactly one blank alt")
        updated_img = BLANK_ALT_RE.sub(f'alt="{alt}"', img_tag, count=1)
        updated_figure = figure[: img_match.start()] + updated_img + figure[img_match.end() :]
        replacements.append(
            (
                figure_match.start(),
                figure_match.end(),
                updated_figure,
                Action(image_id, href, alt, img_tag, updated_img),
            )
        )

    updated = content
    for start, end, replacement, _ in sorted(replacements, reverse=True):
        updated = updated[:start] + replacement + updated[end:]

    actions = [item[3] for item in sorted(replacements)]
    if len(actions) != 4:
        raise ValueError(f"Expected 4 alt changes; found {len(actions)}")
    if len(BLANK_ALT_RE.findall(updated)) != original_blank_alts - 4:
        raise ValueError("Unexpected blank-alt count after transform")
    for image_id, href, alt in TARGETS:
        if updated.count(f'alt="{alt}"') != 1:
            raise ValueError(f"Expected one final alt for image {image_id}")
    if 'wp-image-2269' not in updated or not re.search(r'<img\b[^>]*\balt=""[^>]*\bwp-image-2269\b|<img\b[^>]*\bwp-image-2269\b[^>]*\balt=""', updated, re.I | re.S):
        raise ValueError("Hero image blank alt was not preserved")

    return Result(content, updated, actions, original_blank_alts, len(BLANK_ALT_RE.findall(updated)))


def write_report(output_dir: Path, document: Document, result: Result, mode: str, apply_status: str = "not-run") -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "backup-homepage.html").write_text(document.content, encoding="utf-8")
    (output_dir / "after-homepage.html").write_text(result.updated, encoding="utf-8")
    diff = "".join(
        difflib.unified_diff(
            document.content.splitlines(keepends=True),
            result.updated.splitlines(keepends=True),
            fromfile="before/homepage.html",
            tofile="after/homepage.html",
        )
    )
    (output_dir / "homepage.diff").write_text(diff, encoding="utf-8")

    with (output_dir / "summary.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["page_id", "url", "changes", "blank_alts_before", "blank_alts_after", "apply_status"])
        writer.writerow([document.post_id, document.link, len(result.actions), result.blank_alts_before, result.blank_alts_after, apply_status])

    lines = [
        "# トップページ・カテゴリーボタンalt更新",
        "",
        f"- モード: {mode}",
        f"- 固定ページID: `{document.post_id}`",
        f"- URL: {document.link}",
        f"- 変更数: **{len(result.actions)}**",
        f"- 空alt: **{result.blank_alts_before} → {result.blank_alts_after}**",
        f"- apply結果: **{apply_status}**",
        "",
    ]
    for action in result.actions:
        lines += [
            f"## wp-image-{action.image_id}",
            "",
            f"- リンク先: {action.href}",
            f"- alt: `{action.alt}`",
            "",
            "変更前:",
            "```html",
            action.before,
            "```",
            "",
            "変更後:",
            "```html",
            action.after,
            "```",
            "",
        ]
    (output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def apply_with_rollback(site_url: str, user: str, app_password: str, document: Document, result: Result) -> None:
    header = make_auth_header(user, app_password)
    endpoint = endpoint_for(site_url)
    updated = False
    try:
        request_json(endpoint, method="POST", auth_header=header, payload={"content": result.updated})
        updated = True
        refreshed = fetch_document(site_url, user, app_password)
        if refreshed.content != result.updated:
            raise RuntimeError("Post-apply content did not match the approved dry-run content")
        if transform_after_apply(refreshed.content) is not True:
            raise RuntimeError("Post-apply alt verification failed")
    except Exception:
        if updated:
            request_json(endpoint, method="POST", auth_header=header, payload={"content": document.content})
        raise


def transform_after_apply(content: str) -> bool:
    for image_id, href, alt in TARGETS:
        token = f"wp-image-{image_id}"
        matching = [m.group(0) for m in FIGURE_RE.finditer(content) if token in m.group(0) and f'href="{href}"' in m.group(0)]
        if len(matching) != 1:
            return False
        imgs = [m.group(0) for m in IMG_RE.finditer(matching[0]) if token in m.group(0)]
        if len(imgs) != 1 or f'alt="{alt}"' not in imgs[0]:
            return False
    return True


def credentials(args) -> tuple[str, str]:
    user = args.wp_user or os.environ.get("TSURIKUE_WP_USER")
    password = args.wp_app_password or os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("WordPress credentials are required")
    return user, password


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("authenticated-dry-run", "apply"), default="authenticated-dry-run")
    parser.add_argument("--site-url", default=SITE_URL)
    parser.add_argument("--output-dir", type=Path, default=Path("reports/tsurikue-home-category-alt"))
    parser.add_argument("--apply-confirmation", default="")
    parser.add_argument("--wp-user")
    parser.add_argument("--wp-app-password")
    args = parser.parse_args()

    if args.mode == "apply" and args.apply_confirmation != APPLY_CONFIRMATION:
        raise SystemExit(f"apply mode requires confirmation string {APPLY_CONFIRMATION}")

    user, password = credentials(args)
    try:
        document = fetch_document(args.site_url, user, password)
        result = transform(document.content)
        write_report(args.output_dir, document, result, args.mode)
        if args.mode == "apply":
            apply_with_rollback(args.site_url, user, password, document, result)
            write_report(args.output_dir, document, result, args.mode, "updated-and-verified")
    except urllib.error.HTTPError as error:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "connection-error.txt").write_text(f"HTTP {error.code}", encoding="utf-8")
        raise
    except urllib.error.URLError as error:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        reason = getattr(error, "reason", None)
        (args.output_dir / "connection-error.txt").write_text(f"URLError: {type(reason).__name__}", encoding="utf-8")
        raise

    print(f"Mode: {args.mode}")
    print(f"Page ID: {PAGE_ID}")
    print("Changes: 4")
    print(f"Report: {args.output_dir / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
