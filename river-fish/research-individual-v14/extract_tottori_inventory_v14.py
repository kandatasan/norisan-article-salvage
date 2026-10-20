#!/usr/bin/env python3
"""Audit the official Tottori 2023 named river inventory in three regional PDFs.

Source scope: prefectural administrative river list, NOT biological sightings.
Do not infer watershed from page continuation, or a legal 10-digit river code
from the PDF's local row numbering. No commercial-site publication is granted.
"""
from __future__ import annotations
import csv, hashlib, io, json, re, subprocess, tempfile, unicodedata, urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZipFile
BASE=Path(__file__).resolve().parents[1]
HERE=Path(__file__).resolve().parent
OUT=HERE/"outputs"
SOURCE="https://www.pref.tottori.lg.jp/307111.htm"
COPYRIGHT="https://www.pref.tottori.lg.jp/9314.htm"
PDFS={
 "east":"https://www.pref.tottori.lg.jp/secure/1313532/toubu.pdf",
 "central":"https://www.pref.tottori.lg.jp/secure/1313532/230401chubu.pdf",
 "west":"https://www.pref.tottori.lg.jp/secure/1313532/230401seibu.pdf",
}
# Source page is dated 2023-04-01, not the run date.
YEAR="2023-04-01"
GROUPS={"１":"first_class","1":"first_class","２":"second_class","2":"second_class"}
RIVERNAME=re.compile(r"^[\u3400-\u9fff々〆ヵヶーぁ-んァ-ヴ⻄⻑⼾]+(?:川|河|水路|放水路|運河)$")
ROW=re.compile(r"(?<![0-9])([0-9]{1,3})\s+([^\s0-9,()（）]{2,30})\s+([0-9][0-9,]{0,9})(?=\s|$)")
WATER=re.compile(r"([\u3400-\u9fff々〆ヵヶーぁ-んァ-ヴ⻄⻑⼾]{1,25}水系)")

def text_from_pdf(original):
    with tempfile.TemporaryDirectory() as temp:
        doc=Path(temp)/"official.pdf";doc.write_bytes(original)
        p=subprocess.run(["pdftotext","-layout","-enc","UTF-8",str(doc),"-"],
             check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        return p.stdout.decode("utf-8")

def download(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (official river inventory research)"})
    with urllib.request.urlopen(req,timeout=55) as r:
        if r.status!=200:raise ValueError("Original HTTP failure "+str(r.status))
        data=r.read(2_000_000)
    if not data.startswith(b"%PDF") or len(data)<15000:
        raise ValueError("Official PDF is missing or unexpectedly small")
    return data

def normal(s):
    return unicodedata.normalize("NFKC",s).replace("⻄","西").replace("⻑","長").replace("⼾","戸").replace("﨑","崎").strip()

def extract(text,url,region,sha):
    if "河川一覧" not in text or "令和5年4月1日時点" not in normal(text.replace(" ","")):
        raise ValueError("Original title/as-of date not corroborated: "+region)
    category=None
    entries=[]
    counters=Counter()
    watermark=None
    for num,line in enumerate(text.splitlines(),1):
        short=normal(line)
        if re.search(r"[○◯]\s*[1１]\s*級河川",short):category="first_class";watermark=None;continue
        if re.search(r"[○◯]\s*[2２]\s*級河川",short):category="second_class";watermark=None;continue
        if "準用河川" in short and ("○" in short or "◯" in short):category="quasi_public";watermark=None;continue
        if category is None:continue
        # Some table cells print a watershed, and others leave it blank.
        # Only SAME-ROW watershed assertions go into the research table.
        system=WATER.search(short)
        water=system.group(1) if system else None
        for match in ROW.finditer(short):
            serial,name,length=match.groups()
            name=normal(name)
            if not RIVERNAME.fullmatch(name):continue
            if len(name)>24 or int(length.replace(",",""))>500_000:continue
            entries.append({"prefecture":"鳥取県","source_region":region,
                "management_category":category,
                "source_local_row_number":int(serial),
                "river_name_as_printed":name,
                "watershed_same_row_only":water if water else "",
                "river_length_m_as_printed":int(length.replace(",","")),
                "source_file_sha256":sha,
                "original_pdf_url":url,
                "source_as_of_date":YEAR,
                "license_flag":"RESEARCH_ONLY_CITY_OR_PREFECTURE_PERMISSION_REQUIRED",
                "biospecies_from_this_document":0,
                "ten_digit_river_code":""})
            counters[category]+=1
    if not entries:raise ValueError("No actual named-river rows parsed: "+region)
    uniq={(e["management_category"],e["source_local_row_number"],e["river_name_as_printed"]) for e in entries}
    if len(uniq)!=len(entries):
        raise ValueError("Repeated same-number river inventory row")
    return entries,dict(counters)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    with ZipFile(BASE/"research-individual-v12"/"outputs"/"river_atlas_static_preview_v12.zip") as z:
        atlas=json.loads(z.read("atlas.json"))
    assert atlas["research_display_name_groups"]==511
    allrows=[];audits=[]
    for region,url in PDFS.items():
        data=download(url)
        sha=hashlib.sha256(data).hexdigest()
        txt=text_from_pdf(data)
        rows,count=extract(txt,url,region,sha)
        allrows.extend(rows)
        audits.append({"region":region,"source_url":url,"sha256":sha,"pdf_bytes":len(data),
                       "parsed_river_list_rows":len(rows),"by_administrative_class":count,
                       "same_row_verified_watershed_pairs":sum(bool(x["watershed_same_row_only"]) for x in rows),
                       "no_original_pdf_republished":True})
        print(json.dumps({"region":region,"rows":len(rows),"sha256":sha},ensure_ascii=False))
    if len(allrows)<180:raise ValueError("Official regional inventories appear incomplete; review extraction")
    # Do not assert the PDF inventory number is a nationally unique or distinct
    # physical river count. The same river name may appear in multiple classes.
    names={e["river_name_as_printed"] for e in allrows}
    combined={(e["water"],e["name"]) for e in atlas["entries"]}
    confirmed_pairs={(e["watershed_same_row_only"].removesuffix("水系"),e["river_name_as_printed"])
                 for e in allrows if e["watershed_same_row_only"]}
    overlaps=sorted(combined & confirmed_pairs)
    unmatched=sorted(confirmed_pairs-combined)
    fieldnames=list(allrows[0])
    with (OUT/"tottori_official_river_source_rows_research_v14.csv").open("w",encoding="utf-8",newline="") as fp:
        wr=csv.DictWriter(fp,fieldnames=fieldnames);wr.writeheader();wr.writerows(allrows)
    qa={"project":"national river atlas","research_version":"v14","source_prefecture":"鳥取県",
        "official_source_page":SOURCE,"copyright_page":COPYRIGHT,"as_of":YEAR,
        "source_region_pdf_sha256_audits":audits,
        "source_rows_not_distinct_river_count":len(allrows),
        "unique_literal_river_name_spellings":len(names),
        "same_row_watershed_links":len(confirmed_pairs),
        "confirmed_same_row_links_missing_from_baseline_511":len(unmatched),
        "confirmed_same_row_links_already_in_baseline_511":len(overlaps),
        "baseline_511_undisturbed":True,
        "all_prefecture_level_sources_originals_verified":len(audits)==3,
        "no_biological_species_claims":True,
        "pdf_row_numbers_not_10_digit_river_codes":True,
        "river_name_prefix_without_watershed_not_assigned_by_inference":True,
        "reproduction_and_commercial_site_use_prohibited_until_review":True,
        "no_wordpress_or_live_api_mutation":True}
    (OUT/"tottori_river_inventory_provenance_qa_v14.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(qa,ensure_ascii=False))

if __name__=="__main__":
    main()
