#!/usr/bin/env python3
"""Read only the Yamaguchi Report No. 04 black-bass table pages for scope review."""
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
WATERSHEDS = ("錦川", "島田川", "佐波川", "椹野川", "厚東川", "厚狭川", "木屋川", "阿武川")
MAX_BYTES = 30_000_000


def validate_source(url: str = SOURCE_URL) -> None:
    parts = urlsplit(url)
    if (parts.scheme != "https" or parts.hostname != "www.pref.yamaguchi.lg.jp"
            or parts.path != "/uploaded/attachment/197775.pdf"
            or parts.query or parts.fragment or parts.username or parts.password):
        raise ValueError("Unexpected official Yamaguchi source URL")


def extract_table_excerpt(page_text: str) -> str:
    if not isinstance(page_text, str) or not page_text.strip():
        raise ValueError("No extractable text on the reviewed pages")
    normalized = re.sub(r"[ \t\r\n]+", " ", page_text).strip()
    start_match = re.search(r"表\s*[-‐－]?\s*[3３]", normalized)
    if not start_match:
        raise ValueError("Table 3 heading not found on pinned pages")
    end_match = re.search(r"表\s*[-‐－]?\s*[4４]", normalized[start_match.end():])
    end = start_match.end() + end_match.start() if end_match else len(normalized)
    excerpt = normalized[start_match.start():end].strip()
    compact = re.sub(r"\s+", "", excerpt)
    if len(excerpt) > 10_000:
        raise ValueError("Table excerpt exceeds the review bound")
    if "オオクチバス" not in compact:
        raise ValueError("Black bass label not found within the Table 3 excerpt")
    missing = [name for name in WATERSHEDS if name not in compact]
    if missing:
        raise ValueError("Expected watershed names missing from Table 3 excerpt: " + ",".join(missing))
    return excerpt


def review_pdf(raw: bytes, page_text: str, page_count: int) -> dict:
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("Official PDF SHA256 changed; stop for review")
    if page_count != EXPECTED_PAGES:
        raise ValueError("Official PDF page count changed; stop for review")
    excerpt = extract_table_excerpt(page_text)
    return {
        "schema": "tsurikue-yamaguchi-bass-table-review-v11",
        "status": "SOURCE_TABLE_EXCERPT_FOR_MANUAL_SCOPE_REVIEW",
        "source_id": "YA04",
        "source_url": SOURCE_URL,
        "source_sha256": SOURCE_SHA256,
        "pdf_pages": page_count,
        "reviewed_pdf_pages": list(REVIEW_PAGES),
        "table_reference": "表3",
        "species_term": "オオクチバス",
        "candidate_watershed_terms_present": list(WATERSHEDS),
        "excerpt": excerpt,
        "source_rows_changed": 0,
        "approved_for_publication": False,
        "site_updated": False,
        "human_review_required": True,
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


def extract_review_pages(pdf_path: Path) -> str:
    proc = subprocess.run(
        ["pdftotext", "-layout", "-f", str(REVIEW_PAGES[0]), "-l", str(REVIEW_PAGES[-1]),
         "-enc", "UTF-8", str(pdf_path), "-"],
        capture_output=True, timeout=90, check=True,
    )
    return proc.stdout.decode("utf-8", errors="replace")


def count_pages(pdf_path: Path) -> int:
    proc = subprocess.run(["pdfinfo", str(pdf_path)], capture_output=True, text=True,
                          timeout=60, check=True)
    match = re.search(r"^Pages:\s*(\d+)\s*$", proc.stdout, flags=re.MULTILINE)
    if not match or not 1 <= int(match.group(1)) <= 500:
        raise ValueError("Unexpected PDF page count")
    return int(match.group(1))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError("Refuse to overwrite an existing source review artifact")
    raw = download_pdf()
    with tempfile.TemporaryDirectory(prefix="ya04-table-review-") as tmp:
        pdf_path = Path(tmp) / "YA04.pdf"
        pdf_path.write_bytes(raw)
        pages = count_pages(pdf_path)
        text = extract_review_pages(pdf_path)
    result = review_pdf(raw, text, pages)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("YAMAGUCHI_BASS_TABLE_REVIEW_V11", json.dumps({
        "source_id": result["source_id"], "pages": result["reviewed_pdf_pages"],
        "water_names": len(result["candidate_watershed_terms_present"]),
        "rows_changed": result["source_rows_changed"],
        "approved": result["approved_for_publication"],
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
