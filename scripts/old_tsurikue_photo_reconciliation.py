#!/usr/bin/env python3
"""GET-only photo reconciliation for the 46 old tsurikue.com salvage targets."""
from __future__ import annotations

import argparse
import base64
import csv
import io
import json
import os
import re
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from PIL import Image

HERE = Path(__file__).resolve().parent
TARGETS_FILE = HERE / "old_tsurikue_targets.json"
ARCHIVES_FILE = HERE / "old_tsurikue_archives.json"
EXPECTED_TARGETS = 46
USER_AGENT = "old-tsurikue-photo-reconciliation/1.0"
HASH_STRONG_MAX = 6
HASH_CANDIDATE_MAX = 12
HASH_STRONG_MARGIN = 4
MAX_HASH_CANDIDATES = 12

NOISE_RE = re.compile(
    r"(?:avatar|gravatar|profile|author|logo|icon|sns|social|facebook|twitter|x-logo|line|hatena|pocket|advert|affiliate|tracking|pixel|1x1|(?:^|[./_-])ads?(?:[./_-]|$))",
    re.I,
)
CONTENT_RE = re.compile(r"(?:post[_-]?content|entry[_-]?content|c-postContent|article[_-]?body|articleBody)", re.I)
LEXUS_RE = re.compile(r"(?:lexus-diary\.com|(?:^|[./_-])lexus(?:[./_-]|$))", re.I)
WAYBACK_RE = re.compile(r"^https?://web\.archive\.org/web/(\d+)(?:[a-z_]+)?/(.+)$", re.I)
SIZE_SUFFIX_RE = re.compile(r"-\d{2,5}x\d{2,5}$", re.I)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_inputs(targets_path: Path = TARGETS_FILE, archives_path: Path = ARCHIVES_FILE) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    targets = load_json(targets_path)
    archives_rows = load_json(archives_path)
    if not isinstance(targets, list) or len(targets) != EXPECTED_TARGETS:
        raise ValueError(f"target manifest must contain exactly {EXPECTED_TARGETS} rows")
    if not isinstance(archives_rows, list) or len(archives_rows) != EXPECTED_TARGETS:
        raise ValueError(f"archive map must contain exactly {EXPECTED_TARGETS} rows")
    target_slugs = [row.get("slug") for row in targets]
    archive_slugs = [row.get("slug") for row in archives_rows]
    if len(set(target_slugs)) != EXPECTED_TARGETS or len(set(archive_slugs)) != EXPECTED_TARGETS:
        raise ValueError("duplicate slugs in target/archive inputs")
    if set(target_slugs) != set(archive_slugs):
        raise ValueError("target and archive slug sets differ")
    if any(row.get("source_site") != "tsurikue.com" for row in targets):
        raise ValueError("non-tsurikue target present")
    archive_map: dict[str, list[str]] = {}
    for row in archives_rows:
        urls = row.get("archives")
        if not isinstance(urls, list) or not urls or not all(isinstance(u, str) and u.startswith("https://web.archive.org/") for u in urls):
            raise ValueError(f"invalid archives for {row.get('slug')}")
        if any("lexus-diary.com" in u.lower() for u in urls):
            raise ValueError("Lexus archive URL present")
        archive_map[row["slug"]] = urls
    return targets, archive_map


def basic_auth(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def get_bytes(url: str, authorization: str | None = None, timeout: int = 45) -> tuple[bytes, dict[str, str]]:
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if authorization:
        headers["Authorization"] = authorization
    request = urllib.request.Request(url, headers=headers, method="GET")
    if request.method != "GET":
        raise RuntimeError("GET-only dry-run attempted a non-GET request")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(), {k.lower(): v for k, v in response.headers.items()}


def get_json(url: str, authorization: str) -> tuple[Any, dict[str, str]]:
    payload, headers = get_bytes(url, authorization)
    return json.loads(payload.decode("utf-8")), headers


def fetch_media(site_url: str, authorization: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        query = urllib.parse.urlencode(
            {
                "context": "edit",
                "status": "inherit,private",
                "per_page": "100",
                "page": str(page),
                "_fields": "id,slug,date,source_url,title,caption,alt_text,media_details",
            }
        )
        data, headers = get_json(f"{site_url.rstrip('/')}/wp-json/wp/v2/media?{query}", authorization)
        if not isinstance(data, list):
            raise ValueError("WordPress media endpoint did not return a list")
        rows.extend(data)
        pages = int(headers.get("x-wp-totalpages", "1"))
        if page >= pages:
            return rows
        page += 1


def unwrap_wayback(url: str) -> str:
    match = WAYBACK_RE.match(url)
    return match.group(2) if match else url


def normalized_filename(url: str) -> str:
    raw = unwrap_wayback(url)
    parsed = urllib.parse.urlsplit(raw)
    basename = urllib.parse.unquote(Path(parsed.path).name).strip().lower()
    if not basename:
        return ""
    stem, ext = os.path.splitext(basename)
    stem = re.sub(r"-scaled$", "", stem, flags=re.I)
    stem = SIZE_SUFFIX_RE.sub("", stem)
    return f"{stem}{ext.lower()}"


def filename_stem(url: str) -> str:
    return os.path.splitext(normalized_filename(url))[0]


def upload_year_month(url: str) -> tuple[str, str] | None:
    match = re.search(r"/wp-content/uploads/(\d{4})/(\d{2})/", unwrap_wayback(url))
    return match.groups() if match else None


def dimensions_from_media(media: dict[str, Any]) -> tuple[int, int] | None:
    details = media.get("media_details") or {}
    try:
        w, h = int(details.get("width") or 0), int(details.get("height") or 0)
    except (TypeError, ValueError):
        return None
    return (w, h) if w > 0 and h > 0 else None


def aspect_ratio(dimensions: tuple[int, int] | None) -> float | None:
    if not dimensions or dimensions[1] <= 0:
        return None
    return dimensions[0] / dimensions[1]


@dataclass
class LegacyImage:
    order: int
    url: str
    filename: str
    nearest_heading: str
    context_before: str
    context_after: str
    width: int | None = None
    height: int | None = None


class ArticleImageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.events: list[tuple[str, Any]] = []
        self.stack: list[tuple[str, bool, bool]] = []
        self.skip_depth = 0
        self.content_depth = 0
        self.article_depth = 0
        self.heading_tag: str | None = None
        self.heading_buf: list[str] = []
        self.current_heading = ""

    @staticmethod
    def _classes(attrs: dict[str, str]) -> str:
        return " ".join([attrs.get("class", ""), attrs.get("id", "")])

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = {k: (v or "") for k, v in attrs_list}
        marker = self._classes(attrs)
        skipped = tag in {"header", "footer", "nav", "aside", "script", "style", "noscript", "form"} or bool(NOISE_RE.search(marker))
        content_marker = bool(CONTENT_RE.search(marker))
        if tag == "article":
            self.article_depth += 1
        if skipped:
            self.skip_depth += 1
        if content_marker:
            self.content_depth += 1
        if tag not in {"img", "br", "hr", "meta", "link", "input", "source"}:
            self.stack.append((tag, skipped, content_marker))
        active = self.skip_depth == 0 and (self.content_depth > 0 or self.article_depth > 0)
        if not active:
            return
        if tag in {"h2", "h3"}:
            self.heading_tag = tag
            self.heading_buf = []
        if tag == "img":
            src = attrs.get("data-src") or attrs.get("data-lazy-src") or attrs.get("data-original") or attrs.get("src") or ""
            if not src or src.startswith("data:") or LEXUS_RE.search(src) or NOISE_RE.search(src):
                return
            try:
                width = int(re.sub(r"\D", "", attrs.get("width", "")) or 0) or None
                height = int(re.sub(r"\D", "", attrs.get("height", "")) or 0) or None
            except ValueError:
                width = height = None
            if width is not None and height is not None and width <= 2 and height <= 2:
                return
            self.events.append(("image", {"url": src, "heading": self.current_heading, "width": width, "height": height}))

    def handle_endtag(self, tag: str) -> None:
        if self.heading_tag == tag:
            heading = " ".join("".join(self.heading_buf).split()).strip()
            if heading:
                self.current_heading = heading[:180]
            self.heading_tag = None
            self.heading_buf = []
        if not self.stack:
            return
        open_tag, skipped, content_marker = self.stack.pop()
        if content_marker:
            self.content_depth = max(0, self.content_depth - 1)
        if skipped:
            self.skip_depth = max(0, self.skip_depth - 1)
        if open_tag == "article":
            self.article_depth = max(0, self.article_depth - 1)

    def handle_data(self, data: str) -> None:
        if self.skip_depth or not (self.content_depth > 0 or self.article_depth > 0):
            return
        clean = " ".join(data.split()).strip()
        if not clean:
            return
        if self.heading_tag:
            self.heading_buf.append(clean)
        else:
            self.events.append(("text", clean))

    def images(self, base_url: str) -> list[LegacyImage]:
        out: list[LegacyImage] = []
        image_idx = 0
        for idx, (kind, value) in enumerate(self.events):
            if kind != "image":
                continue
            image_idx += 1
            before = next((self.events[j][1][:180] for j in range(idx - 1, -1, -1) if self.events[j][0] == "text"), "")
            after = next((self.events[j][1][:180] for j in range(idx + 1, len(self.events)) if self.events[j][0] == "text"), "")
            url = urllib.parse.urljoin(base_url, value["url"])
            out.append(LegacyImage(image_idx, url, normalized_filename(url), value["heading"], before, after, value["width"], value["height"]))
        return out


def extract_images(html_bytes: bytes, archive_url: str) -> list[LegacyImage]:
    parser = ArticleImageParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    return parser.images(archive_url)


def filename_match(image_url: str, media: list[dict[str, Any]]) -> dict[str, Any] | None:
    key = normalized_filename(image_url)
    if not key:
        return None
    matches = [row for row in media if normalized_filename(row.get("source_url", "")) == key]
    return matches[0] if len(matches) == 1 else None


def media_candidates(image: LegacyImage, media: list[dict[str, Any]], limit: int = MAX_HASH_CANDIDATES) -> list[dict[str, Any]]:
    legacy_stem = filename_stem(image.url)
    legacy_ym = upload_year_month(image.url)
    legacy_ratio = aspect_ratio((image.width, image.height)) if image.width and image.height else None
    scored: list[tuple[int, int, dict[str, Any]]] = []
    for row in media:
        src = row.get("source_url", "")
        if not src or LEXUS_RE.search(src):
            continue
        score = 0
        stem = filename_stem(src)
        if legacy_stem and stem == legacy_stem:
            score += 6
        elif legacy_stem and stem and (legacy_stem in stem or stem in legacy_stem):
            score += 3
        if legacy_ym and upload_year_month(src) == legacy_ym:
            score += 3
        mr = aspect_ratio(dimensions_from_media(row))
        if legacy_ratio is not None and mr is not None and abs(legacy_ratio - mr) <= 0.03 * max(legacy_ratio, mr):
            score += 2
        if score:
            scored.append((score, int(row.get("id") or 0), row))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [row for _, _, row in scored[:limit]]


def dhash_bytes(payload: bytes) -> int:
    with Image.open(io.BytesIO(payload)) as image:
        gray = image.convert("L").resize((9, 8))
        pixels = list(gray.getdata())
    bits = 0
    for y in range(8):
        row = pixels[y * 9 : (y + 1) * 9]
        for x in range(8):
            bits = (bits << 1) | int(row[x] > row[x + 1])
    return bits


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def classify_hash_distances(distances: list[int]) -> str:
    if not distances:
        return "PLACEHOLDER"
    ordered = sorted(distances)
    best = ordered[0]
    second = ordered[1] if len(ordered) > 1 else None
    if best <= HASH_STRONG_MAX and (second is None or second - best >= HASH_STRONG_MARGIN):
        return "MATCH_HASH_STRONG"
    if best <= HASH_CANDIDATE_MAX:
        return "CANDIDATE_HASH"
    return "PLACEHOLDER"


def wayback_image_url(article_archive_url: str, image_url: str) -> str:
    if image_url.startswith("//web.archive.org/"):
        return "https:" + image_url
    if image_url.startswith("http://web.archive.org/") or image_url.startswith("https://web.archive.org/"):
        return image_url
    match = re.search(r"/web/(\d+)", article_archive_url)
    if not match:
        return image_url
    absolute = urllib.parse.urljoin(unwrap_wayback(article_archive_url), image_url)
    return f"https://web.archive.org/web/{match.group(1)}im_/{absolute}"


def placeholder(image: LegacyImage) -> str:
    context = " / ".join(x for x in [image.context_before, image.context_after] if x)[:220]
    return f"【写真差し込み：旧画像{image.order} / {image.filename or 'filename不明'} / {context or '前後文脈なし'}】"


def blank_row(slug: str, archive_url: str, result: str, reason: str) -> dict[str, Any]:
    return {"target_slug": slug, "archive_url": archive_url, "nearest_heading": "", "image_order": 0, "legacy_image_url": "", "legacy_filename": "", "context_before": "", "context_after": "", "result": result, "matched_media_id": None, "matched_media_source_url": None, "hash_distance": None, "confidence_reason": reason, "placeholder_text": ""}


def reconcile_one(slug: str, archive_urls: list[str], media: list[dict[str, Any]]) -> tuple[bool, list[dict[str, Any]]]:
    article_url = ""
    images: list[LegacyImage] | None = None
    last_error = ""
    for candidate in archive_urls:
        try:
            html_bytes, _ = get_bytes(candidate)
            article_url, images = candidate, extract_images(html_bytes, candidate)
            break
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
    if images is None:
        return False, [blank_row(slug, archive_urls[0], "ARCHIVE_UNAVAILABLE", last_error or "archive unavailable")]
    rows: list[dict[str, Any]] = []
    for image in images:
        row = blank_row(slug, article_url, "PLACEHOLDER", "no confident match")
        row.update({"nearest_heading": image.nearest_heading, "image_order": image.order, "legacy_image_url": image.url, "legacy_filename": image.filename, "context_before": image.context_before, "context_after": image.context_after, "placeholder_text": placeholder(image)})
        fm = filename_match(image.url, media)
        if fm is not None:
            row.update({"result": "MATCH_FILENAME", "matched_media_id": fm.get("id"), "matched_media_source_url": fm.get("source_url"), "confidence_reason": "unique normalized filename match", "placeholder_text": ""})
            rows.append(row)
            continue
        candidates = media_candidates(image, media)
        if not candidates:
            rows.append(row)
            continue
        try:
            legacy_bytes, _ = get_bytes(wayback_image_url(article_url, image.url))
            legacy_hash = dhash_bytes(legacy_bytes)
        except Exception as exc:
            row["confidence_reason"] = f"legacy image unavailable: {type(exc).__name__}"
            rows.append(row)
            continue
        hashes: list[tuple[int, dict[str, Any]]] = []
        for candidate in candidates:
            try:
                payload, _ = get_bytes(candidate.get("source_url", ""))
                hashes.append((hamming(legacy_hash, dhash_bytes(payload)), candidate))
            except Exception:
                continue
        hashes.sort(key=lambda item: item[0])
        classification = classify_hash_distances([d for d, _ in hashes])
        if hashes:
            best_distance, best_media = hashes[0]
            row["hash_distance"] = best_distance
            row["matched_media_id"] = best_media.get("id")
            row["matched_media_source_url"] = best_media.get("source_url")
        row["result"] = classification
        if classification == "MATCH_HASH_STRONG":
            row["confidence_reason"] = "conservative dHash threshold and separation margin satisfied"
            row["placeholder_text"] = ""
        elif classification == "CANDIDATE_HASH":
            row["confidence_reason"] = "similar candidate found but not safe for automatic insertion"
        rows.append(row)
    return True, rows


def build_report(targets: list[dict[str, Any]], archives: dict[str, list[str]], media: list[dict[str, Any]]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    article_ok = 0
    article_failed = 0
    for target in targets:
        ok, rows = reconcile_one(target["slug"], archives[target["slug"]], media)
        article_ok += int(ok)
        article_failed += int(not ok)
        results.extend(rows)
    counts = Counter(row["result"] for row in results)
    image_refs = sum(1 for row in results if int(row.get("image_order") or 0) > 0)
    return {"mode": "authenticated-photo-reconciliation-dry-run", "targets": len(targets), "lexus_targets": 0, "live_media_count": len(media), "archive_articles_ok": article_ok, "archive_articles_failed": article_failed, "archive_image_refs": image_refs, "MATCH_FILENAME": counts["MATCH_FILENAME"], "MATCH_HASH_STRONG": counts["MATCH_HASH_STRONG"], "CANDIDATE_HASH": counts["CANDIDATE_HASH"], "PLACEHOLDER": counts["PLACEHOLDER"], "ARCHIVE_UNAVAILABLE": counts["ARCHIVE_UNAVAILABLE"], "wordpress_write_count": 0, "results": results}


def write_artifacts(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = ["target_slug", "archive_url", "nearest_heading", "image_order", "legacy_image_url", "legacy_filename", "context_before", "context_after", "result", "matched_media_id", "matched_media_source_url", "hash_distance", "confidence_reason", "placeholder_text"]
    with (output_dir / "result.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["results"])
    summary_keys = ["targets", "lexus_targets", "live_media_count", "archive_articles_ok", "archive_articles_failed", "archive_image_refs", "MATCH_FILENAME", "MATCH_HASH_STRONG", "CANDIDATE_HASH", "PLACEHOLDER", "ARCHIVE_UNAVAILABLE", "wordpress_write_count"]
    lines = ["# 旧つりくえ！46記事 写真・アーカイブ照合 dry-run", ""] + [f"- {key}: **{report[key]}**" for key in summary_keys]
    lines += ["", "| slug | # | filename | result | media | heading |", "|---|---:|---|---|---|---|"]
    for row in report["results"]:
        media_text = f"#{row['matched_media_id']}" if row.get("matched_media_id") else "—"
        lines.append(f"| `{row['target_slug']}` | {row['image_order']} | {row['legacy_filename'].replace('|','｜')} | `{row['result']}` | {media_text} | {row['nearest_heading'].replace('|','｜')} |")
    (output_dir / "result.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-url", default="https://tsurikue.com")
    parser.add_argument("--targets", type=Path, default=TARGETS_FILE)
    parser.add_argument("--archives", type=Path, default=ARCHIVES_FILE)
    parser.add_argument("--output-dir", type=Path, default=Path("reports/old-tsurikue-photo-reconciliation"))
    args = parser.parse_args()
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    targets, archives = load_inputs(args.targets, args.archives)
    media = fetch_media(args.site_url, basic_auth(user, password))
    report = build_report(targets, archives, media)
    write_artifacts(args.output_dir, report)
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
