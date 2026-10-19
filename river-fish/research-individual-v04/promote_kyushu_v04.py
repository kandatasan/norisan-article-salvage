#!/usr/bin/env python3
"""Build NEW research v0.4 SQLite by promoting only nine independently proved Kyushu rivers.

Never modify or replace the pinned v0.3 input or any production system.
Evidence conditions: JMA 2026 direct exact river-name/10-digit code + separate
MLIT watershed/river pairing + national official river catalog.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
from urllib.parse import quote

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/"research-individual-v04/outputs"
SOURCE_DB_SHA="67046cdea0533a708a1a9101ef8889ad756a9fb963c25eff794599e32c96f4dc"
JMA_SHA="1fd72d7aaca4c42292249012de4dee03e0fa2e40554ac55b33ab12e306bb3275"
MLIT_SHA="36d0cfacef4c6fffbb0df7b2019aeadcdb0a5b3e554894a0c236263894077489"
EXPECTED_PREVIOUS_A=155156
EXPECTED_NEW_A=21621
EXPECTED_RIVERS=9
TOTAL_A=EXPECTED_PREVIOUS_A+EXPECTED_NEW_A
EXPECTED_BASE=408036
EXPECTED_RECOVERED=679478

def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()

def read(path):
    with Path(path).open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))

def read_db(path):
    return sqlite3.connect("file:"+quote(str(Path(path).resolve()),safe="/")+"?mode=ro",uri=True)

def metrics(conn):
    return {
      "original":conn.execute("SELECT COUNT(*) FROM original_keys").fetchone()[0],
      "recovered":conn.execute("SELECT COUNT(*) FROM river_evidence").fetchone()[0],
      "approved":conn.execute("SELECT COUNT(*) FROM approved_individual_river").fetchone()[0],
      "rivers":conn.execute("SELECT COUNT(DISTINCT river_code) FROM approved_individual_river").fetchone()[0],
      "original_classes":dict(conn.execute("SELECT match_class,COUNT(*) FROM original_keys GROUP BY match_class")),
      "recovered_classes":dict(conn.execute("SELECT match_class,COUNT(*) FROM evidence GROUP BY match_class")),
      "group_counts":dict(conn.execute("SELECT s.group_id,COUNT(*) FROM original_keys k JOIN sources s ON s.id=k.source_id GROUP BY s.group_id"))
    }

def direct(conn,code):
    return dict(conn.execute("""
      SELECT s.group_id,COUNT(*) FROM river_evidence e
      JOIN sources s ON s.id=e.source_id
      JOIN river_context r ON r.id=e.river_context_id
      WHERE r.river_code=? AND r.match_class='A'
      GROUP BY s.group_id
    """,(code,)))

def run(source,dest,out_dir):
    source=Path(source);dest=Path(dest);out_dir=Path(out_dir)
    if dest.exists():raise FileExistsError(dest)
    if digest(source)!=SOURCE_DB_SHA:raise ValueError("Pinned v03 research SQLite checksum mismatch")
    cross=read(EVIDENCE/"kyushu_strict_independent_code_crosswalk_v04.csv")
    groups=read(EVIDENCE/"kyushu_jma_verified_group_counts_v04.csv")
    review=json.loads((EVIDENCE/"kyushu_jma_crosswalk_review_v04.json").read_text())
    national={r["river_code"]:r for r in read(ROOT/"national-codes-staged/river_codes_national_v07.csv")}
    if (len(cross)!=EXPECTED_RIVERS or review["strict_matched_rivers"]!=EXPECTED_RIVERS
        or review["matched_old_B_recovered_contexts"]!=EXPECTED_NEW_A):
        raise ValueError("Kyushu external evidence aggregate mismatch")
    expected={}
    for r in groups:
        key=(r["watershed_name"],r["river_name"])
        expected.setdefault(key,{})
        if r["category"] in expected[key]:raise ValueError("Duplicated source category")
        expected[key][r["category"]]=int(r["recovered_records"])
    if len(expected)!=EXPECTED_RIVERS or sum(sum(x.values()) for x in expected.values())!=EXPECTED_NEW_A:
        raise ValueError("Source group counts changed")
    source_pairs=set()
    for item in cross:
        key=(item["watershed_name"],item["river_name"])
        if key in source_pairs:raise ValueError("Duplicated independent evidence")
        source_pairs.add(key)
        nat=national.get(item["river_code"])
        if (item["region"]!="kyushu" or item["source_authority"]!="九州地方整備局"
            or item["jma_source_sha256"]!=JMA_SHA or item["mlit_pair_source_sha256"]!=MLIT_SHA
            or not nat or nat["river_code"][:6]!=item["watershed_code"]
            or nat["river_name"]!=item["river_name"] or nat["watershed_name"]!=item["watershed_name"]
            or nat["watershed_code"]!=item["watershed_code"]
            or not item["jma_page"].isdigit()):
            raise ValueError("Individual Kyushu code proof not sufficient: "+repr(key))
        if key not in expected:raise ValueError("No source biology for proved name")
    baseline=read_db(source);baseline.execute("PRAGMA query_only=ON")
    before=metrics(baseline)
    if (before["original"]!=EXPECTED_BASE or before["recovered"]!=EXPECTED_RECOVERED
        or before["approved"]!=EXPECTED_PREVIOUS_A or before["rivers"]!=106):
        raise ValueError("Unexpected v03 source dataset")
    stable_codes=["8707090029","8707090047","8202040001"]
    snapshots={code:direct(baseline,code) for code in stable_codes}
    out=sqlite3.connect(dest)
    try:
        baseline.backup(out)
        baseline.close()
        out.execute("PRAGMA foreign_keys=ON")
        old_regions=dict(out.execute("SELECT region,COUNT(*) FROM approved_individual_river GROUP BY region"))
        promoted=0
        n=0
        for item in cross:
            water,river=item["watershed_name"],item["river_name"]
            matches=out.execute("""
                SELECT r.id,r.match_class,r.river_code,r.source_authority,r.target_scope
                FROM river_context r JOIN watersheds w ON w.id=r.watershed_id
                WHERE w.region='kyushu' AND w.watershed_name=? AND r.river_name=?
            """,(water,river)).fetchall()
            if len(matches)!=1 or tuple(matches[0][1:])!=("B",None,"九州地方整備局","individual_river"):
                raise ValueError("Existing B context inconsistent: "+repr((water,river,matches)))
            ctx=matches[0][0]
            actual=dict(out.execute("""
                SELECT s.group_id,COUNT(*) FROM river_evidence e
                JOIN sources s ON e.source_id=s.id
                WHERE e.river_context_id=? GROUP BY s.group_id
            """,(ctx,)))
            if actual!=expected[(water,river)]:
                raise ValueError("Actual individual-year/name records disagree: "+repr((water,river,actual)))
            cur=out.execute("""
                UPDATE river_context SET river_code=?,watershed_code=?,match_class='A',
                    match_reason=?,code_source_url=?,code_source_page=?
                WHERE id=? AND match_class='B' AND river_code IS NULL
            """,(item["river_code"],item["watershed_code"],item["approval_basis"],
                 item["jma_source_url"],item["jma_page"],ctx))
            if cur.rowcount!=1:raise ValueError("Unexpected context promotion count")
            promoted+=1;n+=sum(actual.values())
        if promoted!=EXPECTED_RIVERS or n!=EXPECTED_NEW_A:raise ValueError("Promotion total mismatch")

        # Original compressed-keys (408036) are recounted from *all* per-river
        # contexts. Mixed A/C remains C rather than falsely A.
        rollup=out.execute("""
            SELECT e.source_id,r.watershed_id,e.label_id,e.survey_year,
                   MAX(r.match_class='A') a,MAX(r.match_class='B') b,
                   MAX(r.match_class='C') c,MAX(r.match_class='D') d,
                   MIN(r.match_class='A') all_a
            FROM river_evidence e JOIN river_context r ON r.id=e.river_context_id
            JOIN watersheds w ON w.id=r.watershed_id WHERE w.region='kyushu'
            GROUP BY e.source_id,r.watershed_id,e.label_id,e.survey_year
        """).fetchall()
        updates=[]
        for sid,wid,lid,year,a,b,c,d,all_a in rollup:
            state="A" if all_a else ("D" if d else ("B" if b else "C"))
            updates.append((state,int(bool(a)),sid,wid,lid,year))
        out.executemany("""
            UPDATE original_keys SET match_class=?,has_any_approved_river=?
            WHERE source_id=? AND watershed_id=? AND label_id=? AND survey_year=?
        """,updates)
        keys=out.execute("""
            SELECT COUNT(*) FROM original_keys k JOIN watersheds w ON w.id=k.watershed_id
            WHERE w.region='kyushu'
        """).fetchone()[0]
        if keys!=len(rollup):raise ValueError("Kyushu key conservation failed")
        out.commit()

        after=metrics(out)
        if (after["original"]!=before["original"] or after["recovered"]!=before["recovered"]
            or after["group_counts"]!=before["group_counts"]
            or after["approved"]!=TOTAL_A or after["rivers"]!=115
            or dict(out.execute("SELECT region,COUNT(*) FROM approved_individual_river WHERE region!='kyushu' GROUP BY region"))!=old_regions):
            # Existing version has only China/Tohoku; compare against them explicitly.
            stable_before={k:v for k,v in old_regions.items() if k!="kyushu"}
            stable_after=dict(out.execute("SELECT region,COUNT(*) FROM approved_individual_river WHERE region!='kyushu' GROUP BY region"))
            if not (stable_before==stable_after and after["approved"]==TOTAL_A and after["rivers"]==115
                    and after["original"]==before["original"] and after["recovered"]==before["recovered"]
                    and after["group_counts"]==before["group_counts"]):
                raise ValueError("Research v04 identity conservation failed")
        if any(direct(out,c)!=snapshots[c] for c in stable_codes):
            raise ValueError("Old Chugoku or Tohoku river regression")
        if out.execute("PRAGMA integrity_check").fetchone()[0]!="ok" or out.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("SQLite integrity failure")
        if out.execute("SELECT COUNT(*) FROM evidence WHERE match_class!='A' AND river_code IS NOT NULL").fetchone()[0]:
            raise ValueError("Unapproved evidence received a river code")
        def river_rows():
            return out.execute("""
                SELECT r.river_code,w.region,w.watershed_name,r.river_name,
                    s.group_id,COUNT(*),COUNT(DISTINCT e.label_id),
                    MIN(e.survey_year),MAX(e.survey_year)
                FROM river_evidence e
                JOIN river_context r ON r.id=e.river_context_id
                JOIN watersheds w ON w.id=r.watershed_id
                JOIN sources s ON s.id=e.source_id
                WHERE r.match_class='A'
                GROUP BY r.river_code,w.region,w.watershed_name,r.river_name,s.group_id
                ORDER BY w.region,w.watershed_name,r.river_name,s.group_id
            """).fetchall()
        out_dir.mkdir(parents=True,exist_ok=True)
        with (out_dir/"confirmed_river_group_counts_v04.csv").open("w",encoding="utf-8",newline="") as f:
            w=csv.writer(f);w.writerow(["river_code","region","watershed","river","group","records","literal_names_not_species","year_min","year_max"]);w.writerows(river_rows())
        report={
            "schema":"research-v04","input_sqlite_sha256":SOURCE_DB_SHA,
            "kyushu_jma_source_sha256":JMA_SHA,"kyushu_mlit_source_sha256":MLIT_SHA,
            "before":before,"after":after,
            "new_kyushu_confirmed_rivers":promoted,"new_kyushu_confirmed_contexts":n,
            "total_approved_rivers":after["rivers"],"total_approved_contexts":after["approved"],
            "unchanged_chugoku_misasa":snapshots["8707090029"],
            "unchanged_tohoku_kitakami":snapshots["8202040001"],
            "kyushu_example_honmyogawa":direct(out,"8909030001"),
            "kyushu_example_ushizugawa":direct(out,"8909040003"),
            "classification_unit":"category x regional watershed x river x survey year x literal name",
            "raw_observations_not_added":True,"w05_noncommercial_gis_not_used":True,
            "prefecture_inference":False,"direct_confluence_inference":False,
            "production_wordpress_changed":False,"production_mysql_changed":False
        }
        (out_dir/"integration_validation_v04.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({k:v for k,v in report.items() if k not in ("before","after")},ensure_ascii=False))
        return report
    finally:
        out.close()
        try:baseline.close()
        except Exception:pass

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True);p.add_argument("--out",required=True);p.add_argument("--report-dir",required=True)
    a=p.parse_args();run(a.source,a.out,a.report_dir)
