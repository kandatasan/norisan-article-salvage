#!/usr/bin/env python3
"""Package audited four-group survey research CSV and PHP/Shadow DOM plugin.

The output ZIP is MANUALLY installable only, not installed or enabled.
Does not connect to WordPress, does not write posts or network files.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import zipfile

ROOT=Path(__file__).resolve().parent
BIO=ROOT/"biota"
sys.path.insert(0,str(BIO))
from engine_v23 import VerifiedSnapshot

PLUGIN=ROOT/"wp-plugin/tsurikue-biota-search"
SAFE_SOURCE_FILES=(
    "tsurikue-biota-search.php",
    "includes/class-tbs-data.php",
    "includes/class-tbs-rest.php",
    "frontend/view.php",
    "frontend/app.js",
    "frontend/style.css",
    "assets/admin.js",
    "readme.txt",
    "data/index.php",
    "data/.htaccess",
)
VERSION="biota-four-groups-v28"
EXPECTED={"fish":18814,"benthic_animals":74949,"birds":44093,"plants":270180}
TOTAL=sum(EXPECTED.values())
CSV_HEADER=("group_id","region_code","watershed_name","survey_year",
            "recorded_name","source_url","source_sha256")
REGIONS={"hokkaido","tohoku","kanto","hokuriku","chubu",
         "kinki","chugoku","shikoku","kyushu"}
URL=re.compile(r"^https://www\.nilim\.go\.jp/lab/fbg/ksnkankyo/[^\s]*\Z")
HEX=re.compile(r"^[0-9a-f]{64}\Z")

def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def build(db,manifest,out,zip_path):
    out=Path(out).resolve(); zip_path=Path(zip_path).resolve()
    if out.exists() and any(out.iterdir()):
        raise FileExistsError("Output directory must be new or empty")
    if zip_path.exists():
        raise FileExistsError("Do not overwrite an existing installable ZIP")
    source=VerifiedSnapshot(db,manifest)
    meta=source.catalog()
    if (source.metadata["group_counts"]!=EXPECTED
        or meta["data_rows"]!=TOTAL
        or source.metadata["publication_status"]!="research_only_not_wordpress"
        or source.metadata["individual_river_verified"] is not False
        or source.metadata["taxonomy_identity_verified"] is not False):
        raise ValueError("Only audited nationwide 4-group dataset can be packaged")
    target=out/"tsurikue-biota-search"
    target.mkdir(parents=True,exist_ok=True)
    for relative in SAFE_SOURCE_FILES:
        if not (PLUGIN/relative).is_file():
            raise FileNotFoundError("Expected PHP/Shadow DOM component missing: "+relative)
        dst=target/relative
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(PLUGIN/relative,dst)
    csvfile=target/"data/survey_evidence.csv"
    counts={k:0 for k in EXPECTED}
    with source.connect() as conn:
        with csvfile.open("w",encoding="utf-8",newline="") as fh:
            writer=csv.writer(fh,lineterminator="\n")
            writer.writerow(CSV_HEADER)
            cur=conn.execute("""SELECT group_id,region,watershed_name,survey_year,
                recorded_name,source_url,source_archive_sha256
                FROM survey_evidence ORDER BY evidence_id""")
            for group,region,watershed,year,name,url,digest in cur:
                if (group not in counts or region not in REGIONS
                    or not URL.fullmatch(url or "")
                    or not re.fullmatch(r"(?:19|20)\d{2}",year or "")
                    or year>"2026"
                    or not (1<=len(watershed)<=80 and 1<=len(name)<=150)
                    or ((digest or "")!="" and not HEX.fullmatch(digest))
                    or (group!="fish" and not HEX.fullmatch(digest or ""))):
                    raise ValueError("Unapproved data in WordPress package")
                writer.writerow((group,region,watershed,year,name,url,digest or ""))
                counts[group]+=1
    if counts!=EXPECTED:
        raise ValueError("CSV export rows do not match the original verified dataset")
    result={
        "version":VERSION,
        "publication_status":"not_imported_until_manual_admin_action",
        "counts":EXPECTED,
        "total":TOTAL,
        "groups":source.metadata["groups"],
        "source_dataset_sha256":sha(db),
        "sha256_csv":sha(csvfile),
        "geographic_scope":"regional_watershed_year_only",
        "taxonomy_identity_verified":False,
        "individual_river_presence_verified":False,
        "wordpress_posts_modified":False,
        "source":"国土交通省河川水辺の国勢調査（元資料URL）を加工して作成"
    }
    (target/"data/manifest.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    zip_path.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
        for f in sorted(target.rglob("*")):
            if f.is_file():
                z.write(f,arcname=str(f.relative_to(out)))
    with zipfile.ZipFile(zip_path) as z:
        if z.testzip() is not None:raise ValueError("ZIP CRC check failed")
        members=set(z.namelist())
        expected={str(Path("tsurikue-biota-search")/p) for p in SAFE_SOURCE_FILES}
        expected.update({"tsurikue-biota-search/data/survey_evidence.csv",
                         "tsurikue-biota-search/data/manifest.json"})
        if members!=expected:raise ValueError("Unexpected WordPress ZIP file listing")
        manifest2=json.loads(z.read("tsurikue-biota-search/data/manifest.json"))
        if hashlib.sha256(z.read("tsurikue-biota-search/data/survey_evidence.csv")).hexdigest()!=manifest2["sha256_csv"]:
            raise ValueError("Actual packaged CSV hash mismatch")
    return {"plugin_zip":str(zip_path),"size_bytes":zip_path.stat().st_size,
            "survey_rows":TOTAL,"groups":counts,
            "source_db_sha256":result["source_dataset_sha256"],
            "auto_installed":False,"wordpress_modified":False}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--db",required=True)
    p.add_argument("--manifest",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--zip",required=True)
    a=p.parse_args()
    print(json.dumps(build(a.db,a.manifest,a.out,a.zip),ensure_ascii=False,indent=2))
