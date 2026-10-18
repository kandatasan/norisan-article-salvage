#!/usr/bin/env python3
"""Research-only, literal-name taxonomy audit; NEVER creates an aquatic-insect search group.

Compare historical benthic names with the SHA-verified official 2025 *reference*
without claiming identity, individual-river presence, or insect ecology.
Report only aggregate counts (no sensitive sites/coordinates).
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sqlite3

from build_biota_catalog_v18 import read_reference

EXPECTED_BENTHIC = 74949
AUDIT_VERSION = 1


def reference_class(row):
    """Unknown or disagreeing class metadata may never become an insect match."""
    japanese = row["class_japanese"].strip()
    scientific = row["class_scientific"].strip().casefold()
    jp_insect = japanese in ("昆虫綱", "昆虫")
    sci_insect = scientific == "insecta"
    # Candidate insect status requires BOTH matching official class fields.
    # Missing/disagreeing fields are unresolved, never inferred from one field.
    if not japanese or not scientific or jp_insect != sci_insect:
        return "uncertain_class"
    return "insect" if jp_insect else "other_class"


def index_reference(rows):
    index = defaultdict(list)
    for r in rows:
        # Names only: never normalize or infer synonyms from NFKC, morphology,
        # scientific names, higher ranks or taxon codes.
        if r["japanese_name"]:
            index[r["japanese_name"]].append((
                reference_class(r), r["benthic_animals"] == "1"))
    return index


def classify(name, index):
    matches = index.get(name, [])
    if not matches:
        return "no_exact_2025_reference_name"
    # A terrestrial-insect-only list name is NOT enough to prove that a
    # watershed's benthic record is an aquatic insect.
    if not any(benthic for _kind, benthic in matches):
        return "outside_benthic_reference_membership"
    kinds = {kind for kind, _benthic in matches}
    if "uncertain_class" in kinds:
        return "uncertain_reference_class"
    if kinds == {"insect"}:
        return "insect_name_candidate_not_verified"
    if kinds == {"other_class"}:
        return "non_insect_reference_name"
    return "insect_other_class_name_collision"


def run(db_path, manifest_path, reference_root):
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    db_path = Path(db_path)
    with db_path.open("rb") as handle:
        h = hashlib.file_digest(handle, "sha256").hexdigest()
    if h != manifest["database_sha256"]:
        raise ValueError("Immutable four-group snapshot SHA mismatch")
    if (manifest["group_counts"].get("benthic_animals") != EXPECTED_BENTHIC
            or manifest["taxonomy_identity_verified"] is not False
            or manifest["wordpress_modified"] is not False):
        raise ValueError("Unapproved survey or classification source")
    references, source_manifest = read_reference(reference_root)
    index = index_reference(references)
    conn = sqlite3.connect("file:" + db_path.resolve().as_uri()[5:] + "?mode=ro", uri=True)
    try:
        conn.execute("PRAGMA query_only=ON")
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Snapshot SQLite corruption")
        rows = conn.execute("""
            SELECT recorded_name, COUNT(*) AS records
            FROM survey_evidence WHERE group_id='benthic_animals'
            GROUP BY recorded_name
        """).fetchall()
        raw_count = sum(record_count for _, record_count in rows)
        if raw_count != EXPECTED_BENTHIC:
            raise ValueError("Benthic group total changed")
        record_counts = Counter()
        label_counts = Counter()
        for name, n in rows:
            category = classify(name, index)
            record_counts[category] += n
            label_counts[category] += 1
    finally:
        conn.close()
    expected = set(CATEGORIES)
    if set(record_counts) - expected or sum(record_counts.values()) != EXPECTED_BENTHIC:
        raise ValueError("Literal-name partition failed")
    return {
        "audit_version": AUDIT_VERSION,
        "report_type": "research_only_exact_literal_name_screening_not_taxonomic_identity",
        "reference_edition": source_manifest["edition"],
        "reference_csv_sha256": source_manifest["staged_csv_sha256"],
        "dataset_sha256": manifest["database_sha256"],
        "benthic_survey_records": raw_count,
        "benthic_distinct_literal_labels_not_species": len(rows),
        "records_by_screening_status": {key: record_counts[key] for key in CATEGORIES},
        "labels_by_screening_status": {key: label_counts[key] for key in CATEGORIES},
        "aquatic_insect_group_can_be_published": False,
        "survey_names_identified_as_species": 0,
        "records_assigned_to_individual_river": 0,
        "wordpress_modified": False,
        "warning": "昆虫綱の分類表との掲載名一致は候補抽出にすぎず、水生昆虫の確定同定ではありません。同名異分類・分類欠落・未一致を自動補完しません。"
    }


CATEGORIES = (
    "insect_name_candidate_not_verified",
    "non_insect_reference_name",
    "insect_other_class_name_collision",
    "uncertain_reference_class",
    "outside_benthic_reference_membership",
    "no_exact_2025_reference_name",
)


def self_test():
    def record(name, japanese, scientific, benthic):
        return {"japanese_name": name, "class_japanese": japanese,
                "class_scientific": scientific, "benthic_animals": benthic}
    index = index_reference([
        record("insect", "昆虫綱", "Insecta", "1"),
        record("non", "軟甲綱", "Malacostraca", "1"),
        record("mixed", "昆虫綱", "Insecta", "1"),
        record("mixed", "軟甲綱", "Malacostraca", "1"),
        record("unknown", "", "", "1"),
        record("outside", "昆虫綱", "Insecta", "0"),
        record("conflict", "昆虫綱", "Malacostraca", "1"),
        record("missingclass", "昆虫綱", "", "1"),
    ])
    actual = {x: classify(x, index) for x in
              ("insect", "non", "mixed", "unknown", "outside", "conflict", "missingclass", "missing")}
    assert actual == {
        "insect": "insect_name_candidate_not_verified",
        "non": "non_insect_reference_name",
        "mixed": "insect_other_class_name_collision",
        "unknown": "uncertain_reference_class",
        "outside": "outside_benthic_reference_membership",
        "conflict": "uncertain_reference_class",
        "missingclass": "uncertain_reference_class",
        "missing": "no_exact_2025_reference_name",
    }, actual
    print("AQUATIC_INSECT_NAME_SCREENING_UNIT_PASS")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db")
    parser.add_argument("--manifest")
    parser.add_argument("--reference-root", default=str(Path(__file__).resolve().parent))
    parser.add_argument("--out")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    self_test()
    if args.self_test:
        return
    if not all((args.db, args.manifest, args.out)):
        parser.error("--db, --manifest and --out required")
    result = run(args.db, args.manifest, args.reference_root)
    output = Path(args.out)
    if output.exists():
        raise FileExistsError("Audit reports are immutable")
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("AQUATIC_INSECT_NAME_SCREENING_AUDIT_PASS",
          result["benthic_survey_records"],
          result["records_by_screening_status"])


if __name__ == "__main__":
    main()
