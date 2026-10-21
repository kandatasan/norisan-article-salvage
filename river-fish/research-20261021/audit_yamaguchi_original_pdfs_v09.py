#!/usr/bin/env python3
"""Read-only primary PDF audit for the 10 Yamaguchi research-excerpt rows.

Machine text inspection only; NO automatic source_text_checked promotion.
Only PDF metadata, SHA256 and token PAGE NUMBERS are saved (no survey sites,
coordinates, full text, fish-to-river publication records or PDF copies).
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import subprocess
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

PDFS = {
    "YA07": {
        "url": "https://www.pref.yamaguchi.lg.jp/uploaded/attachment/197780.pdf",
        "sha256": "41d78a5ebb002543667ac2b373ea7fbf275f0eb0748ab40fb64a67326ab8aef5",
        "expected_pages": 87,
        "tokens": {"fish_term": "ヌマムツ", "named_river_term": "小島川",
                   "watershed_term": "長沢川", "year_2005": "2005", "year_2007": "2007"},
    },
    "YA04": {
        "url": "https://www.pref.yamaguchi.lg.jp/uploaded/attachment/197775.pdf",
        "sha256": "fb395e4d98b92bc6f33c50c312b42a5bcb9e56a94a5ac1d8af6d0af52264f29d",
        "expected_pages": 173,
        "tokens": {"fish_term": "オオクチバス", "table_reference": "表3"},
    },
}
MAX_BYTES = 30_000_000
MAX_TEXT_BYTES = 12_000_000
SCHEMA = "tsurikue-yamaguchi-original-research-pdf-machine-audit-v09"


def validate_url(url):
    p = urlsplit(url)
    if (p.scheme != "https" or p.hostname != "www.pref.yamaguchi.lg.jp"
            or not re.fullmatch(r"/uploaded/attachment/1977(?:80|75)\.pdf", p.path)
            or p.username or p.password or p.query or p.fragment):
        raise ValueError("Unexpected Yamaguchi official PDF URL")


def download(url):
    validate_url(url)
    req = Request(url, headers={"User-Agent": "tsurikue-fish-primary-source-audit/0.9",
                                "Accept": "application/pdf"})
    with urlopen(req, timeout=120) as response:
        if response.status != 200 or response.url != url:
            raise ValueError("Official PDF redirected or unavailable")
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES or len(raw) < 1000 or not raw.startswith(b"%PDF-"):
        raise ValueError("PDF content unexpectedly sized or not a PDF")
    return raw


def text_page_hits(text, tokens):
    if not isinstance(text, str) or not text:
        return {label: [] for label in tokens}, 0
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    results = {}
    for label, token in tokens.items():
        results[label] = [i + 1 for i, page in enumerate(pages)
                          if token in re.sub(r"\s+", "", page)]
    return results, sum(bool(x.strip()) for x in pages)


def scan(source_id, raw, text, pdf_page_count):
    if source_id not in PDFS:
        raise ValueError("Unexpected source ID")
    hits, text_pages = text_page_hits(text, PDFS[source_id]["tokens"])
    return {
        "source_id": source_id,
        "source_url": PDFS[source_id]["url"],
        "sha256": hashlib.sha256(raw).hexdigest(),
        "pdf_bytes": len(raw),
        "pdf_pages": pdf_page_count,
        "machine_text_pages": text_pages,
        "keyword_page_numbers_not_sampling_sites": hits,
        "text_extraction_status": ("no_extractable_text" if not text_pages
                                   else "keywords_partially_detected" if any(not v for v in hits.values())
                                   else "all_screening_keywords_detected"),
        "original_human_read_verified": False,
        "staged_source_rows_promoted": 0,
        "approved_for_publication": False,
    }


def extract_text(pdf_path):
    proc = subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", str(pdf_path), "-"],
                          capture_output=True, timeout=180, check=True)
    if len(proc.stdout) > MAX_TEXT_BYTES:
        raise ValueError("PDF text extraction unexpectedly large")
    return proc.stdout.decode("utf-8", errors="replace")


def page_count(pdf_path):
    proc = subprocess.run(["pdfinfo", str(pdf_path)], capture_output=True,
                          text=True, timeout=60, check=True)
    m = re.search(r"^Pages:\s*(\d+)\s*$", proc.stdout, flags=re.MULTILINE)
    if not m or not (1 <= int(m.group(1)) <= 500):
        raise ValueError("Unexpected PDF page count")
    return int(m.group(1))


def main():
    import tempfile
    from pathlib import Path
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        raise FileExistsError("Refuse to overwrite original PDF review")
    result = []
    with tempfile.TemporaryDirectory(prefix="yamaguchi-fish-original-") as tmp:
        for source_id in ("YA07", "YA04"):
            raw = download(PDFS[source_id]["url"])
            if hashlib.sha256(raw).hexdigest() != PDFS[source_id]["sha256"]:
                raise ValueError("Original prefecture PDF changed; stop for manual review")
            path = Path(tmp) / (source_id + ".pdf")
            path.write_bytes(raw)
            pages = page_count(path)
            if pages != PDFS[source_id]["expected_pages"]:
                raise ValueError("Original PDF page count changed; stop for manual review")
            result.append(scan(source_id, raw, extract_text(path), pages))
            path.unlink()
    report = {
        "schema": SCHEMA,
        "status": "MACHINE_PDF_TEXT_SCAN_ONLY_NOT_VERIFIED_NOT_PUBLISHED",
        "source_records_pending_manual_review": 10,
        "source_records_automatically_approved": 0,
        "files": result,
        "notice": "キーワード検出だけでは資料の表・図・対象河川・観測年を確認したことにはならない。元の10行はsearch_excerpt_onlyのまま。",
        "site_updated": False,
    }
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("YAMAGUCHI_ORIGINAL_PDF_V09", json.dumps({
        "sources": [{k: r[k] for k in ("source_id", "sha256", "pdf_pages",
                                      "machine_text_pages", "text_extraction_status")}
                    for r in result],
        "rows_promoted": 0, "site_updated": False
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
