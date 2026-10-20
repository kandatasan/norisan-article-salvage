#!/usr/bin/env python3
"""Build a LOCAL/RESEARCH-ONLY 511-group river atlas from SHA-audited v09-v11.
No WordPress/API/database write, no external network dependency, no new claims
of live captures, precise river identity, benthic invertebrates, or residence.
"""
import csv
import hashlib
import io
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo

ROOT=Path(__file__).resolve().parents[1]
HERE=Path(__file__).resolve().parent
OUT=HERE/"outputs"
CATS=("fish","benthic_animals","birds","plants")
REGIONS={"hokkaido":"北海道","tohoku":"東北","kanto":"関東","hokuriku":"北陸","chubu":"中部","kinki":"近畿","chugoku":"中国","shikoku":"四国","kyushu":"九州"}
UNKNOWN="所在県未確定（地方別資料）"
EDNA_GROUPS={"fish_edna":"fish","bird_edna_not_visual_observation":"birds",
             "insect_edna_not_proven_benthic":"other_edna",
             "other_invertebrate_edna_not_proven_benthic":"other_edna"}
BASE=ROOT/"research-individual-v09"/"outputs"
V10=ROOT/"research-individual-v10"/"outputs"
V11=ROOT/"research-individual-v11"/"outputs"
NAV=ROOT/"research-individual-v07"/"outputs"/"river_atlas_navigation_v07.json"

def load(p):
    return json.loads(p.read_text(encoding="utf-8"))

def encode(d):
    return (json.dumps(d,ensure_ascii=False,separators=(",",":"),sort_keys=True)+"\n").encode("utf-8")

def add(z,path,data):
    assert not path.startswith("/") and ".." not in path.split("/")
    assert re.fullmatch(r"[a-z0-9_./-]+",path), path
    item=ZipInfo(path,date_time=(1980,1,1,0,0,0))
    item.external_attr=0o644<<16
    item.compress_type=ZIP_DEFLATED
    z.writestr(item,data,compress_type=ZIP_DEFLATED,compresslevel=8)

def main():
    OUT.mkdir(exist_ok=True)
    manifest=load(BASE/"manifest_v09.json")
    nav=load(NAV)
    v10=load(V10/"research_biological_method_layers_v10.json")
    held=load(V10/"held_name_only_manifest_v10.json")
    groups=load(V11/"kanagawa_2023_2024_edna_river_groups_v11.json")
    qa=load(V11/"kanagawa_2023_2024_edna_provenance_qa_v11.json")
    assert len(manifest["rivers"])==428
    assert len(v10["entries"])==492
    assert len(held["entries"])==40
    assert len(groups)==31
    assert qa["new_candidate_name_groups_not_in_v10_492"]==19
    assert len(nav["prefectures"])==47
    assert len(nav["prefecture_watershed_entries"])==80
    old_by_id={r["identity_key"]:r for r in manifest["rivers"]}
    held_by_id={r["identity_key"]:r for r in held["entries"]}
    entries=[]
    for e in v10["entries"]:
        key=e["identity_key"]
        kind=e["category_method"]
        if kind=="historical_national_river_survey":
            assert key in old_by_id
            m=old_by_id[key]
            old={cat:m["categories"][cat]["file"] for cat in CATS}
        elif kind=="historical_survey_river_name_multiple_code_candidates":
            assert key in held_by_id
            old={cat:"held/"+key+"/"+cat+".json" for cat in CATS}
        else:
            assert kind=="prefectural_environmental_DNA_only"
            old={}
        entries.append({"id":key,"water":e["watershed_name"],"name":e["river_name"],
                        "region":e["source_region"],"kind":kind,
                        "old":old,"edna":None,"river_code":e.get("river_code_optional"),
                        "is_a_verified_individual_physical_river":False})
    for g in groups:
        if not g["not_in_v10_display_groups"]:
            continue
        assert not g["spelling_variant_identity_hold"]
        key="edna11_"+hashlib.sha256((g["watershed_name"]+"\0"+g["river_name"]).encode("utf-8")).hexdigest()[:24]
        entries.append({"id":key,"water":g["watershed_name"],"name":g["river_name"],
                        "region":"kanto","kind":"prefectural_environmental_DNA_only",
                        "old":{},"edna":None,"river_code":None,
                        "is_a_verified_individual_physical_river":False})
    assert len(entries)==511 and len({e["id"] for e in entries})==511
    index={e["id"]:e for e in entries}
    pairs=defaultdict(list)
    for e in entries:pairs[(e["water"],e["name"])].append(e)
    linked=defaultdict(set)
    # Existing regional sources have documented prefecture+watershed ENTRY links,
    # not necessarily proof that an entire named river lies in that prefecture.
    for link in nav["prefecture_river_links"]:
        key=link["identity_key"]
        if key not in index:continue
        e=index[key]
        if e["water"] != link["watershed"] or e["name"] != link["river_name"]:
            raise AssertionError("Original prefectural navigation shifted")
        linked[key].add((link["prefecture"],e["water"]))
    # Every source-named group remains reachable if its prefectural river location
    # cannot be documented. An ambiguity is never silently assigned to a prefecture.
    for e in entries:
        if e["kind"]=="prefectural_environmental_DNA_only":
            linked[e["id"]].add(("神奈川県",e["water"]))
        if not linked[e["id"]]:
            linked[e["id"]].add((UNKNOWN,REGIONS[e["region"]]+"地方資料："+e["water"]))

    # eDNA: exactly one matching river-name group, never propagate across
    # ambiguous same-named river identities. Hold uncertain attachments.
    def target(water,name):
        name="早渕川" if (water,name)==("鶴見川","早淵川") else name
        candidates=pairs.get((water,name),[])
        selected=[e for e in candidates if e["kind"]=="prefectural_environmental_DNA_only"]
        if len(selected)==1:return selected[0]
        # v10 already vetted two historic eDNA overlays in the Kanto region.
        old=[e for e in candidates if e["region"]=="kanto" and e["kind"]=="historical_national_river_survey"]
        if len(selected)==0 and len(old)==1:return old[0]
        return None

    edna=defaultdict(dict)
    held_rows=[]
    source_rows_2023=0
    unique_keys_23=set()
    with (V11/"kanagawa_2023_2024_edna_evidence_v11.csv").open(encoding="utf-8",newline="") as fp:
        for row in csv.DictReader(fp):
            source_rows_2023+=1
            method=row["biological_group"]
            assert method in EDNA_GROUPS and row["survey_year"] in ("2023","2024")
            assert row["survey_method"]=="environmental_DNA_positive_sequence_reads_not_capture"
            assert row["identification_confidence_verbatim"] in ("高","中","not_reported")
            w,n=row["watershed_name"],row["river_name"]
            e=target(w,n)
            if e is None:
                held_rows.append({"year":row["survey_year"],"water":w,"river":n,"group":method})
                continue
            group=EDNA_GROUPS[method]
            display_key=(row["survey_year"],method,row["verbatim_source_taxon_label"])
            unique_keys_23.add((w,n)+display_key)
            pack=edna[e["id"]]
            if display_key not in pack:
                pack[display_key]={"year":int(row["survey_year"]),"name":row["verbatim_source_taxon_label"],
                                   "method":"eDNA","group":group,"source_group":method,
                                   "confidence":row["identification_confidence_verbatim"],
                                   "sources":[]}
            item=pack[display_key]
            if row["source_url"] not in item["sources"]:
                item["sources"].append(row["source_url"])
    assert source_rows_2023==3675
    assert len(unique_keys_23)==3570, len(unique_keys_23)
    # v10 2025 source kept separate by YEAR, never added as specimen observation.
    source_rows_2025=0
    with (V10/"kanagawa_2025_tributary_fish_edna_candidate_labels_v10.csv").open(encoding="utf-8",newline="") as fp:
        for row in csv.DictReader(fp):
            source_rows_2025+=1
            assert row["survey_year"]=="2025" and row["category"]=="fish"
            assert row["survey_method"]=="environmental_DNA_positive_sequence_reads"
            w,n=row["watershed_name"],row["river_name"]
            e=target(w,n)
            if e is None:
                held_rows.append({"year":2025,"water":w,"river":n,"group":"fish_edna"})
                continue
            display_key=("2025","fish_edna",row["verbatim_manual_taxon_label"])
            pack=edna[e["id"]]
            if display_key not in pack:
                pack[display_key]={"year":2025,"name":row["verbatim_manual_taxon_label"],
                                   "method":"eDNA","group":"fish","source_group":"fish_edna",
                                   "confidence":row["source_taxon_confidence"],"sources":[]}
            if row["source_url"] not in pack[display_key]["sources"]:
                pack[display_key]["sources"].append(row["source_url"])
    assert source_rows_2025==265,source_rows_2025

    # Rare unresolvable joins MUST remain an explicit QA hold, never fabricated.
    if held_rows:
        raise AssertionError("eDNA identity needs manual hold review: "+str(Counter((r["water"],r["river"]) for r in held_rows).most_common(12)))

    for e in entries:
        if e["id"] in edna:
            e["edna"]="edna/"+e["id"]+".json"
    link_rows=[{"prefecture":p,"water":w,"river_id":id}
               for id,targets in linked.items() for p,w in sorted(targets)]
    link_rows.sort(key=lambda a:(a["prefecture"],a["water"],index[a["river_id"]]["name"],a["river_id"]))
    index_json={
        "title":"日本の河川大図鑑（研究用）",
        "strictly_source_named_river_groups_not_geographically_unique_rivers":True,
        "original_historical_groups":428,"old_identity_uncertain_groups":40,
        "kanagawa_2025_new_groups":24,"kanagawa_2023_24_new_groups":19,
        "research_display_name_groups":511,
        "prefectures":[p["prefecture"] for p in nav["prefectures"]],
        "unknown_prefecture_bucket":UNKNOWN,
        "entries":entries,"links":link_rows,
        "method_note":"過去の調査=当時の資料記載名。環境DNA=水からの検出で、魚の捕獲・鳥の目視・底生動物の採集とは異なる。",
        "method_counts_separate":{"historical_contexts":651435,"kanagawa_2023_2024_edna_source_rows":3675,
                                 "kanagawa_2023_2024_edna_year_river_taxon_groups":3570,
                                 "kanagawa_2025_edna_label_groups":265},
        "new_biology_records_not_direct_specimen_confirmation":True,
        "location_sensitive_data_excluded":True}
    archive=OUT/"river_atlas_static_preview_v12.zip"
    if archive.exists():archive.unlink()
    expected={r["categories"][cat]["file"] for r in manifest["rivers"] for cat in CATS}
    assert len(expected)==1712
    old_paths=set();held_paths=set();edna_paths=set()
    with ZipFile(archive,"w",compression=ZIP_DEFLATED,compresslevel=8) as result:
        add(result,"index.html",(HERE/"viewer_v12.html").read_bytes())
        add(result,"atlas.json",encode(index_json))
        preview=("日本の河川大図鑑 研究用 v0.12\n"
                 "ZIPを解凍し、そのフォルダで python -m http.server 8000 を実行。\n"
                 "http://localhost:8000 を開く。file:// での fetch は動作しない場合があります。\n"
                 "サイト本番には反映していません。511は河川名資料グループで河川実数ではありません。\n").encode("utf-8")
        add(result,"readme_preview.txt",preview)
        with ZipFile(BASE/"river_atlas_static_preview_v09.zip") as previous:
            for name in previous.namelist():
                if name not in expected:continue
                old_paths.add(name)
                row=previous.read(name)
                doc=json.loads(row)
                assert doc["schema"]=="river-category-historical-v09"
                add(result,name,row)
        with ZipFile(V10/"held_river_name_biology_v10.zip") as z:
            for name in z.namelist():
                assert re.fullmatch(r"held_[0-9a-f]{24}/(fish|benthic_animals|birds|plants)\.json",name)
                path="held/"+name
                doc=json.loads(z.read(name))
                assert doc["physical_river_or_segment_identification"]=="UNRESOLVED"
                held_paths.add(path)
                add(result,path,z.read(name))
        for e in entries:
            if not e["edna"]:continue
            allrows=list(edna[e["id"]].values())
            doc={"id":e["id"],"name":e["name"],"water":e["water"],
                 "records":sorted(allrows,key=lambda t:(t["group"],t["year"],t["name"],t["source_group"])),
                 "not_capture_or_visual_survey":True,
                 "other_edna_is_not_confirmed_benthic_animals":True}
            add(result,e["edna"],encode(doc));edna_paths.add(e["edna"])
    assert old_paths==expected
    assert len(held_paths)==160
    with ZipFile(archive) as z:
        assert len(z.namelist())==3+1712+160+len(edna_paths)
        assert z.testzip() is None
        saved=load_index=json.loads(z.read("atlas.json"))
        assert len(saved["entries"])==511
        assert len({l["river_id"] for l in saved["links"]})==511
        assert not any("latitude" in n or "longitude" in n for n in saved)
    report={
        "version":"v12", "source_scope":"research_only_no_production_change",
        "archive":archive.name,"zip_bytes":archive.stat().st_size,
        "archive_sha256":hashlib.sha256(archive.read_bytes()).hexdigest(),
        "unique_research_display_name_groups":len(entries),
        "original_v09_historical_categories":len(old_paths),
        "v10_held_unresolved_categories":len(held_paths),
        "eDNA_river_json_packs":len(edna_paths),
        "source_prefecture_options":47,
        "source_prefecture_water_system_pairs_v07":len(nav["prefecture_watershed_entries"]),
        "navigable_display_name_groups":len({l["river_id"] for l in link_rows}),
        "entries_without_verified_prefecture_count":sum(all(x[0]==UNKNOWN for x in linked[e["id"]]) for e in entries),
        "eDNA_unique_2023_2024":len(unique_keys_23),
        "eDNA_source_rows_2023_2024":source_rows_2023,
        "eDNA_2025":source_rows_2025,
        "all_eDNA_rows_successfully_attached":not held_rows,
        "held_2023_2024_spelling_variant_alias":"鶴見川水系の早渕川／早淵川は横浜市公式により同一河川の表記ゆれを確認。資料原表記は記録に保持（区間コード未同定）",
        "spelling_variant_official_source":"https://www.city.yokohama.lg.jp/tsuzuki/kurashi/machizukuri_kankyo/machizukuri/hayabuchigawa/toppage0.html",
        "eDNA_not_specimen_or_capture":True,
        "eDNA_insects_not_assigned_to_benthic_capture":True,
        "all_source_name_groups_accessible_without_guessing_prefecture":True,
        "all_precise_sampling_sites_excluded":True,
        "no_WordPress_or_API_calls":True}
    (OUT/"viewer_integrity_v12.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))
    return report

if __name__=="__main__":
    main()
