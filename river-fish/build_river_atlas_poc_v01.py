#!/usr/bin/env python3
"""Build a source-scoped, offline Ota watershed exploration prototype.

Reuses the independently tested v1.5 input contract. No writes to WordPress,
Xserver, MySQL, or existing data. Code membership is not geography; survey
labels are not direct observations in individual rivers.
"""
import argparse
import json
from pathlib import Path
import shutil
import zipfile

from build_river_beta_v15 import create_payload, records

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "atlas-poc-v01"
CODE = "870709"
NAME = "太田川"
PREF = "広島県"
FISH_REGION = "chugoku"
STATUS = "research_preview_only_no_server_or_wordpress_changes"

def collect():
    source = create_payload()  # vetted original counts, sources, and row format
    water_matches = [w for w in records("national-codes-staged/watershed_codes_national_v07.csv")
                     if w["watershed_code"] == CODE]
    if len(water_matches) != 1 or water_matches[0]["watershed_name"] != NAME:
        raise ValueError("Official water code/name identity changed")

    coded = [r for r in source["riverCodes"] if r[3] == CODE]
    if not coded or len({r[0] for r in coded}) != len(coded):
        raise ValueError("Ota watershed has missing or duplicated river codes")
    if any(r[0][:6] != CODE or r[2] != NAME or len(r[0]) != 10 for r in coded):
        raise ValueError("River code/watershed identity mismatch")
    if not any(r[0] == "8707090023" and r[1] == "諸木川" for r in coded):
        raise ValueError("Expected documented river code not found")

    # This local source proves that Hiroshima prefectural material mentions the
    # Ota system, NOT that every nationwide river code is within Hiroshima.
    local = [r for r in source["localEvidence"]
             if r[0] == PREF and r[2] == "river" and r[3] == NAME]
    if not local or not any(r[1] == "三篠川" for r in local):
        raise ValueError("Prefectural Ota source evidence missing")

    fish = [r for r in source["fishCensus"]
            if r[0] == FISH_REGION and r[1] == NAME]
    if not fish:
        raise ValueError("No original Chugoku Ota-name fish records")
    if any(len(r) != 5 or r[0] != FISH_REGION or r[1] != NAME for r in fish):
        raise ValueError("Fish source scope changed")

    # Keep separate evidence objects: never insert local prefecture, survey
    # species, parent-river, or presence fields into coded river objects.
    return {
        "status": STATUS,
        "edition": "2026-10-19 research v0.1",
        "prefectureEntry": PREF,
        "prefectureEvidence": {
            "scope": "Hiroshima prefectural source listing; not geographic approval for codes",
            "sourceUrls": sorted({r[5] for r in local}),
            "localMentions": len(local)
        },
        "watershed": {"code": CODE, "name": NAME,
                      "codeSource": "https://nlftp.mlit.go.jp/ksj/gml/codelist/WaterSystemCodeCd.html"},
        "riverSource": source["meta"]["officialRiverSource"],
        "rivers": [{"riverCode": r[0], "riverName": r[1]}
                   for r in sorted(coded, key=lambda x: (x[1], x[0]))],
        "fishSurvey": [{"region": r[0], "watershedLabel": r[1],
                        "surveyYear": r[2], "recordedName": r[3], "sourceUrl": r[4]}
                       for r in sorted(fish, key=lambda x: (x[3], x[2]))],
        "fishJoinStatus": "name_and_region_context_only_not_official_code_identity",
        "parentRiverStatus": "not_available",
        "directRiverSpeciesStatus": "not_available",
        "riverPrefectureStatus": "not_verified",
    }

def build(out, archive=None):
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        raise FileExistsError("Refusing to overwrite an existing preview")
    data = collect()
    out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ASSETS/"index.html", out/"index.html")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    data_script = "window.TSURI_ATLAS_POC = " + payload + ";\n"
    (out/"data.js").write_text(data_script, encoding="utf-8")
    standalone = (out/"index.html").read_text(encoding="utf-8").replace(
        '<script src="data.js"></script>',
        '<script>\n' + data_script + '</script>', 1)
    if '<script src="data.js"></script>' in standalone:
        raise ValueError("Standalone preview still loads external data")
    (out/"standalone.html").write_text(standalone, encoding="utf-8")
    manifest = {
        "status": STATUS, "watershed": CODE, "watershedName": NAME,
        "riverCodes": len(data["rivers"]), "fishSurveyRecords": len(data["fishSurvey"]),
        "prefectureMapping": "not_per_river", "directSpecies": "not_per_river",
        "files": ["index.html", "data.js", "standalone.html"]
    }
    (out/"manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    if archive:
        dest=Path(archive)
        dest.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(dest,"w",zipfile.ZIP_DEFLATED,compresslevel=8) as z:
            for name in manifest["files"]+["manifest.json"]:
                z.write(out/name,"tsurikue-ota-atlas-poc/"+name)
    return manifest

if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True)
    p.add_argument("--zip",default="")
    a=p.parse_args()
    print(json.dumps(build(a.out,a.zip or None),ensure_ascii=False,indent=2))
