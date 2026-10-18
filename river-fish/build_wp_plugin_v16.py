#!/usr/bin/env python3
"""Make installable WP plugin ZIP with three source-scoped CSV snapshots.

No WP credentials, no HTTP and no server writes: reproducible from GitHub
v1.5 audited nationwide data. PHP's importer checks SHA-256 before switching
from an old, complete generation to a newly validated one.

Data source files are generated during CI, not versioned twice in the repo.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from build_river_beta_v15 import create_payload, verified_url

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/"wp-plugin/tsurikue-river-search"
VERSION="v1.5-20261018"
COUNTS={"codes":35449,"local":1449,"fish":18814}
FILES={
    "codes":("river_codes.csv",["river_code","river_name","watershed_name","watershed_code","source_url"]),
    "local":("source_mentions.csv",["prefecture","name","kind","watershed","area",
                                    "source_url","source_id","source_scope","source_date"]),
    "fish":("watershed_fish.csv",["region_code","watershed_name","survey_year",
                                 "fish_name","source_url"])
}
SAFE_SOURCE_FILES=[
    "tsurikue-river-search.php",
    "includes/class-tsr-search.php",
    "includes/class-tsr-import.php",
    "assets/river-search.js",
    "assets/river-search.css",
    "assets/river-admin.js",
    "readme.txt",
]
EXPECTED_COLUMN_LENGTHS={"codes":5,"local":9,"fish":5}


def prepare_rows():
    p=create_payload()
    code_url=verified_url(p["meta"]["officialRiverSource"])
    out={
        "codes":[[code,name,basin,basin_code,code_url] for code,name,basin,basin_code in p["riverCodes"]],
        "local":list(p["localEvidence"]),
        "fish":list(p["fishCensus"])
    }
    assert {k:len(v) for k,v in out.items()} == COUNTS
    assert set(x[0] for x in out["local"])==set(p["prefectures"])
    for k,rows in out.items():
        for row in rows:
            if len(row)!=EXPECTED_COLUMN_LENGTHS[k]:
                raise ValueError("Data shape unsafe: "+k)
            verified_url(row[4] if k!="local" else row[5])
    return out


def build(out_dir,zip_path):
    out_dir=Path(out_dir)
    zip_path=Path(zip_path)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError("Target directory already contains data")
    if zip_path.exists():
        raise FileExistsError("Do not overwrite ZIP")
    rows=prepare_rows()
    root=out_dir/"tsurikue-river-search"
    data_dir=root/"data"
    data_dir.mkdir(parents=True,exist_ok=True)
    for source in SAFE_SOURCE_FILES:
        path=SOURCE/source
        if not path.is_file():
            raise FileNotFoundError("Plugin component missing: "+source)
        target=root/source
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,target)

    sha={}
    for k,(file_name,columns) in FILES.items():
        path=data_dir/file_name
        with path.open("w",encoding="utf-8",newline="") as f:
            writer=csv.writer(f,quoting=csv.QUOTE_MINIMAL,lineterminator="\n")
            writer.writerow(columns)
            for record in rows[k]:
                writer.writerow(record)
        # Validate the bytes that will be uploaded, not only source objects.
        with path.open(encoding="utf-8",newline="") as f:
            reader=csv.reader(f)
            assert next(reader)==columns
            actual=list(reader)
        if len(actual)!=COUNTS[k]:
            raise ValueError("Installed CSV row count inconsistent")
        sha[k]=hashlib.sha256(path.read_bytes()).hexdigest()

    manifest={
        "version":VERSION,
        "counts":COUNTS,
        "sha256":sha,
        "source_scope":{
            "codes":"official_code_and_name_only_no_geographic_prefecture",
            "local":"prefecture_document_mentions_not_exact_geolocation",
            "fish":"region_watershed_year_name_only_not_specific_tributary"
        },
        "status":"not_imported_until_manual_admin_action",
        "published_to_wordpress":False
    }
    (data_dir/"manifest.json").write_text(
        json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    zip_path.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for source in sorted(root.rglob("*")):
            if source.is_file():
                z.write(source,arcname=str(source.relative_to(out_dir)))
    with zipfile.ZipFile(zip_path) as z:
        if z.testzip() is not None:
            raise ValueError("Plugin ZIP CRC failed")
        names=z.namelist()
        if not all(x.startswith("tsurikue-river-search/") for x in names):
            raise ValueError("Plugin ZIP root must be installable directory")
        if len(names)!=len(SAFE_SOURCE_FILES)+4:
            raise ValueError("Unexpected plugin ZIP file list")
    return {
        "plugin_zip":str(zip_path),
        "zip_bytes":zip_path.stat().st_size,
        "uncompressed_csv_bytes":sum((data_dir/name).stat().st_size for name,_ in FILES.values()),
        "counts":COUNTS,"manifest":manifest,
        "plugin_path":str(root)
    }

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True,help="Non-existing or empty build directory")
    p.add_argument("--zip",required=True,help="New installable zip destination")
    a=p.parse_args()
    print(json.dumps(build(a.out,a.zip),ensure_ascii=False,indent=2))
