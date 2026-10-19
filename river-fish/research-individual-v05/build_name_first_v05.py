#!/usr/bin/env python3
"""Name-first research index for actual river-labelled biota survey records.

The old v0.4 A/B/C classifications remain unchanged. This INDEPENDENT index
allows uniquely identifiable survey river labels with NO confirmed 10-digit
river code. No regional-code-to-prefecture inference, no locations, no WP.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import quote

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
EXPECTED_SOURCE_SHA="PENDING_SHA_FROM_MANIFEST"
EXPECTED_OLD_KEYS=408036
EXPECTED_RECOVERED=679478
EXPECTED_CODE_A=176777
EXPECTED_CODE_RIVERS=115

CATEGORIES=("fish","benthic_animals","birds","plants")
REVIEW_NAMES = [
    (re.compile(r"(?:^|[（(])(?:全域|全体|本流|本川|上流|下流|中流|流域|不明)"),"survey_section_label"),
    (re.compile(r"[()（）]"),"parenthesized_river_section"),
    (re.compile(r"[・／/,、]"),"composite_river_label"),
    (re.compile(r"(?:水系|流域|河川全体|その他|不明|未記入|未設定|合流|河口)$"),"general_or_nonriver_label"),
    (re.compile(r"(?:湖|沼|ダム|貯水池|海|湾)$"),"nonriver_waterbody"),
]
REGION_AUTHORITY={
    "chugoku":"中国地方整備局",
    "chubu":"中部地方整備局",
    "hokkaido":"北海道開発局",
    "hokuriku":"北陸地方整備局",
    "kanto":"関東地方整備局",
    "kinki":"近畿地方整備局",
    "kyushu":"九州地方整備局",
    "shikoku":"四国地方整備局",
    "tohoku":"東北地方整備局",
}

def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda:source.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()

def catalog_pairs(path):
    pairs=defaultdict(set)
    with Path(path).open(encoding="utf-8-sig",newline="") as f:
        for row in csv.DictReader(f):
            pairs[(row["watershed_name"],row["river_name"])].add(row["river_code"])
    return pairs

def review_name(name):
    if not name or len(name)>60 or not name.strip() or name.strip() in ("-","－","―","―","なし"):
        return "empty_or_invalid_name"
    for pattern,reason in REVIEW_NAMES:
        if pattern.search(name):
            return reason
    if re.search(r"[<>{}\n\r\t]",name):
        return "unsafe_label"
    return None

def identity_key(region,authority,watershed,river):
    b=json.dumps([region,authority,watershed,river],ensure_ascii=False,separators=(",",":")).encode()
    return "rn_"+hashlib.sha256(b).hexdigest()[:24]

def base_counts(conn):
    return {
        "original_keys":conn.execute("SELECT COUNT(*) FROM original_keys").fetchone()[0],
        "recovered_contexts":conn.execute("SELECT COUNT(*) FROM river_evidence").fetchone()[0],
        "A_records":conn.execute("SELECT COUNT(*) FROM approved_individual_river").fetchone()[0],
        "A_rivers":conn.execute("SELECT COUNT(DISTINCT river_code) FROM approved_individual_river").fetchone()[0],
        "key_counts":dict(conn.execute("SELECT s.group_id,COUNT(*) FROM original_keys k JOIN sources s ON s.id=k.source_id GROUP BY s.group_id")),
        "class_counts":dict(conn.execute("SELECT match_class,COUNT(*) FROM evidence GROUP BY match_class"))
    }

def make(source,dest,report_dir):
    source=Path(source).resolve()
    dest=Path(dest).resolve()
    report_dir=Path(report_dir)
    if dest.exists():
        raise FileExistsError("Will not overwrite research SQLite")
    actual_sha=digest(source)
    if actual_sha!=EXPECTED_SOURCE_SHA:
        raise ValueError(f"Unrecognized v04 SQLite SHA256: {actual_sha}")
    pairs=catalog_pairs(ROOT/"national-codes-staged/river_codes_national_v07.csv")
    old=sqlite3.connect("file:"+quote(str(source),safe="/")+"?mode=ro",uri=True)
    old.execute("PRAGMA query_only=ON")
    before=base_counts(old)
    if (before["original_keys"]!=EXPECTED_OLD_KEYS or
        before["recovered_contexts"]!=EXPECTED_RECOVERED or
        before["A_records"]!=EXPECTED_CODE_A or before["A_rivers"]!=EXPECTED_CODE_RIVERS):
        raise ValueError("Baseline counts changed")
    new=sqlite3.connect(dest)
    try:
        old.backup(new)
        old.close()
        new.execute("PRAGMA foreign_keys=ON")
        new.executescript("""
        CREATE TABLE name_first_rivers (
            identity_key TEXT PRIMARY KEY,
            region TEXT NOT NULL,
            source_authority TEXT NOT NULL,
            watershed_name TEXT NOT NULL,
            river_name TEXT NOT NULL,
            river_code TEXT,
            code_confidence TEXT NOT NULL,
            review_status TEXT NOT NULL CHECK(review_status IN ('eligible','hold')),
            review_reason TEXT,
            catalog_code_candidates INTEGER NOT NULL,
            survey_record_contexts INTEGER NOT NULL,
            UNIQUE(region,source_authority,watershed_name,river_name)
        );
        CREATE TABLE name_first_context_links(
            context_id INTEGER PRIMARY KEY REFERENCES river_context(id),
            identity_key TEXT NOT NULL REFERENCES name_first_rivers(identity_key)
        );
        CREATE INDEX name_first_region_water ON name_first_rivers(region,watershed_name,review_status,river_name);
        CREATE INDEX name_first_river_name ON name_first_rivers(river_name,review_status);
        CREATE INDEX name_first_code ON name_first_rivers(river_code);
        CREATE INDEX name_first_context_join ON name_first_context_links(identity_key);
        CREATE VIEW name_first_evidence AS
            SELECT n.identity_key,n.region,n.source_authority,n.watershed_name,
                n.river_name,n.river_code,n.code_confidence,
                s.group_id, e.survey_year,lb.recorded_name,
                s.source_url,s.source_sha256,e.source_rows,
                r.match_class AS original_code_match_class
            FROM name_first_rivers n
            JOIN name_first_context_links k ON k.identity_key=n.identity_key
            JOIN river_context r ON r.id=k.context_id
            JOIN river_evidence e ON e.river_context_id=r.id
            JOIN sources s ON s.id=e.source_id
            JOIN labels lb ON lb.id=e.label_id
            WHERE n.review_status='eligible';
        """)
        context_rows=new.execute("""
            SELECT r.id,w.region,w.watershed_name,r.river_name,r.source_authority,
                   r.river_code,r.match_class,r.target_scope,COUNT(e.id)
            FROM river_context r
            JOIN watersheds w ON w.id=r.watershed_id
            JOIN river_evidence e ON e.river_context_id=r.id
            GROUP BY r.id
            ORDER BY w.region,w.watershed_name,r.river_name,r.source_authority
        """).fetchall()
        merged=defaultdict(list)
        for ctxid,region,water,river,auth,code,cl,scope,count in context_rows:
            if cl=="C" or not river or scope!="individual_river":
                continue
            if cl not in ("A","B"):
                raise ValueError("Unexpected class of named source")
            merged[(region,auth,water,river)].append({
                "context_id":ctxid,"river_code":code,"match_class":cl,"records":count
            })
        rows=[];links=[]
        for (region,auth,water,river),contexts in sorted(merged.items()):
            codes={c["river_code"] for c in contexts if c["river_code"]}
            if len(codes)>1:
                raise ValueError("Multiple verified codes for one source-level identity")
            code=next(iter(codes)) if codes else None
            registry=pairs.get((water,river),set())
            problem=review_name(river)
            if auth!=REGION_AUTHORITY.get(region):
                problem="authority_region_not_verified"
            elif not water or not region or not auth:
                problem="missing_watershed_or_region"
            elif not code and len(registry)>1:
                problem="same_name_in_watershed_multiple_codes"
            if code:
                if code not in registry:
                    raise ValueError("Previously approved official code disappeared")
                if any(c["match_class"]=="B" for c in contexts):
                    # Do not merge unknown B under a previously known A code.
                    problem="mixed_code_verified_and_unverified_source_context"
            status="hold" if problem else "eligible"
            key=identity_key(region,auth,water,river)
            rows.append((
                key,region,auth,water,river,code,
                "approved_10digit" if code else "source_river_name_only",
                status,problem,len(registry),sum(c["records"] for c in contexts)
            ))
            links.extend((c["context_id"],key) for c in contexts)
        new.executemany("""
            INSERT INTO name_first_rivers(identity_key,region,source_authority,
            watershed_name,river_name,river_code,code_confidence,review_status,
            review_reason,catalog_code_candidates,survey_record_contexts)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
        """,rows)
        new.executemany("INSERT INTO name_first_context_links VALUES(?,?)",links)
        new.commit()
        after=base_counts(new)
        if before!=after:
            raise ValueError("Baseline immutable A/B/C data was unexpectedly modified")
        if new.execute("PRAGMA integrity_check").fetchone()[0]!="ok" or new.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("SQLite integrity or foreign keys broken")
        for code in ("8707090029","8202040001","8909030001"):
            if new.execute("SELECT COUNT(*) FROM name_first_evidence WHERE river_code=?",(code,)).fetchone()[0] != new.execute("SELECT COUNT(*) FROM approved_individual_river WHERE river_code=?",(code,)).fetchone()[0]:
                raise ValueError("Prior code-confirmed river regressed: "+code)
        status_counts=dict(new.execute("SELECT review_status,COUNT(*) FROM name_first_rivers GROUP BY review_status"))
        code_counts=dict(new.execute("SELECT code_confidence,COUNT(*) FROM name_first_rivers WHERE review_status='eligible' GROUP BY code_confidence"))
        counts=dict(new.execute("SELECT code_confidence,COUNT(*) FROM name_first_evidence GROUP BY code_confidence"))
        groups=dict(new.execute("SELECT group_id,COUNT(*) FROM name_first_evidence GROUP BY group_id"))
        if code_counts.get("approved_10digit")!=EXPECTED_CODE_RIVERS or counts.get("approved_10digit")!=EXPECTED_CODE_A:
            raise ValueError("Existing verified 115 rivers must stay in named index")
        if sum(counts.values())>EXPECTED_RECOVERED or sum(groups.values())!=sum(counts.values()):
            raise ValueError("Incorrect named-river context totals")

        region_rows=new.execute("""
            SELECT region,code_confidence,COUNT(*),SUM(survey_record_contexts)
            FROM name_first_rivers WHERE review_status='eligible'
            GROUP BY region,code_confidence ORDER BY region,code_confidence
        """).fetchall()
        hold_rows=new.execute("""
            SELECT region,watershed_name,river_name,review_reason,
                   catalog_code_candidates,survey_record_contexts
            FROM name_first_rivers WHERE review_status='hold'
            ORDER BY region,watershed_name,river_name
        """).fetchall()
        public_rows=new.execute("""
            SELECT identity_key,region,source_authority,watershed_name,river_name,
                   river_code,code_confidence,survey_record_contexts
            FROM name_first_rivers WHERE review_status='eligible'
            ORDER BY region,watershed_name,river_name
        """).fetchall()
        report_dir.mkdir(parents=True,exist_ok=True)
        def write(name,headers,content):
            with (report_dir/name).open("w",encoding="utf-8",newline="") as f:
                writer=csv.writer(f);writer.writerow(headers);writer.writerows(content)
        write("name_first_rivers_v05.csv",
              ["identity_key","region","source_authority","watershed_name","river_name",
               "river_code_optional","code_confidence","historical_record_contexts"],public_rows)
        write("name_first_by_region_v05.csv",
              ["region","code_confidence","river_names","historical_record_contexts"],region_rows)
        write("name_first_held_for_review_v05.csv",
              ["region","watershed_name","river_name","reason","national_code_candidates","historical_record_contexts"],hold_rows)
        report={
            "schema":"name-first-v05",
            "immutable_v04_input_sha256":EXPECTED_SOURCE_SHA,
            "original_aggregate_keys":after["original_keys"],
            "source_recovered_river_contexts":after["recovered_contexts"],
            "original_code_A_river_count":EXPECTED_CODE_RIVERS,
            "original_code_A_contexts":EXPECTED_CODE_A,
            "eligible_river_name_identities":status_counts.get("eligible",0),
            "new_eligible_name_only_rivers":code_counts.get("source_river_name_only",0),
            "name_only_historical_contexts":counts.get("source_river_name_only",0),
            "total_eligible_name_first_contexts":sum(counts.values()),
            "held_identity_count":status_counts.get("hold",0),
            "held_historical_contexts":new.execute("""
                SELECT COALESCE(SUM(survey_record_contexts),0)
                FROM name_first_rivers WHERE review_status='hold'
            """).fetchone()[0],
            "all_four_categories":groups,
            "region_breakdown":[dict(zip(["region","code_status","river_names","records"],r)) for r in region_rows],
            "hold_reason_counts":dict(new.execute("""
                SELECT review_reason,COUNT(*) FROM name_first_rivers
                WHERE review_status='hold' GROUP BY review_reason
            """)),
            "database_integrity":"ok",
            "source_identity_rule":"source administrative region + independent source authority + survey watershed label + survey river label",
            "survey_name_not_necessarily_geospatially_verified":True,
            "not_a_current_species_checklist":True,
            "prefecture_not_inferred":True,
            "watershed_only_C_not_in_individual_river_results":True,
            "original_A_B_C_preserved":True,
            "code_optional_not_auto_inferred":True,
            "wordpress_changed":False,
            "production_mysql_changed":False
        }
        (report_dir/"name_first_audit_v05.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(report,ensure_ascii=False))
        return report
    finally:
        new.close()
        try:old.close()
        except Exception:pass

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--report-dir",required=True)
    a=p.parse_args()
    make(a.source,a.out,a.report_dir)
