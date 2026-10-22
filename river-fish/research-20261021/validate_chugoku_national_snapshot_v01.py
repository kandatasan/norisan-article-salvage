#!/usr/bin/env python3
"""Validate and materialize the pinned, location-minimized Chugoku fish snapshot.

The encoded artifact is a compact storage form, not encryption. It contains the
publicly downloadable, river-name-level fish/year records, but no sample sites,
coordinates, subreaches, dates, or abundance. Every record remains unapproved.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE_DIR = HERE.parent / "nationwide-staged" / "chugoku"
SNAPSHOT_PATH = SOURCE_DIR / "official_direct_river_fish_v04_snapshot.zip.b64"
MANIFEST_PATH = SOURCE_DIR / "official_direct_river_fish_v04_snapshot_v01.json"
CSV_MEMBER = "official_direct_river_fish_v04.csv"
SOURCE_MANIFEST_MEMBER = "manifest_review_only_v04.json"
CSV_FIELDS = (
    "region", "watershed", "river_name", "survey_year", "recorded_name",
    "source_url", "source_sha256", "review_status",
)
BLOCKED_FIELD_PARTS = (
    "station", "site", "coordinate", "district", "subreach", "distance",
    "abundance", "individual", "precise_date", "weather",
)
EXPECTED_SOURCE_URL = "https://www.nilim.go.jp/lab/fbg/ksnkankyo/download/slist/RT87_B01.zip"
EXPECTED_SOURCE_SHA256 = "1fd6a7201f3100164bc9921002b2723c04a9b6d1f55e0e773b957f6d97205f4e"
EXPECTED_ARCHIVE_SHA256 = "27675043f1cc24e5f173a481a70d68c2238c4189106a4c02fcc4cecf8dd28543"
EXPECTED_CSV_SHA256 = "26ff8edebc92e152b2b19fc34ba51f963a0a197ef706cebd8fd347f8cd7f82a8"
EXPECTED_ROWS = 3592
EXPECTED_RIVER_GROUPS = 35
EXPECTED_FISH_LABELS = 216
EXPECTED_STATUS = "unapproved_requires_conservation_and_identity_review"


def _fail(message: str) -> None:
    raise ValueError(message)


def validate_snapshot(encoded: str, meta: dict) -> dict:
    if meta.get("schema") != "tsurikue-chugoku-direct-river-fish-snapshot-v01":
        _fail("Unexpected snapshot manifest schema")
    if meta.get("status") != "REVIEW_ONLY_PINNED_DERIVATIVE_SNAPSHOT":
        _fail("Snapshot is not explicitly research-only")
    source = meta.get("official_source", {})
    if (source.get("source_url") != EXPECTED_SOURCE_URL
            or source.get("source_sha256") != EXPECTED_SOURCE_SHA256
            or source.get("valid_chugoku_fish_year_records") != EXPECTED_ROWS
            or source.get("river_name_groups") != EXPECTED_RIVER_GROUPS
            or source.get("distinct_literal_fish_labels") != EXPECTED_FISH_LABELS
            or source.get("prefecture") is not None
            or source.get("national_river_code") is not None):
        _fail("Official source pin or conservative identity bounds changed")
    captured = meta.get("normalized_snapshot", {})
    if (captured.get("archive_sha256") != EXPECTED_ARCHIVE_SHA256
            or captured.get("source_csv_sha256") != EXPECTED_CSV_SHA256
            or captured.get("source_csv_rows") != EXPECTED_ROWS):
        _fail("Captured artifact pin changed")
    try:
        archive = base64.b64decode(encoded.strip(), validate=True)
    except Exception as exc:
        raise ValueError("Snapshot is not valid base64") from exc
    if hashlib.sha256(archive).hexdigest() != EXPECTED_ARCHIVE_SHA256:
        _fail("Snapshot artifact SHA256 mismatch")
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as zf:
            names = sorted(zf.namelist())
            expected_names = sorted((CSV_MEMBER, SOURCE_MANIFEST_MEMBER))
            if names != expected_names:
                _fail("Snapshot contains unexpected files")
            csv_bytes = zf.read(CSV_MEMBER)
            source_manifest = json.loads(zf.read(SOURCE_MANIFEST_MEMBER).decode("utf-8"))
    except Exception as exc:
        raise ValueError("Pinned artifact ZIP is invalid") from exc
    if hashlib.sha256(csv_bytes).hexdigest() != EXPECTED_CSV_SHA256:
        _fail("Derived Chugoku CSV SHA256 mismatch")
    if (source_manifest.get("schema") != "tsurikue-official-nine-regions-named-river-fish-v04"
            or source_manifest.get("status") != "STAGED_REVIEW_ONLY_NOT_FOR_PUBLICATION"
            or source_manifest.get("region") != "chugoku"
            or source_manifest.get("source_url") != EXPECTED_SOURCE_URL
            or source_manifest.get("source_sha256") != EXPECTED_SOURCE_SHA256
            or source_manifest.get("source_fish_year_records") != EXPECTED_ROWS
            or source_manifest.get("river_name_groups") != EXPECTED_RIVER_GROUPS
            or source_manifest.get("fish_label_names") != EXPECTED_FISH_LABELS
            or source_manifest.get("prefecture") is not None
            or source_manifest.get("national_river_code") is not None):
        _fail("Derived snapshot manifest does not match the pinned official source")
    try:
        text = csv_bytes.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text, newline=""))
        if tuple(reader.fieldnames or ()) != CSV_FIELDS:
            _fail("Snapshot CSV headers changed")
        rows = list(reader)
    except Exception as exc:
        raise ValueError("Snapshot CSV could not be parsed") from exc
    if len(rows) != EXPECTED_ROWS:
        _fail("Snapshot row count changed")
    groups = set()
    fish_names = set()
    record_keys = set()
    years = set()
    for row in rows:
        if set(row) != set(CSV_FIELDS):
            _fail("Snapshot row fields changed")
        if (row["region"] != "chugoku" or row["source_url"] != EXPECTED_SOURCE_URL
                or row["source_sha256"] != EXPECTED_SOURCE_SHA256
                or row["review_status"] != EXPECTED_STATUS
                or not all(row[key].strip() for key in ("watershed", "river_name", "survey_year", "recorded_name"))):
            _fail("Snapshot provenance or review status changed")
        if not (row["survey_year"].isdigit() and len(row["survey_year"]) == 4
                and 2000 <= int(row["survey_year"]) <= 2030):
            _fail("Unexpected survey year")
        record_key = (row["region"], row["watershed"], row["river_name"],
                      row["survey_year"], row["recorded_name"])
        if record_key in record_keys:
            _fail("Duplicate source record")
        record_keys.add(record_key)
        groups.add((row["watershed"], row["river_name"]))
        fish_names.add(row["recorded_name"])
        years.add(int(row["survey_year"]))
    if (len(groups) != EXPECTED_RIVER_GROUPS or len(fish_names) != EXPECTED_FISH_LABELS
            or (min(years), max(years)) != (2006, 2023)):
        _fail("Snapshot inventory drifted")
    fields = set(CSV_FIELDS)
    if any(any(part in name.lower() for part in BLOCKED_FIELD_PARTS) for name in fields):
        _fail("Location-sensitive field present")
    if meta.get("review", {}).get("all_rows_publication_status") != EXPECTED_STATUS:
        _fail("Snapshot publication gate changed")
    if (meta.get("review", {}).get("sensitive_species_review_required") is not True
            or meta.get("review", {}).get("site_updated") is not False):
        _fail("Snapshot conservation or site boundary changed")
    return {
        "archive_sha256": EXPECTED_ARCHIVE_SHA256,
        "source_csv_sha256": EXPECTED_CSV_SHA256,
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "rows": len(rows),
        "river_name_groups": len(groups),
        "literal_fish_labels": len(fish_names),
        "survey_year_range": [min(years), max(years)],
        "publication_approvals": 0,
        "site_updated": False,
        "rows_data": rows,
        "csv_bytes": csv_bytes,
        "source_manifest": source_manifest,
    }


def load_snapshot() -> dict:
    if not SNAPSHOT_PATH.is_file() or not MANIFEST_PATH.is_file():
        _fail("Pinned Chugoku snapshot files are missing")
    meta = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return validate_snapshot(SNAPSHOT_PATH.read_text(encoding="ascii"), meta)


def materialize(out_dir: Path) -> dict:
    if out_dir.exists():
        raise FileExistsError("Refusing to overwrite snapshot output")
    snapshot = load_snapshot()
    out_dir.mkdir(parents=True)
    (out_dir / CSV_MEMBER).write_bytes(snapshot["csv_bytes"])
    (out_dir / SOURCE_MANIFEST_MEMBER).write_text(
        json.dumps(snapshot["source_manifest"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {key: value for key, value in snapshot.items()
            if key not in {"rows_data", "csv_bytes", "source_manifest"}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    print("CHUGOKU_OFFICIAL_FISH_SNAPSHOT_V01", json.dumps(materialize(args.out_dir), ensure_ascii=False))


if __name__ == "__main__":
    main()
