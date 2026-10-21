#!/usr/bin/env python3
"""Extract exact named-river×fish evidence from 9 pinned NILIM regional ZIPs.

Research only. No prefecture inference, no station/coordinate/site/date fields.
The original source's river-name field is read directly, not inferred from a
watershed-wide species list. Every regional ZIP is SHA256 pinned.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from extract_official_named_river_fish_v03 import aggregate, workbook_records

ROOT = Path(__file__).resolve().parent.parent / "nationwide-staged"
REGIONS = ("hokkaido", "tohoku", "kanto", "hokuriku", "chubu", "kinki",
           "chugoku", "shikoku", "kyushu")
FIELDS = ("region", "watershed", "river_name", "survey_year",
          "recorded_name", "source_url", "source_sha256", "review_status")
STATUS = "STAGED_REVIEW_ONLY_NOT_FOR_PUBLICATION"
SCHEMA = "tsurikue-official-nine-regions-named-river-fish-v04"


def manifest_for(region):
    if region not in REGIONS:
        raise ValueError("Unknown region")
    path = ROOT / region / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def validate_manifest(region, m):
    url = urlsplit(m["source_url"])
    if (region not in REGIONS or m.get("region") != region or
            m.get("status") != "staged_not_published" or
            m.get("publication_status") != "staged_not_published" or
            m.get("prefecture_mapping") != "not_inferred" or
            m.get("direct_river_mapping") != "not_inferred" or
            url.scheme != "https" or url.hostname != "www.nilim.go.jp" or
            not re.fullmatch(r"/lab/fbg/ksnkankyo/download/slist/RT8\d_B01\.zip", url.path) or
            not re.fullmatch(r"[0-9a-f]{64}", m["source_sha256"]) or
            not re.fullmatch(r"RT8\d_B01/魚類_[^/]+\.xlsx", m["source_member"]) or
            not (100 <= m["source_rows"] <= 1000000) or
            not (1 <= m["unique_watersheds"] <= 100) or
            m.get("source_sheet") != "データ"):
        raise ValueError("Unexpected regional manifest: manual review required")
    if m["source_member"].split("/")[0] != url.path.rsplit("/", 1)[-1].removesuffix(".zip"):
        raise ValueError("ZIP member does not match pinned official URL")


def download_pinned(m):
    url = m["source_url"]
    req = Request(url, headers={"User-Agent": "tsurikue-river-fish-research/0.4"})
    with urlopen(req, timeout=90) as resp:
        if resp.status != 200 or resp.url != url:
            raise ValueError("Official source URL redirected or changed")
        raw = resp.read(75_000_001)
    if len(raw) > 75_000_000:
        raise ValueError("Unexpectedly large source ZIP")
    if hashlib.sha256(raw).hexdigest() != m["source_sha256"]:
        raise ValueError("Official ZIP SHA256 changed; stop for manual review")
    return raw


def build_region(region, m, source_rows):
    validate_manifest(region, m)
    rows, report = aggregate(source_rows)
    if report["counts"]["source_rows"] != m["source_rows"]:
        raise ValueError("Official workbook source row count changed")
    if report["watershed_groups"] != m["unique_watersheds"]:
        raise ValueError("Watershed groups unexpectedly differ from pinned aggregate")
    if report["fish_name_labels"] > m["distinct_name_labels"]:
        raise ValueError("Unexpected fish name labels beyond official fish inventory")
    if not set(report["years"]).issubset(set(m["years"])):
        raise ValueError("Survey year outside official inventory")
    return rows, {
        "schema": SCHEMA, "region": region, "official_region": m["official_region"],
        "status": STATUS, "source_url": m["source_url"],
        "source_sha256": m["source_sha256"],
        "source_member": m["source_member"],
        "source_rows": report["counts"]["source_rows"],
        "source_fish_category_only": True,
        "source_fish_year_records": report["aggregated_records"],
        "river_name_groups": report["river_name_groups"],
        "watersheds": report["watershed_groups"],
        "fish_label_names": report["fish_name_labels"],
        "years": report["years"],
        "excluded": report["counts"],
        "prefecture": None, "national_river_code": None,
        "river_identity_review": "unverified_same_names_possible",
        "sensitive_species_review": "required_before_publication",
        "excluded_location_fields": ["station", "site", "district", "subreach",
                                     "coordinate", "distance", "precise_date",
                                     "abundance", "individual_count"],
        "counting_rule": "region x watershed x literal river name x year x literal fish name",
        "site_updated": False,
    }


def export_region(region, m, records, report, out):
    if out.exists():
        raise FileExistsError("Refuse to overwrite output")
    out.mkdir(parents=True)
    with (out / "official_direct_river_fish_v04.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(FIELDS)
        for water, river, year, fish in records:
            writer.writerow((region, water, river, year, fish,
                             m["source_url"], m["source_sha256"],
                             "unapproved_requires_conservation_and_identity_review"))
    (out / "manifest_review_only_v04.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--region", choices=REGIONS, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    m = manifest_for(args.region)
    validate_manifest(args.region, m)
    raw = download_pinned(m)
    records, report = build_region(args.region, m,
                                   workbook_records(raw, member=m["source_member"]))
    export_region(args.region, m, records, report, args.out)
    print("NATIONAL_DIRECT_RIVER_FISH_V04", json.dumps({
        "region": args.region,
        "source_rows": report["source_rows"],
        "named_river_groups": report["river_name_groups"],
        "river_fish_year_records": report["source_fish_year_records"],
        "fish_name_labels": report["fish_label_names"],
        "site_updated": False,
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
