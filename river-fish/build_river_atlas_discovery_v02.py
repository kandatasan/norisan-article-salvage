#!/usr/bin/env python3
"""Build safe discovery indexes from the existing Ota atlas payload.

No river-parent inference and no claim that watershed survey species inhabit
individual rivers. This is a read-only transformation of existing source data.
"""
import json
from collections import defaultdict
from pathlib import Path
from build_river_atlas_poc_v01 import collect


def discovery(data=None):
    data = collect() if data is None else data
    watershed = data["watershed"]
    code = watershed["code"]
    rivers = data["rivers"]
    surveys = data["fishSurvey"]
    if any(r["riverCode"][:6] != code for r in rivers):
        raise ValueError("River code outside selected watershed")
    by_name = defaultdict(list)
    for item in surveys:
        if item["watershedLabel"] != watershed["name"] or item["region"] != "chugoku":
            raise ValueError("Survey scope mismatch")
        by_name[item["recordedName"]].append(item)

    species = []
    for name in sorted(by_name):
        observations = by_name[name]
        species.append({
            "recordedName": name,
            "surveyScope": "watershed_name_region_context",
            "watershedCode": code,
            "watershedCodeMatch": "unverified",
            "years": sorted({str(r["surveyYear"]) for r in observations}),
            "recordCount": len(observations),
            "sourceUrls": sorted({r["sourceUrl"] for r in observations}),
            "individualRiverPresence": "not_verified",
        })

    return {
        "schemaVersion": "0.2",
        "watershed": watershed,
        "riverCount": len(rivers),
        "rivers": [
            {"riverCode": r["riverCode"], "riverName": r["riverName"],
             "parentRiverCode": None, "parentVerification": "unverified",
             "children": [], "childrenStatus": "not_verified"}
            for r in rivers
        ],
        "riverTreeStatus": "unavailable_until_independent_parent_evidence",
        "species": species,
        "speciesNavigationStatus": "survey_watershed_name_context_only",
        "directRiverSpeciesStatus": "not_available",
    }


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    args = p.parse_args()
    output = Path(args.out)
    if output.exists():
        raise FileExistsError("Refusing to overwrite output")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(discovery(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
