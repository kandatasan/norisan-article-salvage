#!/usr/bin/env python3
"""Fetch a fixed public supplement and emit workbook schema metadata only."""
import hashlib
import io
import json
import re
import urllib.request
import zipfile
from pathlib import PurePosixPath

URL = "https://onlinelibrary.wiley.com/action/downloadSupplement?doi=10.1002%2Fedn3.70292&file=edn370292-sup-0001-supinfo.zip"
MAX_BYTES = 8_000_000


def inspect(raw):
    if len(raw) > MAX_BYTES or len(raw) < 1000:
        raise ValueError("Unexpected supplement size")
    result = {"schema": "national-black-bass-edna-supplement-schema-v01",
              "doi": "10.1002/edn3.70292", "sha256": hashlib.sha256(raw).hexdigest(),
              "bytes": len(raw), "members": [], "workbooks": []}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if archive.testzip() is not None:
            raise ValueError("Supplement ZIP CRC failure")
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            if path.is_absolute() or ".." in path.parts or "\\" in item.filename:
                raise ValueError("Unsafe supplement member")
            if item.is_dir():
                continue
            result["members"].append({"name": path.name, "bytes": item.file_size})
        books = [x for x in archive.infolist() if not x.is_dir() and x.filename.lower().endswith(".xlsx")]
        if not books:
            raise ValueError("Supplement has no XLSX workbook")
        from openpyxl import load_workbook
        for item in books:
            workbook = load_workbook(io.BytesIO(archive.read(item)), read_only=True, data_only=True)
            sheets = []
            for sheet in workbook.worksheets:
                # Emit only recognisable header labels, never a data row or sample name.
                header_rows = []
                for row_number, cells in enumerate(sheet.iter_rows(min_row=1, max_row=min(sheet.max_row or 1, 30)), 1):
                    values = [str(c.value).strip() if c.value is not None else "" for c in cells]
                    hits = [(i + 1, v) for i, v in enumerate(values)
                            if re.search(r"^(prefecture|site(?:\s*(?:id|no\.?|name))?|sample(?:\s*(?:id|name))?|"
                                         r"water\s*body|waterbody|river|lake|species|presence|absence|"
                                         r"micropterus(?:\s+.*)?|northern\s+bass|florida\s+bass|smallmouth\s+bass)$",
                                         v, re.I)]
                    if len(hits) >= 2:
                        header_rows.append({"row": row_number, "labels": hits})
                sheets.append({"name": sheet.title, "rows": sheet.max_row,
                               "columns": sheet.max_column, "header_candidates": header_rows[:5]})
            result["workbooks"].append({"name": PurePosixPath(item.filename).name, "sheets": sheets})
            workbook.close()
    return result


def fetch():
    request = urllib.request.Request(URL, headers={
        "User-Agent": "tsurikue-national-edna-source-inspection/1.0",
        "Accept": "application/zip,*/*;q=0.8",
        "Referer": "https://onlinelibrary.wiley.com/doi/10.1002/edn3.70292",
    })
    with urllib.request.urlopen(request, timeout=90) as response:
        if response.status != 200 or response.geturl().split("/", 3)[2] not in {
                "onlinelibrary.wiley.com", "onlinelibrary.wiley.com:443"}:
            raise ValueError("Publisher response left the pinned public host")
        raw = response.read(MAX_BYTES + 1)
    return inspect(raw)


if __name__ == "__main__":
    print("NATIONAL_EDNA_SUPPLEMENT_SCHEMA", json.dumps(fetch(), ensure_ascii=False))
