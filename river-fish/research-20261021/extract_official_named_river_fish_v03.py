#!/usr/bin/env python3
"""Read pinned official China-region fish workbook: watershed + named river + fish.

RESEARCH ONLY. Extract no station, district, coordinates, subreach, site code,
distance, abundance, or exact date. Never infer prefecture or national river ID.
"""
from __future__ import annotations
import argparse
import collections
import csv
import hashlib
import json
import re
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aggregate_official_workbook import (
    get_official_zip, MEMBER, M, SOURCE, EXPECTED_SHA256
)

SCHEMA = "tsurikue-official-chugoku-named-river-fish-v03"
HEADERS = {"C": "生物項目", "F": "水系", "G": "調査年度", "J": "種名", "M": "河川名"}
FIELDS = ("region", "watershed", "river_name", "survey_year",
          "recorded_name", "source_url", "source_sha256", "review_status")
UNUSABLE_RIVER_NAMES = {"不明", "未記入", "不詳", "その他", "河川名", "-", "なし", "不定", "複数河川"}


def workbook_records(zip_bytes, member=MEMBER):
    """Yield only 5 permitted source fields, with strict header validation."""
    with ZipFile(BytesIO(zip_bytes)) as outer:
        if member not in outer.namelist():
            raise ValueError("Unexpected source workbook member")
        inner = outer.read(member)
    with ZipFile(BytesIO(inner)) as book:
        if book.getinfo("xl/worksheets/sheet1.xml").file_size > 300_000_000:
            raise ValueError("Unexpectedly large workbook")
        with book.open("xl/sharedStrings.xml") as f:
            strings = []
            for _, el in ET.iterparse(f, events=("end",)):
                if el.tag == M + "si":
                    strings.append("".join(x.text or "" for x in el.iter(M + "t")))
                    el.clear()
        first = True
        with book.open("xl/worksheets/sheet1.xml") as f:
            for _, row in ET.iterparse(f, events=("end",)):
                if row.tag != M + "row":
                    continue
                data = {}
                for cell in row.findall(M + "c"):
                    ref = cell.get("r", "")
                    match = re.match(r"^[A-Z]+", ref)
                    col = match.group(0) if match else ""
                    if col not in HEADERS:
                        continue
                    val = cell.findtext(M + "v") or ""
                    if cell.get("t") == "s":
                        if not val.isdecimal() or int(val) >= len(strings):
                            raise ValueError("Invalid string table index")
                        val = strings[int(val)]
                    elif cell.get("t") == "inlineStr":
                        val = "".join(x.text or "" for x in cell.iter(M + "t"))
                    data[col] = val.strip()
                if first:
                    if data != HEADERS:
                        raise ValueError("Official schema changed: expected only five fixed headers")
                    first = False
                else:
                    yield data
                row.clear()
        if first:
            raise ValueError("Missing source header")


def aggregate(records, min_source_rows=100):
    unique = set()
    counters = collections.Counter()
    years = set()
    for row in records:
        counters["source_rows"] += 1
        if counters["source_rows"] > 1_000_000:
            raise ValueError("Source row count exceeded limit")
        if row.get("C") != "魚類":
            counters["excluded_not_explicit_fish_category"] += 1
            continue
        water = row.get("F", "").strip()
        river = row.get("M", "").strip()
        fish = row.get("J", "").strip()
        year = row.get("G", "").strip()
        if not water or not river or not fish:
            counters["excluded_missing_watershed_river_or_fish"] += 1
            continue
        if river in UNUSABLE_RIVER_NAMES or "水系" == river:
            counters["excluded_nonidentifiable_river_name"] += 1
            continue
        if not re.fullmatch(r"(?:19|20)\d{2}", year) or year > "2026":
            counters["excluded_invalid_survey_year"] += 1
            continue
        if len(water) > 80 or len(river) > 80 or len(fish) > 150:
            counters["excluded_oversize_fields"] += 1
            continue
        if any(x[0] in "=+-@" for x in (water, river, fish)):
            counters["excluded_formula_like_value"] += 1
            continue
        unique.add((water, river, year, fish))
        years.add(year)
        counters["valid_source_rows"] += 1
    if counters["source_rows"] < min_source_rows:
        raise ValueError("Source unexpectedly small")
    if not unique:
        raise ValueError("No named-river fish evidence in official source")
    ordered = sorted(unique)
    return ordered, {
        "schema": SCHEMA,
        "status": "STAGED_REVIEW_ONLY_NOT_FOR_PUBLICATION",
        "region": "chugoku",
        "prefecture": None,
        "prefecture_mapping": "not_inferred",
        "national_river_code": None,
        "national_river_code_identity_verified": False,
        "river_identity_review": "unverified_same_names_possible",
        "sensitive_species_review": "required_before_publication",
        "source_url": SOURCE,
        "source_sha256": EXPECTED_SHA256,
        "source_member": MEMBER,
        "source_headers": HEADERS,
        "counts": dict(sorted(counters.items())),
        "aggregated_records": len(ordered),
        "river_name_groups": len({(x[0], x[1]) for x in ordered}),
        "watershed_groups": len({x[0] for x in ordered}),
        "fish_name_labels": len({x[3] for x in ordered}),
        "years": sorted(years),
        "counting_rule": "unique watershed x literal river name x survey year x literal fish label",
        "not_saved": ["site", "station", "subreach", "district", "coordinates",
                      "distance", "precise_date", "abundance", "individual_count"],
        "notice": "国交省の河川水辺の国勢調査における水系・河川名・調査年度・魚名の組。地点情報は保持せず、同名別河川と保全上の公開可否は未審査。",
    }


def write_outputs(out, records, summary):
    if out.exists():
        raise FileExistsError("Refuse to overwrite an existing output directory")
    out.mkdir(parents=True)
    path = out / "direct_named_river_fish_review_v03.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(FIELDS)
        for water, river, year, fish in records:
            writer.writerow(("chugoku", water, river, year, fish,
                             SOURCE, EXPECTED_SHA256, "unapproved_requires_conservation_and_identity_review"))
    (out / "direct_named_river_fish_summary_v03.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    raw, digest = get_official_zip()
    if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA256 or digest != EXPECTED_SHA256:
        raise ValueError("Source ZIP hash mismatch")
    records, summary = aggregate(workbook_records(raw))
    write_outputs(args.out, records, summary)
    print("OFFICIAL_NAMED_RIVER_FISH_V03", json.dumps({
        "source_rows": summary["counts"]["source_rows"],
        "named_river_fish_year_records": summary["aggregated_records"],
        "named_river_groups": summary["river_name_groups"],
        "watersheds": summary["watershed_groups"],
        "fish_labels": summary["fish_name_labels"],
        "survey_years": [summary["years"][0], summary["years"][-1]],
        "public_site_changed": False,
        "prefecture_inferred": False,
        "sensitive_species_review": "pending",
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
