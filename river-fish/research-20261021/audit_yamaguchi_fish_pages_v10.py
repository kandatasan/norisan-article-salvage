#!/usr/bin/env python3
"""Extract a bounded fish-record passage from one pinned Yamaguchi PDF page.

The output is a source-review aid, not an approval. It stores only the short
sentence span connecting the species to the two named rivers and years; it
never stores the full PDF, full page, coordinates, or sampling-site codes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

from audit_yamaguchi_original_pdfs_v09 import PDFS, download, page_count

SOURCE_ID = "YA07"
SOURCE_PDF_PAGE = 50
REQUIRED_TERMS = ("ヌマムツ", "2005", "佐波川", "小島川", "2007", "山口湾", "長沢川")
SCHEMA = "tsurikue-yamaguchi-fish-page-review-v10"
STATUS = "SOURCE_TEXT_EXCERPT_FOR_MANUAL_SCOPE_REVIEW"


def extract_pdf_page_text(pdf_path: Path, page: int) -> str:
    if page < 1 or page > 500:
        raise ValueError("Unexpected PDF page number")
    result = subprocess.run(
        ["pdftotext", "-f", str(page), "-l", str(page), "-layout",
         "-enc", "UTF-8", str(pdf_path), "-"],
        capture_output=True, timeout=60, check=True,
    )
    if len(result.stdout) > 1_000_000:
        raise ValueError("Single-page text extraction unexpectedly large")
    return result.stdout.decode("utf-8", errors="replace")


def extract_target_excerpt(page_text: str) -> str:
    normalized = re.sub(r"\s+", "", page_text or "")
    if not normalized:
        raise ValueError("Target PDF page has no extractable text")
    for match in re.finditer("ヌマムツ", normalized):
        start = normalized.rfind("。", 0, match.start()) + 1
        river_end = normalized.find("長沢川", match.start())
        if river_end < 0:
            continue
        end = normalized.find("。", river_end)
        if end < 0:
            end = len(normalized) - 1
        excerpt = normalized[start:end + 1]
        if all(term in excerpt for term in REQUIRED_TERMS):
            if len(excerpt) > 700:
                raise ValueError("Target evidence span unexpectedly long")
            if re.search(r"(北緯|東経|座標|[0-9]{2,3}°)", excerpt):
                raise ValueError("Target evidence span contains coordinate-like detail")
            return excerpt
    raise ValueError("Could not isolate the target fish/rivers/years in one short span")


def build_review(raw_pdf: bytes, extracted_page_text: str, pages: int) -> dict:
    expected = PDFS[SOURCE_ID]
    if hashlib.sha256(raw_pdf).hexdigest() != expected["sha256"]:
        raise ValueError("Pinned official PDF SHA256 mismatch")
    if pages != expected["expected_pages"]:
        raise ValueError("Pinned official PDF page count mismatch")
    excerpt = extract_target_excerpt(extracted_page_text)
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "source_id": SOURCE_ID,
        "source_url": expected["url"],
        "source_sha256": expected["sha256"],
        "pdf_page_number": SOURCE_PDF_PAGE,
        "excerpt_kind": "short_species_record_sentence_span",
        "excerpt": excerpt,
        "source_claims_visible_in_excerpt": {
            "species": "ヌマムツ",
            "2005_record_wording": "佐波川水系小島川",
            "2007_record_wording": "山口湾に流入する長沢川",
        },
        "human_review_required": True,
        "source_rows_changed": 0,
        "approved_for_publication": False,
        "site_updated": False,
        "notice": "短い原本テキスト抜粋による確認補助。調査地点・座標は保存せず、魚記録の公開承認も行わない。",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError("Refuse to overwrite review output")
    with tempfile.TemporaryDirectory(prefix="yamaguchi-fish-page-v10-") as tmp:
        raw = download(PDFS[SOURCE_ID]["url"])
        if hashlib.sha256(raw).hexdigest() != PDFS[SOURCE_ID]["sha256"]:
            raise ValueError("Official PDF changed; stop for manual review")
        pdf_path = Path(tmp) / "YA07.pdf"
        pdf_path.write_bytes(raw)
        pages = page_count(pdf_path)
        page_text = extract_pdf_page_text(pdf_path, SOURCE_PDF_PAGE)
        review = build_review(raw, page_text, pages)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("YAMAGUCHI_FISH_PAGE_REVIEW_V10", json.dumps({
        "source_id": review["source_id"],
        "pdf_page_number": review["pdf_page_number"],
        "status": review["status"],
        "human_review_required": review["human_review_required"],
        "source_rows_changed": review["source_rows_changed"],
        "approved_for_publication": review["approved_for_publication"],
        "site_updated": review["site_updated"],
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
