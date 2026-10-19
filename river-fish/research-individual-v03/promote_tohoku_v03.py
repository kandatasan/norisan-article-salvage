#!/usr/bin/env python3
"""Create a NEW, offline SQLite research snapshot with independently reviewed Tohoku evidence.

The v0.1 SQLite remains read-only and unchanged. No site, network, WP or MySQL calls.
Only context IDs uniquely supported by the pinned Tohoku code ledger may move B -> A.
Keep individual-river evidence distinct from watershed-only history.
"""
import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import sqlite3
from urllib.parse import quote

HERE=Path(__file__).resolve().parent
RIVER_ROOT=HERE.parent
V01=RIVER_ROOT/"research-individual-v01"
V02=RIVER_ROOT/"research-individual-v02"
EXPECTED_V01_SHA="9143419acb23c9181eaea8112ca44d0b219a92a15723baa1ae43ef075b0b9f34"
EXPECTED_TOHOKU_SOURCE_SHA="cde06431d9f50fbccf9ac4606544a595168d86ea44b1864a9c47ccbf8e5111f8"
COUNTS={"fish":18814,"benthic_animals":74949,"birds":44093,"plants":270180}
EXPECTED_RECOVERED=679478
EXPECTED_OLD_APPROVED=84965
EXPECTED_TOHOKU=70191
EXPECTED_NEW_RIVERS=62
ORIGINAL_CODE="8707090029"
PROBE_TOHOKU="8202040001"

def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()

def csvrows(path):
    with Path(path).open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))

def validate_inputs(crosswalk,counts):
    ledger=csvrows(crosswalk);candidate=csvrows(counts)
    if len(ledger)!=1953 or len(candidate)!=152:raise ValueError("Research evidence cardinality unexpected")
    with (V02/"outputs/tohoku_crosswalk_review.json").open(encoding="utf-8") as f:review=json.load(f)
    if (review["pinned_sha256"]!=EXPECTED_TOHOKU_SOURCE_SHA or
        review["candidate_B_records_supported_by_ledger"]!=EXPECTED_TOHOKU or
        review["candidate_rivers_with_records"]!=EXPECTED_NEW_RIVERS):
        raise ValueError("Tohoku independent ledger source changed")
    catalog={r["river_code"]:r for r in csvrows(RIVER_ROOT/"national-codes-staged/river_codes_national_v07.csv")}
    mapping={}
    for row in ledger:
        if row["region"]!="tohoku" or row["source_authority"]!="東北地方整備局":
            raise ValueError("Authority/region mismatch")
        if row["source_sha256"]!=EXPECTED_TOHOKU_SOURCE_SHA:
            raise ValueError("Unpinned code source")
        key=row["watershed_name"],row["river_name"]
        if key in mapping:raise ValueError("Ambiguous name under watershed")
        c=catalog.get(row["river_code"])
        if (not c or c["river_name"]!=row["river_name"]
            or c["watershed_name"]!=row["watershed_name"]
            or c["watershed_code"]!=row["watershed_code"]
            or c["river_code"][:6]!=row["watershed_code"]):
            raise ValueError("Official code/name/watershed mismatch")
        mapping[key]=row
    pairs=defaultdict(dict)
    for row in candidate:
        key=row["watershed_name"],row["river_name"]
        authority=mapping.get(key)
        if not authority or row["river_code"]!=authority["river_code"] or row["watershed_code"]!=authority["watershed_code"]:
            raise ValueError("Candidate not in approved official code ledger")
        if row["region"]!="tohoku" or row["group"] not in COUNTS:raise ValueError("Candidate category invalid")
        if row["group"] in pairs[key]:raise ValueError("Duplicate category in candidate")
        pairs[key][row["group"]]=row
    if len(pairs)!=EXPECTED_NEW_RIVERS or sum(int(x["recovered_records"]) for x in candidate)!=EXPECTED_TOHOKU:
        raise ValueError("Candidate identity or totals changed")
    return mapping,pairs

def read_connection(path):
    p=Path(path).resolve()
    return sqlite3.connect("file:"+quote(str(p),safe="/")+"?mode=ro",uri=True)

def original_class_counts(c):
    return dict(c.execute("SELECT match_class,COUNT(*) FROM original_keys GROUP BY match_class"))

def group_counts(c):
    return dict(c.execute("SELECT s.group_id,COUNT(*) FROM original_keys k JOIN sources s ON k.source_id=s.id GROUP BY s.group_id"))

def total_approved(c):
    return c.execute("SELECT COUNT(*) FROM approved_individual_river").fetchone()[0]

def direct_group_counts(c,code):
    return dict(c.execute("""
    SELECT s.group_id,COUNT(*) FROM river_evidence e
    JOIN river_context r ON r.id=e.river_context_id
    JOIN sources s ON s.id=e.source_id
    WHERE r.river_code=? AND r.match_class='A'
    GROUP BY s.group_id
    """,(code,)))

def run(source,dest,out_dir,crosswalk,counts):
    source=Path(source);dest=Path(dest);out_dir=Path(out_dir)
    if dest.exists():raise FileExistsError(dest)
    if digest(source)!=EXPECTED_V01_SHA:raise ValueError("Original independently verified v0.1 SQLite SHA changed")
    mapping,pairs=validate_inputs(crosswalk,counts)
    baseline=read_connection(source)
    if baseline.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
        raise ValueError("Baseline SQLite integrity")
    before={"original_keys":baseline.execute("SELECT COUNT(*) FROM original_keys").fetchone()[0],
            "recovered":baseline.execute("SELECT COUNT(*) FROM river_evidence").fetchone()[0],
            "approved":total_approved(baseline),
            "original_classes":original_class_counts(baseline),
            "groups":group_counts(baseline),
            "misasa":direct_group_counts(baseline,ORIGINAL_CODE)}
    if (before["original_keys"]!=408036 or before["recovered"]!=EXPECTED_RECOVERED or
        before["approved"]!=EXPECTED_OLD_APPROVED or before["groups"]!=COUNTS or
        before["misasa"]!={"fish":67,"benthic_animals":464,"birds":214,"plants":1347}):
        raise ValueError("Unexpected original research snapshot, refusing promotion")
    new=sqlite3.connect(dest)
    try:
        baseline.backup(new)
        baseline.close()
        new.execute("PRAGMA foreign_keys=ON")
        before_chugoku=new.execute("""
            SELECT COUNT(*) FROM approved_individual_river WHERE region='chugoku'
        """).fetchone()[0]
        promoted_contexts=0
        promoted_records=0
        for (water,river),rows_by_group in sorted(pairs.items()):
            approval=mapping[(water,river)]
            hits=new.execute("""
                SELECT r.id,r.match_class,r.river_code,r.source_authority,r.target_scope
                FROM river_context r JOIN watersheds w ON r.watershed_id=w.id
                WHERE w.region='tohoku' AND w.watershed_name=? AND r.river_name=?
            """,(water,river)).fetchall()
            if len(hits)!=1 or hits[0][1:]!=("B",None,"東北地方整備局","individual_river"):
                raise ValueError("Nonunique/unexpected existing river context: "+repr((water,river,hits)))
            ctx_id=hits[0][0]
            measured=dict(new.execute("""
                SELECT s.group_id,COUNT(*) FROM river_evidence e
                JOIN sources s ON e.source_id=s.id
                WHERE e.river_context_id=? GROUP BY s.group_id
            """,(ctx_id,)))
            claimed={k:int(v["recovered_records"]) for k,v in rows_by_group.items()}
            if measured!=claimed:raise ValueError("Actual evidence disagrees: "+repr((water,river,measured,claimed)))
            updated=new.execute("""
                UPDATE river_context
                SET river_code=?,watershed_code=?,match_class='A',
                    match_reason=?,code_source_url=?,code_source_page=?
                WHERE id=? AND match_class='B' AND river_code IS NULL
            """,(
                approval["river_code"],approval["watershed_code"],
                "Tohoku pinned code ledger: full 10-digit code/name matches watershed page header and national code; unique code-name within verified ledger",
                approval["code_source_url"],approval["code_source_page"],ctx_id
            ))
            if updated.rowcount!=1:raise ValueError("Failed to update exactly one existing river context")
            promoted_contexts+=1
            promoted_records+=sum(measured.values())
        if promoted_contexts!=EXPECTED_NEW_RIVERS or promoted_records!=EXPECTED_TOHOKU:
            raise ValueError("Promotion counts differ from independent CSV")

        # Preserve exact original-key semantics: A iff ALL recovered river
        # contexts for the original category/watershed/year/name are A.
        grouped=new.execute("""
            SELECT e.source_id,r.watershed_id,e.label_id,e.survey_year,
              MAX(r.match_class='A') a,MAX(r.match_class='B') b,
              MAX(r.match_class='C') c,MAX(r.match_class='D') d,
              MIN(r.match_class='A') all_a
            FROM river_evidence e JOIN river_context r ON e.river_context_id=r.id
            JOIN watersheds w ON r.watershed_id=w.id
            WHERE w.region='tohoku'
            GROUP BY e.source_id,r.watershed_id,e.label_id,e.survey_year
        """).fetchall()
        corrected=0
        updates=[]
        for sid,wid,lid,year,a,b,c,d,all_a in grouped:
            state="A" if all_a else ("D" if d else ("B" if b else "C"))
            updates.append((state,int(bool(a)),sid,wid,lid,year))
        new.executemany("""
            UPDATE original_keys SET match_class=?,has_any_approved_river=?
            WHERE source_id=? AND watershed_id=? AND label_id=? AND survey_year=?
        """,updates)
        if new.execute("SELECT changes()").fetchone()[0] not in (0,1):
            pass # executemany rowcount is audited against the grouped total below
        if new.execute("""
            SELECT COUNT(*) FROM original_keys k JOIN watersheds w ON k.watershed_id=w.id
            WHERE w.region='tohoku'
        """).fetchone()[0]!=len(grouped):
            raise ValueError("Original key coverage mismatch after recompute")
        new.commit()
        after={"original_keys":new.execute("SELECT COUNT(*) FROM original_keys").fetchone()[0],
               "recovered":new.execute("SELECT COUNT(*) FROM river_evidence").fetchone()[0],
               "approved":total_approved(new),"original_classes":original_class_counts(new),
               "groups":group_counts(new),"misasa":direct_group_counts(new,ORIGINAL_CODE),
               "tohoku":new.execute("SELECT COUNT(*) FROM approved_individual_river WHERE region='tohoku'").fetchone()[0]}
        if (after["original_keys"]!=before["original_keys"] or after["recovered"]!=before["recovered"]
            or after["groups"]!=before["groups"] or after["misasa"]!=before["misasa"]
            or after["approved"]!=before["approved"]+EXPECTED_TOHOKU
            or after["tohoku"]!=EXPECTED_TOHOKU
            or new.execute("SELECT COUNT(*) FROM approved_individual_river WHERE region='chugoku'").fetchone()[0]!=before_chugoku):
            raise ValueError("Baseline count or evidence regression")
        if new.execute("PRAGMA integrity_check").fetchone()[0]!="ok" or new.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("SQLite constraints failed")
        if new.execute("SELECT COUNT(*) FROM evidence WHERE match_class!='A' AND river_code IS NOT NULL").fetchone()[0]:
            raise ValueError("Unapproved river given code")
        codes=new.execute("""
            SELECT region,river_code,COUNT(*) FROM approved_individual_river
            GROUP BY region,river_code ORDER BY region,river_code
        """).fetchall()
        river_count=len(codes)
        if river_count!=44+EXPECTED_NEW_RIVERS or sum(n for _,_,n in codes)!=after["approved"]:
            raise ValueError("Unexpected approved river identities")
        av=new.execute("""
            SELECT r.river_code,w.region,w.watershed_name,r.river_name,
               s.group_id,COUNT(*) records,COUNT(DISTINCT e.label_id) literal_names,
               MIN(e.survey_year),MAX(e.survey_year)
            FROM river_evidence e JOIN river_context r ON r.id=e.river_context_id
            JOIN watersheds w ON w.id=r.watershed_id
            JOIN sources s ON s.id=e.source_id
            WHERE r.match_class='A'
            GROUP BY r.river_code,w.region,w.watershed_name,r.river_name,s.group_id
            ORDER BY w.region,w.watershed_name,r.river_name,s.group_id
        """).fetchall()
        out_dir.mkdir(parents=True,exist_ok=True)
        with (out_dir/"confirmed_river_group_counts_v03.csv").open("w",encoding="utf-8",newline="") as f:
            w=csv.writer(f);w.writerow(["river_code","region","watershed","river","group","records","literal_names_not_species","year_min","year_max"]);w.writerows(av)
        report={"schema":"v03","baseline_sqlite_sha256":EXPECTED_V01_SHA,
                "tohoku_ledger_sha256":EXPECTED_TOHOKU_SOURCE_SHA,
                "baseline":before,"expanded":after,
                "new_tohoku_rivers":promoted_contexts,"new_tohoku_individual_record_contexts":promoted_records,
                "total_confirmed_rivers":river_count,
                "tohoku_example_code":PROBE_TOHOKU,
                "tohoku_example_group_counts":direct_group_counts(new,PROBE_TOHOKU),
                "changed_original_key_classes":{c:after["original_classes"].get(c,0)-before["original_classes"].get(c,0) for c in ("A","B","C","D")},
                "unit":"river / year / literal name / category contexts, not raw observations",
                "research_only":True,"wordpress_changed":False,"mysql_changed":False,
                "prefecture_not_inferred":True,"individual_river_scope_only":True}
        (out_dir/"integration_validation_v03.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        return report
    finally:
        new.close()
        try:baseline.close()
        except Exception:pass

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True);p.add_argument("--out",required=True)
    p.add_argument("--report-dir",required=True)
    p.add_argument("--crosswalk",default=str(V02/"outputs/tohoku_independent_crosswalk.csv"))
    p.add_argument("--candidate-counts",default=str(V02/"outputs/tohoku_B_to_A_candidate_counts.csv"))
    a=p.parse_args()
    result=run(a.source,a.out,a.report_dir,a.crosswalk,a.candidate_counts)
    print(json.dumps({k:v for k,v in result.items() if k!="baseline" and k!="expanded"},ensure_ascii=False))
