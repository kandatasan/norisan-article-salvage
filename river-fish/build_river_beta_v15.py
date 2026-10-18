#!/usr/bin/env python3
"""Create an OFFLINE, source-scoped nationwide river-name search beta.

Data contract:
  35,449 code-name observations (NOT geo-confirmed / complete rivers);
  1,449 independently sourced local-name and basin-name mentions;
  18,814 watershed-year-fish-label survey records (NOT river-specific fish);
  47 prefecture name keys (source coverage != all rivers surveyed).

Pure stdlib; no WP operations, API keys, remote traffic, Google Analytics.
The zipped index.html works from a local file:// directory (script tag data).
"""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import shutil
import urllib.parse
import zipfile

ROOT=Path(__file__).resolve().parent
ASSET_DIR=ROOT/"web-beta"
RIVERS=ROOT/"national-codes-staged/river_codes_national_v07.csv"
SOURCES=[
    ("hiroshima-confirmed","river_registry_hiroshima_v01.csv"),
    ("hiroshima-mentions","river_name_mentions_hiroshima_v02.csv"),
    ("chugoku-basins","chugoku_second_class_watersheds_v10.csv"),
    ("yamaguchi-mentions","yamaguchi_river_municipality_mentions_v10.csv"),
    ("tottori-pdf","tottori-pdf-staged/tottori_river_pdf_mentions_v11.csv"),
    ("ten-pref-mentions","multi_prefecture_source_mentions_v13.csv"),
    ("remaining-pref-mentions","remaining_32pref_source_mentions_v14.csv"),
]
REGIONS=["hokkaido","tohoku","kanto","hokuriku","chubu","kinki","chugoku","shikoku","kyushu"]
REGION_NAMES={"hokkaido":"北海道","tohoku":"東北","kanto":"関東","hokuriku":"北陸",
              "chubu":"中部","kinki":"近畿","chugoku":"中国","shikoku":"四国","kyushu":"九州"}
SOURCE_COUNTS=[66,98,72,81,377,316,439]
SOURCE_DATA_CONTRACT="source_name_only_not_code_or_species"
FISH_DATA_CONTRACT="regional_watershed_year_only_not_tributary"
OFFICIAL_CODES_URL="https://nlftp.mlit.go.jp/ksj/gml/codelist/RiverCodeCd.html"

def records(relative_path):
    with (ROOT/relative_path).open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def verified_url(raw):
    u=urllib.parse.urlsplit(str(raw or ""))
    if u.scheme!="https" or not u.hostname or not u.hostname.endswith(".jp"):
        raise ValueError("Source URL must be an HTTPS official Japanese publisher: "+str(raw))
    return raw

def mention(pref,name,kind,watershed,area,url,source_id,scope,date=""):
    if (not pref or not name or not source_id or kind not in ("river","watershed","planning_region")):
        raise ValueError("Invalid source evidence")
    # Names are presented as SOURCE LABELS ONLY and are never auto-joined to national codes.
    verified_url(url)
    return [pref,name,kind,watershed or "",area or "",url,source_id,scope,date or ""]

def local_mentions():
    dst=[]
    for (origin,src),expected in zip(SOURCES,SOURCE_COUNTS):
        rows=records(src)
        if len(rows)!=expected:raise ValueError(f"Unexpected {origin} count {len(rows)}")
        for r in rows:
            if origin=="hiroshima-confirmed":
                if r["record_status"]!="source_name_confirmed":raise ValueError("Hiroshima source status changed")
                entry=mention(r["prefecture"],r["river_name"],"river",r["watershed"],
                              r["municipality_example"],r["source_url"],r["river_id"],"広島県・2021年河川資料（名称）",r["source_document_year"])
            elif origin=="hiroshima-mentions":
                if r["watershed_review_status"]!="unverified" or r["watershed_name"]:
                    raise ValueError("Unreviewed Hiroshima watershed must be blank")
                entry=mention(r["prefecture"],r["river_name"],"river","",r["municipality_listing"],
                              r["source_url"],r["mention_id"],"広島県・市町村の河川名掲載（未照合）",r["source_page_date"])
            elif origin=="chugoku-basins":
                if r["river_code"] or r["site_status"]!="research_only":raise ValueError("Basin code wrongly approved")
                entry=mention(r["prefecture"],r["watershed_label_as_written"],"watershed","",
                              "",r["source_page_url"],r["record_id"],"中国地方・水系資料掲載",r["source_page_updated_date_if_verified"])
            elif origin=="yamaguchi-mentions":
                if r["official_river_code"] or r["code_identity_status"]!="unlinked_name_and_watershed":
                    raise ValueError("Unreviewed Yamaguchi river code assigned")
                entry=mention(r["prefecture"],r["river_name_as_written"],"river",
                              r["watershed_label_as_written"],r["municipality_in_source"],
                              r["source_url"],r["evidence_id"],"山口県・洪水資料の河川×関係市町",r["page_last_updated"])
            elif origin=="tottori-pdf":
                if (r["ten_digit_code_status"]!="unlinked" or
                    r["text_extraction_review_status"]!="pdf_text_machine_extracted_requires_visual_review"):
                    raise ValueError("Tottori PDF is not published grade")
                entry=mention(r["prefecture"],r["river_name_as_pdf_text"],"river",
                              r["watershed_printed_on_same_line"],r["district_as_published"],
                              r["source_pdf_url"],r["document_mention_id"],
                              "鳥取県・2023年河川一覧PDF（機械抽出・目視未確認）",r["source_as_of"])
            elif origin=="ten-pref-mentions":
                if r["national_river_code_status"]!="not_linked" or r["website_status"]!="research_only":
                    raise ValueError("v1.3 source is not a name-only candidate")
                entry=mention(r["prefecture"],r["literal_name"],r["evidence_kind"],
                              r["watershed_explicit_in_source"],r["source_subarea"],
                              r["source_url"],r["evidence_id"],
                              "県公式資料・"+r["source_scope"],r["source_as_of_if_stated"])
            else:
                if r["individual_river_code"] or r["national_code_geography_status"]!="unlinked":
                    raise ValueError("v1.4 geography cannot be auto assigned")
                entry=mention(r["prefecture"],r["name_as_written"],r["label_type"],
                              r["watershed_explicit_in_source"],r["source_context"],
                              r["source_page_url"],r["mention_id"],
                              "県公式資料・"+r["source_document_scope"],r["page_date_if_available"])
            dst.append(entry)
    if len(dst)!=1449 or len({r[6] for r in dst})!=len(dst):
        raise ValueError("Unexpected or duplicate source identity")
    return dst

def official_river_codes():
    data=records("national-codes-staged/river_codes_national_v07.csv")
    if len(data)!=35449:raise ValueError("Official code manifest size changed")
    seen=set(); result=[]
    for r in data:
        code=r["river_code"]
        if (code in seen or len(code)!=10 or not code.isdigit()
            or r["identity_status"]!="coded_name_only_not_geographically_verified"
            or r["site_status"]!="research_only"
            or r["watershed_code"]!=code[:6]):
            raise ValueError("Unexpected/inaccurately localized code row")
        seen.add(code)
        result.append([code,r["river_name"],r["watershed_name"],r["watershed_code"]])
    return result

def census_fish():
    result=[]
    for rid in REGIONS:
        path=ROOT/"nationwide-staged"/rid
        manifest=json.loads((path/"manifest.json").read_text(encoding="utf-8"))
        if manifest["region"]!=rid or manifest["prefecture_mapping"]!="not_inferred":
            raise ValueError("Unsupported national fish provenance")
        with (path/"watershed_year_fish.csv").open(encoding="utf-8-sig",newline="") as f:
            rows=list(csv.DictReader(f))
        if len(rows)!=manifest["aggregated_records"]:
            raise ValueError("Fish source record count changed")
        for r in rows:
            if r["region"]!=rid or r["source_sha256"]!=manifest["source_sha256"]:
                raise ValueError("Unverified fish survey")
            verified_url(r["source_url"])
            result.append([rid,r["watershed"],r["survey_year"],r["recorded_name"],r["source_url"]])
    if len(result)!=18814:raise ValueError("Unexpected 9-region fish record total")
    return result

def prefectures():
    data=records("japan_prefectures_v06.csv")
    if len(data)!=47 or len({r["prefecture_name"] for r in data})!=47:
        raise ValueError("47-prefecture names not ready")
    return [r["prefecture_name"] for r in data]

def create_payload():
    codes=official_river_codes()
    src=local_mentions()
    fish=census_fish()
    pf=prefectures()
    if set(x[0] for x in src)!=set(pf):
        raise ValueError("Missing official name source in some prefecture")
    return {
      "meta":{
         "edition":"beta-0.1","built_from":"tsurikue source inventory v1.4",
         "rivers":len(codes),"sourceMentions":len(src),"fishCensus":len(fish),
         "prefectures":47,
         "censusScope":FISH_DATA_CONTRACT,"localScope":SOURCE_DATA_CONTRACT,
         "officialRiverSource":OFFICIAL_CODES_URL,
         "websitePublished":False,
         "notice":"全国河川コードは所在県を確定しません。県別資料は一部掲載のみ。魚類記録は水系・年度単位で、支流や釣り場の魚の証拠ではありません。"
      },
      "prefectures":pf,"regionLabels":REGION_NAMES,
      "riverCodes":codes,"localEvidence":src,"fishCensus":fish
    }

def build(output,zip_name=None):
    output=Path(output)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Refusing to overwrite existing beta folder")
    payload=create_payload()
    output.mkdir(parents=True,exist_ok=True)
    for filename in ("index.html","style.css","search-core.js","app.js"):
        shutil.copy2(ASSET_DIR/filename,output/filename)
    # data.js instead of fetch JSON: opens OFFLINE even via file:// on iOS/PC.
    (output/"data.js").write_text(
        "window.TSURIRIVER_BETA_DATA = "+json.dumps(payload,ensure_ascii=False,separators=(",",":")).replace("</","<\\/")+";\n",
        encoding="utf-8")
    manifest={
       "status":"offline_preview_only_not_WordPress_published",
       "file_entrypoint":"index.html","requires_network":False,
       "data_contracts":{"river_codes":"official_code_name_not_verified_location",
                        "source_mentions":SOURCE_DATA_CONTRACT,
                        "fish":FISH_DATA_CONTRACT},
       "counts":{k:payload["meta"][k] for k in ("rivers","sourceMentions","fishCensus","prefectures")},
       "zip_recommended":"extract the zip then open index.html",
       "forbidden":["autolink river to prefecture","autolink fish survey to river","site publication"]
    }
    (output/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if zip_name:
        zip_path=Path(zip_name)
        zip_path.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
            for p in sorted(output.iterdir()):
                z.write(p,arcname="tsurikue-river-beta/"+p.name)
    return manifest

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True)
    p.add_argument("--zip",default="")
    args=p.parse_args()
    print(json.dumps(build(args.out,args.zip or None),ensure_ascii=False,indent=2))
