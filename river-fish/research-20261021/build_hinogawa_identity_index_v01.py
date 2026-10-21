#!/usr/bin/env python3
"""Join verified river-code identities to Hino fish-table research candidates.

This is an exact, review-only overlay. It does not alter the original
transcription and never marks records publishable or current.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
RECORDS = HERE / "hinogawa_diadr_fish_records_v01.csv"
IDENTITIES = HERE / "hinogawa_river_identity_v01.csv"
IDENTITY_FIELDS = (
    "identity_id", "prefecture", "watershed", "river_name", "river_code",
    "river_name_code_status", "system_scheme_status", "relation_to_hino_mainstem",
    "official_management_scope", "management_length_km", "fish_source_site_scope",
    "fish_table_visual_verification", "fish_record_approval", "source_urls",
    "source_locators", "notes",
)
EXPECTED = {
    ("鳥取県", "日野川水系", "日野川"): ("8707030001", "本川"),
    ("鳥取県", "日野川水系", "法勝寺川"): ("8707030003", "日野川本川への支川"),
}
OFFICIAL_HOSTS = {"nlftp.mlit.go.jp", "www.cgr.mlit.go.jp"}
ADD_FIELDS = (
    "river_identity_id", "river_identity_status", "river_relation",
    "river_management_scope_note", "fish_sampling_scope_confirmed",
)


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        return fields, list(reader)


def load_identities(path: Path = IDENTITIES) -> dict[tuple[str, str, str], dict[str, str]]:
    fields, rows = read_csv(path)
    if tuple(fields) != IDENTITY_FIELDS:
        raise ValueError("identity ledger header drift")
    if len(rows) != len(EXPECTED):
        raise ValueError("expected two explicitly identified river names")
    identities: dict[tuple[str, str, str], dict[str, str]] = {}
    codes: set[str] = set()
    for row in rows:
        key = (row["prefecture"], row["watershed"], row["river_name"])
        expected = EXPECTED.get(key)
        if expected is None or (row["river_code"], row["relation_to_hino_mainstem"]) != expected:
            raise ValueError(f"unexpected name/code/relation mapping: {key}")
        if key in identities or row["river_code"] in codes:
            raise ValueError("duplicate river identity or river code")
        if (row["river_name_code_status"] != "confirmed"
                or row["system_scheme_status"] != "confirmed"
                or row["fish_record_approval"] != "not_approved"
                or row["fish_table_visual_verification"] != "true"):
            raise ValueError("identity/source verification or publication boundary changed")
        if not row["fish_source_site_scope"] or not row["official_management_scope"]:
            raise ValueError("missing reach or fish sampling scope qualification")
        urls = row["source_urls"].split(";")
        hosts = {urlsplit(url).hostname for url in urls}
        if not {"nlftp.mlit.go.jp", "www.cgr.mlit.go.jp"} <= hosts:
            raise ValueError("code list and official system/river office evidence are required")
        if not hosts <= OFFICIAL_HOSTS or any(urlsplit(url).scheme != "https" for url in urls):
            raise ValueError("identity sources must be official HTTPS sources")
        identities[key] = row
        codes.add(row["river_code"])
    if set(identities) != set(EXPECTED):
        raise ValueError("identified river set changed")
    return identities


def load_records(path: Path = RECORDS) -> tuple[list[str], list[dict[str, str]]]:
    return read_csv(path)


def build_index(records: list[dict[str, str]],
                identities: dict[tuple[str, str, str], dict[str, str]]) -> list[dict[str, str]]:
    if not records:
        raise ValueError("no source records")
    seen_ids: set[str] = set()
    output = []
    for source in records:
        record = dict(source)
        record_id = record.get("record_id", "")
        if not record_id or record_id in seen_ids:
            raise ValueError("missing or duplicate research record id")
        seen_ids.add(record_id)
        if record.get("river_code", ""):
            raise ValueError("source record already has a code; refuse silent replacement")
        if (record.get("fish_publication_approval") != "not_approved"
                or record.get("integration_status") != "research_only"):
            raise ValueError("source record escaped research-only status")
        key = (record.get("prefecture", ""), record.get("water_system", ""),
               record.get("river_as_published", ""))
        identity = identities.get(key)
        if identity is None:
            raise ValueError(f"no exact reviewed river identity for source row {record_id}")
        record["river_code"] = identity["river_code"]
        record["river_identity_id"] = identity["identity_id"]
        record["river_identity_status"] = "official_code_and_system_identity_confirmed"
        record["river_relation"] = identity["relation_to_hino_mainstem"]
        record["river_management_scope_note"] = identity["official_management_scope"]
        record["fish_sampling_scope_confirmed"] = "false"
        output.append(record)
    if len(output) != 57:
        raise ValueError(f"expected 57 research candidates; got {len(output)}")
    if {row["river_code"] for row in output} != {"8707030001", "8707030003"}:
        raise ValueError("unexpected river-code coverage")
    return output


def write_index(rows: list[dict[str, str]], out: Path, source_fields: list[str]) -> None:
    if out.exists():
        raise FileExistsError(f"refusing to overwrite {out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=source_fields,
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    source_fields, records = load_records()
    index = build_index(records, load_identities())
    write_index(index, args.out, source_fields + list(ADD_FIELDS))
    print("HINOGAWA_IDENTITY_INDEX_V01", {
        "records": len(index), "river_codes": sorted({r["river_code"] for r in index}),
        "publication_approvals": 0, "site_updated": False,
    }, flush=True)


if __name__ == "__main__":
    main()
