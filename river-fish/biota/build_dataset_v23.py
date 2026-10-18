#!/usr/bin/env python3
"""Build immutable, provenance-preserving v2.3 *data* snapshots.

Data/config changes do not require touching the generic search engine or UI.
Legacy v1.9 fish/benthic table adapters are audited and fixed. Additional
independently audited groups are added ONLY as hash-pinned staged CSV files
with the exact approved columns. No taxonomy/location joins or WP writes.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
from urllib.parse import urlparse

HERE=Path(__file__).resolve().parent
REGISTRY=HERE/"dataset_sources_v23.json"
VERSION=1
REGIONS={"hokkaido","tohoku","kanto","hokuriku","chubu","kinki",
         "chugoku","shikoku","kyushu"}
CSV_COLS=("region","watershed","survey_year","recorded_name","source_url","source_sha256")
GROUP=re.compile(r"[a-z][a-z0-9_]{1,39}\Z")
HEX=re.compile(r"[0-9a-f]{64}\Z")
YEAR=re.compile(r"(?:19|20)[0-9]{2}\Z")
LEGACY={
 "legacy_v19_fish":("watershed_year_fish_evidence",
                    "region, watershed_name, survey_year, literal_recorded_name, source_url, ''"),
 "legacy_v19_benthic":("watershed_year_benthic_evidence",
                       "region, watershed_name, survey_year, literal_recorded_name, official_source_url, source_zip_sha256")
}

def sha256_file(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def source_ok(url):
    try:
        p=urlparse(url)
        return p.scheme=="https" and p.hostname=="www.nilim.go.jp" and not p.username and not p.password and not p.fragment and p.path.startswith("/lab/fbg/ksnkankyo/")
    except ValueError:
        return False

def check_config(config):
    if set(config)!={"contract_version","publication_status","geographic_scope",
                    "taxonomy_identity_verified","source_groups","unavailable_separate_groups","note"}:
        raise ValueError("Data source registry schema changed")
    if (config["contract_version"]!=VERSION or
        config["publication_status"]!="research_only_not_wordpress" or
        config["geographic_scope"]!="regional_watershed_year_only" or
        config["taxonomy_identity_verified"] is not False):
        raise ValueError("Unreviewed publishing or geographic source contract")
    groups=config["source_groups"]
    if not isinstance(groups,list) or not 1<=len(groups)<=12:
        raise ValueError("Unsupported number of source groups")
    seen=set()
    for g in groups:
        if not isinstance(g,dict) or not GROUP.fullmatch(g.get("id","")) or g["id"] in seen:
            raise ValueError("Invalid or duplicate biological group ID")
        seen.add(g["id"])
        if not 1<=len(g.get("label",""))<=60 or not 1<=len(g.get("note",""))<=200:
            raise ValueError("Missing reviewed group label")
        if isinstance(g.get("expected_rows"),bool) or not isinstance(g.get("expected_rows"),int) or not 1<=g["expected_rows"]<=2_000_000:
            raise ValueError("Invalid audited expected row count")
        kind=g.get("kind")
        if kind in LEGACY:
            if set(g)!={"id","label","note","kind","expected_rows"}:
                raise ValueError("Unexpected legacy source parameters")
            if g["id"]!=("fish" if kind=="legacy_v19_fish" else "benthic_animals"):
                raise ValueError("Legacy source must keep established survey group identity")
        elif kind=="verified_csv":
            if set(g)!={"id","label","note","kind","expected_rows","file","sha256","reviewed_original_category"}:
                raise ValueError("Missing provenance for reviewed CSV")
            if (not isinstance(g["file"],str) or
                not re.fullmatch(r"[a-zA-Z0-9_.-]{1,90}\.csv",g["file"]) or
                not HEX.fullmatch(g.get("sha256","")) or
                not isinstance(g["reviewed_original_category"],str) or
                not 1<=len(g["reviewed_original_category"])<=80):
                raise ValueError("Reviewed CSV requires exact file/hash/category")
        else:
            raise ValueError("Unapproved import source kind")
    unavailable=config["unavailable_separate_groups"]
    if not isinstance(unavailable,dict) or len(unavailable)>12:
        raise ValueError("Unavailable group format changed")
    for key,val in unavailable.items():
        if not GROUP.fullmatch(key) or not isinstance(val,str) or len(val)>180:
            raise ValueError("Invalid pending group")
    if set(unavailable).intersection(seen):
        raise ValueError("Pending classification cannot also be available")
    return groups

def validated_record(values):
    region,watershed,year,name,url,source_sha=values
    if region not in REGIONS:
        raise ValueError("Official region is not one of nine surveyed areas")
    if not isinstance(watershed,str) or not 1<=len(watershed.strip())<=80:
        raise ValueError("Missing or unbounded watershed")
    if not isinstance(name,str) or not 1<=len(name.strip())<=150:
        raise ValueError("Missing or unbounded literal organism label")
    if any(x[0] in "=+-@" for x in (watershed,name)):
        raise ValueError("Suspicious text-as-formula input")
    if not YEAR.fullmatch(year) or year>"2026":
        raise ValueError("Unreviewed or future survey year")
    if not source_ok(url):
        raise ValueError("Non-official biological source URL")
    if source_sha and not HEX.fullmatch(source_sha):
        raise ValueError("Invalid official source archive checksum")
    return (region,watershed.strip(),year,name.strip(),url,source_sha)

def read_rows(group,legacy,staging):
    if group["kind"] in LEGACY:
        if not legacy or not Path(legacy).is_file():
            raise FileNotFoundError("Verified v1.9 research SQLite is required")
        table,fields=LEGACY[group["kind"]]
        conn=sqlite3.connect("file:"+Path(legacy).resolve().as_uri()[5:]+"?mode=ro",uri=True)
        try:
            conn.execute("PRAGMA query_only=ON")
            if conn.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
                raise ValueError("Legacy research SQLite integrity check failed")
            rows=conn.execute("SELECT "+fields+" FROM "+table).fetchall()
        finally:
            conn.close()
        for item in rows:
            yield validated_record(item)
    else:
        root=Path(staging).resolve() if staging else None
        if root is None:
            raise ValueError("Staged source directory required for reviewed CSV")
        candidate=(root/group["file"]).resolve()
        if candidate.parent!=root or not candidate.is_file() or candidate.is_symlink():
            raise ValueError("Unsafe or absent reviewed CSV")
        if sha256_file(candidate)!=group["sha256"]:
            raise ValueError("Reviewed source CSV SHA-256 mismatch")
        with candidate.open("r",encoding="utf-8-sig",newline="") as f:
            reader=csv.DictReader(f)
            if tuple(reader.fieldnames or ())!=CSV_COLS:
                raise ValueError("Reviewed source CSV header changed")
            for r in reader:
                if None in r or any(v is None for v in r.values()):
                    raise ValueError("Malformed CSV observation row")
                yield validated_record(tuple(r[c] for c in CSV_COLS))

def build(legacy_db,out_db,out_manifest,registry=REGISTRY,staged_dir=None):
    out_db=Path(out_db).resolve()
    out_manifest=Path(out_manifest).resolve()
    if out_db==out_manifest or out_db.exists() or out_manifest.exists():
        raise FileExistsError("Immutable snapshot paths must not exist")
    if out_db.suffix!=".sqlite" or out_manifest.suffix!=".json":
        raise ValueError("Expect SQLite snapshot and JSON manifest")
    if out_db.parent!=out_manifest.parent:
        raise ValueError("Snapshot and manifest must share a directory")
    config=json.loads(Path(registry).read_text(encoding="utf-8"))
    groups=check_config(config)
    out_db.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="biota-build-",dir=out_db.parent) as temp:
        dbfile=Path(temp)/"snapshot.sqlite"
        manifestfile=Path(temp)/"manifest.json"
        conn=sqlite3.connect(dbfile)
        try:
            conn.executescript("""
                PRAGMA foreign_keys=ON;
                CREATE TABLE dataset_contract(
                    id INTEGER PRIMARY KEY CHECK(id=1),
                    schema_version INTEGER NOT NULL CHECK(schema_version=1),
                    geographic_scope TEXT NOT NULL CHECK(geographic_scope='regional_watershed_year_only'),
                    taxonomy_identity_verified INTEGER NOT NULL CHECK(taxonomy_identity_verified=0)
                );
                INSERT INTO dataset_contract VALUES(1,1,'regional_watershed_year_only',0);
                CREATE TABLE available_groups(
                    group_id TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    note TEXT NOT NULL,
                    reviewed_source_rows INTEGER NOT NULL
                );
                CREATE TABLE survey_evidence(
                    evidence_id INTEGER PRIMARY KEY,
                    group_id TEXT NOT NULL REFERENCES available_groups(group_id),
                    region TEXT NOT NULL,
                    watershed_name TEXT NOT NULL,
                    survey_year TEXT NOT NULL,
                    recorded_name TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    source_archive_sha256 TEXT NOT NULL,
                    geographic_scope TEXT NOT NULL CHECK(geographic_scope='regional_watershed_year_only'),
                    verified_prefecture TEXT CHECK(verified_prefecture IS NULL),
                    verified_individual_river TEXT CHECK(verified_individual_river IS NULL),
                    approved_taxon_code TEXT CHECK(approved_taxon_code IS NULL),
                    UNIQUE(group_id,region,watershed_name,survey_year,recorded_name,source_url)
                );
                CREATE INDEX evidence_group_region_watershed ON survey_evidence(group_id,region,watershed_name);
                CREATE INDEX evidence_group_name ON survey_evidence(group_id,recorded_name);
                CREATE INDEX evidence_region_watershed_year ON survey_evidence(region,watershed_name,survey_year);
            """)
            counts={}
            for g in groups:
                group_id=g["id"]
                conn.execute("INSERT INTO available_groups VALUES (?,?,?,?)",
                             (group_id,g["label"],g["note"],g["expected_rows"]))
                n=0
                for item in read_rows(g,legacy_db,staged_dir):
                    conn.execute("""
                        INSERT INTO survey_evidence(
                            group_id,region,watershed_name,survey_year,recorded_name,
                            source_url,source_archive_sha256,geographic_scope,
                            verified_prefecture,verified_individual_river,approved_taxon_code
                        ) VALUES(?,?,?,?,?,?,?,'regional_watershed_year_only',NULL,NULL,NULL)
                    """,(group_id,*item))
                    n+=1
                    if n>g["expected_rows"]:
                        raise ValueError("Unexpected extra source rows for "+group_id)
                if n!=g["expected_rows"]:
                    raise ValueError("Missing audited source rows for "+group_id)
                counts[group_id]=n
            conn.commit()
            if conn.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
                raise ValueError("Output data SQLite failed integrity_check")
            if conn.execute("PRAGMA foreign_key_check").fetchall():
                raise ValueError("Output SQLite foreign key failure")
            if conn.execute("SELECT COUNT(*) FROM survey_evidence WHERE verified_prefecture IS NOT NULL OR verified_individual_river IS NOT NULL OR approved_taxon_code IS NOT NULL").fetchone()[0]!=0:
                raise ValueError("Unsafe location or taxonomy attribution found")
        finally:
            conn.close()
        registry_digest=sha256_file(registry)
        result={
            "contract_version":VERSION,
            "publication_status":"research_only_not_wordpress",
            "database_filename":out_db.name,
            "database_sha256":sha256_file(dbfile),
            "registry_sha256":registry_digest,
            "group_counts":counts,
            "total_survey_rows":sum(counts.values()),
            "groups":[{"id":g["id"],"label":g["label"],"note":g["note"],"source_rows":counts[g["id"]]} for g in groups],
            "unavailable_separate_groups":config["unavailable_separate_groups"],
            "geographic_scope":"regional_watershed_year_only",
            "taxonomy_identity_verified":False,
            "individual_river_verified":False,
            "prefecture_presence_verified":False,
            "wordpress_modified":False
        }
        manifestfile.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        # Data and manifest move only after full build/validation. No overwrites.
        if out_db.exists() or out_manifest.exists():
            raise FileExistsError("Target created during staging")
        try:
            os.replace(dbfile,out_db)
            os.replace(manifestfile,out_manifest)
        except Exception:
            out_db.unlink(missing_ok=True)
            raise
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--legacy-db",required=True)
    p.add_argument("--db",required=True)
    p.add_argument("--manifest",required=True)
    p.add_argument("--registry",default=str(REGISTRY))
    p.add_argument("--staged-dir")
    args=p.parse_args()
    print(json.dumps(build(args.legacy_db,args.db,args.manifest,args.registry,args.staged_dir),
                     ensure_ascii=False,indent=2))
if __name__=="__main__":
    main()
