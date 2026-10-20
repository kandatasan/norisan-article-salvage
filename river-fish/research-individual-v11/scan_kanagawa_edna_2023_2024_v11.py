#!/usr/bin/env python3
"""Official Kanagawa 2023/2024 eDNA workbook acquisition and schema scout.

Read-only: original Excel bytes are downloaded into memory only. No exact
sampling location, coordinates, sample identifier, or personal data exported.
This step DOES NOT promote any eDNA result to fish-capture evidence.
"""
from __future__ import annotations
from collections import Counter
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile
import hashlib
import json
import posixpath
import re
import urllib.request

BASE = "https://www.pref.kanagawa.jp/documents/97797/"
SOURCES = {
    "2023_source_fish": "r5_kenmin_gyorui.xlsx",
    "2023_source_insects": "r5_kenmin_mtinsects-16s.xlsx",
    "2023_prefecturewide_fish": "r5_project_gyorui.xlsx",
    "2024_source_vertebrates_invertebrates": "r6_kenmin_mtinsects_amphi.xlsx",
    "2024_prefecturewide_vertebrates_invertebrates": "r6_project_mtinsects-amphi.xlsx",
}
N = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
SAFE_COLS = list("ABCDEFGHIJKLM")
OUT = Path(__file__).resolve().parent / "outputs"

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Tsurikue-river-biota-research/1.1"})
    with urllib.request.urlopen(req, timeout=90) as response:
        if response.status != 200 or response.geturl().split("/")[2] != "www.pref.kanagawa.jp":
            raise ValueError("Non-government source or bad status")
        data = response.read(4_000_001)
        if len(data) > 4_000_000 or not data.startswith(b"PK"):
            raise ValueError("Unexpected XLSX payload")
        return data

def clean(v):
    v = re.sub(r"\s+", " ", str(v)).strip()
    # Never export coordinates, addresses, people, sample identifiers or raw station columns.
    if re.search(r"緯度|経度|住所|採水地点|採水点|調査員|参加者|氏名|電話|GPS|latitude|longitude", v, re.I):
        return "[site-metadata-excluded]"
    if re.fullmatch(r"\d{6,}", v) or re.search(r"[-+]?\d{2,3}\.\d{4,}", v):
        return "[number-or-site-excluded]"
    return v[:75]

def read_workbook(data):
    with ZipFile(BytesIO(data)) as z:
        files = set(z.namelist())
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rel = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        links = {e.get("Id"): e.get("Target") for e in rel}
        strings = []
        if "xl/sharedStrings.xml" in files:
            ss = ET.fromstring(z.read("xl/sharedStrings.xml"))
            strings = ["".join(t.text or "" for t in si.iter(f"{{{N}}}t"))
                       for si in ss.findall(f"{{{N}}}si")]
        sheets = []
        for sn in wb.findall(f".//{{{N}}}sheets/{{{N}}}sheet"):
            target = links.get(sn.get(f"{{{R}}}id"))
            if not target:
                raise ValueError("Missing worksheet relationship")
            path = target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/" + target)
            if path not in files:
                raise ValueError("Missing worksheet " + path)
            root = ET.fromstring(z.read(path))
            dim = root.find(f"{{{N}}}dimension")
            rows = {}
            for rw in root.findall(f".//{{{N}}}sheetData/{{{N}}}row"):
                cells = {}
                for c in rw.findall(f"{{{N}}}c"):
                    col = re.sub(r"\d", "", c.get("r", ""))
                    v = c.find(f"{{{N}}}v")
                    raw = v.text or "" if v is not None else ""
                    if c.get("t") == "s" and raw.isdecimal():
                        raw = strings[int(raw)]
                    if c.get("t") == "inlineStr":
                        raw = "".join(t.text or "" for t in c.iter(f"{{{N}}}t"))
                    if raw:
                        cells[col] = raw
                rows[int(rw.get("r"))] = cells
            head = []
            for i in range(1, 13):
                row = rows.get(i, {})
                head.append({"row": i, "first_columns": {c: clean(row[c]) for c in SAFE_COLS if c in row and (i not in (1,2) or c in "ABCDEFG")},
                             "populated_columns": len(row)})
            # Only aggregate explicit watershed+tributary labels, never the station ID.
            labels = []
            r3, r4 = rows.get(3, {}), rows.get(4, {})
            for col, rv in r4.items():
                if col in SAFE_COLS or not r3.get(col):
                    continue
                a = re.split(r"[\u30a1-\u30ff]", r3[col])[0].strip()
                b = re.split(r"[\u30a1-\u30ff]", rv)[0].strip()
                if a.endswith("川") and b.endswith(("川", "沢")):
                    labels.append([a, b])
            rclass = Counter(str(rows.get(i, {}).get("A", "")) for i in range(9, min(max(rows)+1,1500)))
            conf = Counter(str(rows.get(i, {}).get("J", "")) for i in range(9, min(max(rows)+1,1500)))
            sheets.append({"sheet": sn.get("name"), "dimension": dim.get("ref") if dim is not None else None,
                           "physical_sheet_rows": len(rows), "head_first_columns": head,
                           "r3_r4_explicit_basin_tributary_pairs": sorted(set(tuple(x) for x in labels)),
                           "r3_r4_pair_count": len(set(tuple(x) for x in labels)),
                           "data_column_A_top_values": rclass.most_common(12),
                           "data_column_J_top_values": conf.most_common(12)})
        return sheets

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    reports = []
    for key, filename in SOURCES.items():
        url = BASE + filename
        x = {"source_key": key, "source_url": url,
             "survey_method": "environmental_DNA_detection_only_not_capture",
             "capture_observations_added": 0, "exact_sites_exported": False}
        try:
            data = get(url)
            x.update(download_ok=True, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                     sheets=read_workbook(data))
        except Exception as exc:
            x.update(download_ok=False, error=type(exc).__name__ + ": " + str(exc)[:250])
        reports.append(x)
        print(json.dumps({"key":key,"download_ok":x["download_ok"],
                          "sha256":x.get("sha256"),
                          "sheets":[{"sheet":s["sheet"],"dimension":s["dimension"],"basins":s["r3_r4_pair_count"]}
                                    for s in x.get("sheets",[])]},ensure_ascii=False))
    obj = {"source_page":"https://www.pref.kanagawa.jp/docs/b4f/suigen/edna.html",
           "license_page":"https://www.pref.kanagawa.jp/documents/97797/riyo-kiyaku.pdf",
           "scope":"2023 and 2024 separate fish/vertebrate/invertebrate eDNA workbooks",
           "2025_baseline_undisturbed": True,"not_a_direct_capture_survey": True,
           "files": reports, "successful_original_workbooks":sum(r["download_ok"] for r in reports)}
    (OUT/"kanagawa_2023_2024_source_schema_scout_v11.json").write_text(
        json.dumps(obj,ensure_ascii=False,indent=2)+"\n", encoding="utf-8")
    if obj["successful_original_workbooks"] < 3:
        raise RuntimeError("Fewer than three official XLSX originals downloaded")
if __name__ == "__main__":
    main()
