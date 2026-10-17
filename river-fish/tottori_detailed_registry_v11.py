#!/usr/bin/env python3
"""Offline SQLite search for 2023 Tottori detailed river-source mentions.

Extends v1.0 five-prefecture source DB WITHOUT assuming a Tottori-specific
10-digit national river identity, geographic centerline or fish occurrences.
A 2023 printed serial number is local to the PDF source and must never be
treated as MLIT 10-digit RiverCodeCd.
"""
import argparse
import csv
import json
from pathlib import Path
import sqlite3
import unicodedata
from chugoku_registry_v10 import build as build_chugoku
from import_tottori_river_pdfs_v11 import CSV_HEAD,PDFS,SOURCE_DATE,NAME_LABELS

ROOT=Path(__file__).resolve().parent
DATA="tottori-pdf-staged/tottori_river_pdf_mentions_v11.csv"
MANIFEST="tottori-pdf-staged/tottori_river_pdf_manifest_v11.json"
EXPECTED_COUNTS={"east":141,"central":114,"west":122}
CLASSES={"一級河川","二級河川","準用河川"}

def load(root=ROOT):
    root=Path(root)
    m=json.loads((root/MANIFEST).read_text(encoding="utf-8"))
    with (root/DATA).open(encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=CSV_HEAD:raise ValueError("Tottori river data fields changed")
        rows=list(reader)
    if (m["source_as_of"]!=SOURCE_DATE or
        m["publication_status"]!="research_only_pending_visual_review"
        or not m["all_codes_unlinked"] or not m["no_geolocation_or_species_inferred"]
        or m["pdf_text_source_mention_rows"]!=377 or len(rows)!=377):
        raise ValueError("Tottori PDF source inventory changed; manually reverify")
    ids=set()
    counters={key:0 for key in PDFS}
    for r in rows:
        entry_id=r["document_mention_id"]
        if entry_id in ids:raise ValueError("Duplicate official PDF row key")
        ids.add(entry_id)
        region=next((k for k in PDFS if entry_id.startswith("TP-"+k+"-")),None)
        if (not region or r["prefecture"]!="鳥取県"
            or r["district_as_published"]!=NAME_LABELS[region]
            or r["river_class_page_heading"] not in CLASSES
            or not r["river_name_as_pdf_text"]
            or r["source_pdf_url"]!=PDFS[region]
            or r["source_as_of"]!=SOURCE_DATE
            or not r["source_pdf_page_1based"].isdigit()
            or r["text_extraction_review_status"]!="pdf_text_machine_extracted_requires_visual_review"
            or r["ten_digit_code_status"]!="unlinked"
            or r["specific_river_ecology_status"]!="not_examined"
            or r["website_publication_status"]!="research_only"):
            raise ValueError("Unreviewed river identification or fish claim in PDF staging")
        counters[region]+=1
    if counters!=EXPECTED_COUNTS:raise ValueError("Unexpected 2023 document count per district")
    return rows,m

def build(db,root=ROOT):
    db=Path(db)
    if db.exists():raise FileExistsError("No overwriting reviewed inventory")
    older=build_chugoku(db,root)
    data,manifest=load(root)
    conn=sqlite3.connect(db)
    try:
        conn.executescript("""
           CREATE TABLE tottori_pdf_river_mentions (
             document_mention_id TEXT PRIMARY KEY,
             prefecture TEXT NOT NULL,
             district TEXT NOT NULL,
             river_name TEXT NOT NULL,
             pdf_local_serial TEXT NOT NULL,
             river_class_as_page_heading TEXT NOT NULL,
             watershed_printed_same_line TEXT,
             source_pdf_url TEXT NOT NULL,
             source_pdf_page TEXT NOT NULL,
             source_as_of TEXT NOT NULL,
             review_status TEXT NOT NULL,
             ten_digit_code_status TEXT NOT NULL,
             river_ecology_status TEXT NOT NULL,
             website_status TEXT NOT NULL
           );
           CREATE INDEX idx_tottori_pdf_name ON tottori_pdf_river_mentions(river_name);
           CREATE INDEX idx_tottori_pdf_class ON tottori_pdf_river_mentions(river_class_as_page_heading);
           CREATE INDEX idx_tottori_pdf_district ON tottori_pdf_river_mentions(district);
        """)
        conn.executemany("INSERT INTO tottori_pdf_river_mentions VALUES ("+",".join("?" for _ in CSV_HEAD)+")",[
            (r["document_mention_id"],r["prefecture"],r["district_as_published"],
             r["river_name_as_pdf_text"],r["printed_local_serial"],
             r["river_class_page_heading"],r["watershed_printed_on_same_line"] or None,
             r["source_pdf_url"],r["source_pdf_page_1based"],r["source_as_of"],
             r["text_extraction_review_status"],r["ten_digit_code_status"],
             r["specific_river_ecology_status"],r["website_publication_status"])
            for r in data
        ])
        conn.commit()
        if conn.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
            raise ValueError("SQLite integrity failed")
        return {
          "chugoku_watershed_source_mentions_previous":older["chugoku_prefecture_watershed_mentions"],
          "yamaguchi_municipality_source_mentions_previous":older["new_yamaguchi_river_municipality_mentions"],
          "tottori_pdf_mention_rows":conn.execute("SELECT COUNT(*) FROM tottori_pdf_river_mentions").fetchone()[0],
          "source_distinct_river_labels":manifest["distinct_printed_name_labels"],
          "tottori_river_code_approvals":0,
          "tottori_direct_fish_occurrences":0,
          "website_published":False
        }
    finally:conn.close()

def search(db,name="",river_class="",district="",limit=40,offset=0):
    if not 1<=limit<=200 or offset<0:raise ValueError("Invalid pagination")
    if river_class and river_class not in CLASSES:raise ValueError("Invalid river class")
    conn=sqlite3.connect(str(db));conn.row_factory=sqlite3.Row
    try:
        normalize=lambda x: unicodedata.normalize("NFKC",str(x or "")).casefold()
        records=[dict(x) for x in conn.execute("SELECT * FROM tottori_pdf_river_mentions ORDER BY document_mention_id")]
        matches=[r for r in records
                 if (not name or normalize(name) in normalize(r["river_name"]))
                 and (not river_class or r["river_class_as_page_heading"]==river_class)
                 and (not district or normalize(district) in normalize(r["district"]))]
        for row in matches:
            # Distinguish literal source text from interpreted modern identity.
            row["national_river_code"]=None
            row["prefectural_fish_occurrence"]=None
            row["specific_river_fish_occurrence"]=None
            row["watershed_inferred_from_other_rows"]=False
        return {
          "source_mention_count":len(matches),"records":matches[offset:offset+limit],
          "offset":offset,"limit":limit,
          "source_as_of":SOURCE_DATE,
          "notice":"2023年4月1日時点の鳥取県一覧をPDFテキストから抽出した確認候補。印刷番号は全国10桁河川コードではありません。河川名や水系名の現在性は別途確認し、魚の生息は推測しません。"
        }
    finally:conn.close()

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--db",default="river-fish/tottori_detailed_v11.sqlite")
    p.add_argument("--build",action="store_true")
    p.add_argument("--name",default="")
    p.add_argument("--river-class",default="")
    p.add_argument("--district",default="")
    p.add_argument("--limit",type=int,default=40)
    p.add_argument("--offset",type=int,default=0)
    a=p.parse_args()
    result=build(a.db) if a.build else search(a.db,a.name,a.river_class,a.district,a.limit,a.offset)
    print(json.dumps(result,ensure_ascii=False,indent=2))
