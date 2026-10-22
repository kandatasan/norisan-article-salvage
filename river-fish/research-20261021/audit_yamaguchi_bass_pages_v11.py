#!/usr/bin/env python3
"""Render only two pinned official Yamaguchi PDF pages for manual table review."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

SOURCE_URL = "https://www.pref.yamaguchi.lg.jp/uploaded/attachment/197775.pdf"
SOURCE_SHA256 = "fb395e4d98b92bc6f33c50c312b42a5bcb9e56a94a5ac1d8af6d0af52264f29d"
EXPECTED_PAGES = 173
REVIEW_PAGES = (125, 126)
MAX_BYTES = 30_000_000

def validate_source(url: str = SOURCE_URL) -> None:
    parts = urlsplit(url)
    if (parts.scheme != "https" or parts.hostname != "www.pref.yamaguchi.lg.jp"
            or parts.path != "/uploaded/attachment/197775.pdf"
            or parts.query or parts.fragment or parts.username or parts.password):
        raise ValueError("Unexpected official Yamaguchi source URL")

def review_pdf(raw: bytes, page_count: int) -> dict:
    digest = hashlib.sha256(raw).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError("Official PDF SHA256 changed; stop for review")
    if page_count != EXPECTED_PAGES:
        raise ValueError("Official PDF page count changed; stop for review")
    return {
        "schema": "tsurikue-yamaguchi-bass-table-review-v11",
        "status": "PINNED_SOURCE_PAGE_IMAGES_FOR_MANUAL_SCOPE_REVIEW",
        "source_id": "YA04", "source_url": SOURCE_URL, "source_sha256": digest,
        "pdf_pages": page_count, "reviewed_pdf_pages": list(REVIEW_PAGES),
        "expected_table_reference": "表3", "expected_species_label": "オオクチバス",
        "page_image_files": [f"YA04-{page}.png" for page in REVIEW_PAGES],
        "source_rows_changed": 0, "approved_for_publication": False,
        "site_updated": False, "human_review_required": True,
        "notice": "原本の対象ページ画像。表の掲載範囲は目視確認が必要。魚類候補の自動変更や公開承認はしない。",
    }

def download_pdf() -> bytes:
    validate_source()
    req = Request(SOURCE_URL, headers={"User-Agent": "tsurikue-yamaguchi-fish-source-review/1.1",
                                       "Accept": "application/pdf"})
    with urlopen(req, timeout=120) as response:
        if response.status != 200 or response.url != SOURCE_URL:
            raise ValueError("Official PDF redirected or unavailable")
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES or len(raw) < 1000 or not raw.startswith(b"%PDF-"):
        raise ValueError("Unexpected PDF size or content")
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("Official PDF SHA256 changed; stop for review")
    return raw

def count_pages(pdf_path: Path) -> int:
    proc = subprocess.run(["pdfinfo", str(pdf_path)], capture_output=True, text=True,
                          timeout=60, check=True)
    match = re.search(r"^Pages:\s*(\d+)\s*$", proc.stdout, flags=re.MULTILINE)
    if not match or not 1 <= int(match.group(1)) <= 500:
        raise ValueError("Unexpected PDF page count")
    return int(match.group(1))

def render_review_pages(pdf_path: Path, output_dir: Path) -> list[str]:
    prefix = output_dir / "YA04"
    subprocess.run(
        ["pdftoppm", "-f", str(REVIEW_PAGES[0]), "-l", str(REVIEW_PAGES[-1]),
         "-r", "180", "-png", str(pdf_path), str(prefix)],
        capture_output=True, timeout=120, check=True)
    files = [f"YA04-{page}.png" for page in REVIEW_PAGES]
    for name in files:
        path = output_dir / name
        if not path.is_file() or path.stat().st_size < 10_000:
            raise ValueError("Expected official page image missing or too small: " + name)
    return files

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.out_dir.exists():
        raise FileExistsError("Refuse to overwrite an existing source review artifact")
    raw = download_pdf()
    args.out_dir.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix="ya04-table-review-") as tmp:
        pdf_path = Path(tmp) / "YA04.pdf"
        pdf_path.write_bytes(raw)
        pages = count_pages(pdf_path)
        result = review_pdf(raw, pages)
        result["page_image_files"] = render_review_pages(pdf_path, args.out_dir)
    (args.out_dir / "review.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("YAMAGUCHI_BASS_TABLE_REVIEW_V11", json.dumps({
        "source_id": result["source_id"], "pages": result["reviewed_pdf_pages"],
        "page_images": len(result["page_image_files"]),
        "rows_changed": result["source_rows_changed"],
        "approved": result["approved_for_publication"]}, ensure_ascii=False), flush=True)

if __name__ == "__main__":
    main()
