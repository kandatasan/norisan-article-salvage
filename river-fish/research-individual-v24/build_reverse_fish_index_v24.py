#!/usr/bin/env python3
"""Research-only v24: build fish-name -> original river-survey groups from actual fish packs.
Never join watershed-only fish names or official-name-only rivers to biota.
"""
import csv
import hashlib
import io
import json
from collections import defaultdict,Counter
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
OUT=HERE/"outputs"
SOURCE=ROOT/"research-individual-v23"/"outputs"/"river_fish_chugoku_watershed_reference_v23.zip"
SOURCE_QA=ROOT/"research-individual-v23"/"outputs"/"chugoku_watershed_fish_qa_v23.json"
ZIP=OUT/"river_fish_reverse_lookup_v24.zip"
QA=OUT/"fish_to_river_reverse_qa_v24.json"
CSV=OUT/"fish_to_river_reverse_evidence_v24.csv"

def serialize(obj):
    return (json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode("utf-8")

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    qa23=json.loads(SOURCE_QA.read_text(encoding="utf-8"))
    sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert sha==qa23["zip_sha256"],"v23 source SHA mismatch"
    with ZipFile(SOURCE) as z:
        assert z.testzip() is None
        atlas=json.loads(z.read("atlas.json"))
        master=json.loads(z.read("fish_master.json"))
        entries=atlas["entries"][:511]
        assert len(atlas["entries"])==1568 and len(entries)==511 and len(master["taxa"])==639
        assert sum(x.get("source_only_name_evidence_v21") is True for x in atlas["entries"])==1057
        assert atlas["research_display_name_groups"]==511
        original_by_id={e["id"]:e for e in entries}
        # Prefecture may be deliberately unknown. Use original nav keys exactly,
        # because unknown-prefecture navigation uses a regional heading for water.
        nav=defaultdict(list)
        for l in atlas["links"]:
            if l["river_id"] in original_by_id:
                nav[l["river_id"]].append({"prefecture":l["prefecture"],"navigation_water":l["water"]})
        assert all(nav[e["id"]] for e in entries)
        assert len({e["id"] for e in entries if any(
           l["prefecture"]==atlas["unknown_prefecture_bucket"] for l in nav[e["id"]])})==195
        candidate={name for name,obj in master["taxa"].items()
                   if obj.get("classification_status")=="named_fish"
                   and obj.get("editorial_status")=="AI_DRAFT_UNVERIFIED"}
        assert len(candidate)==349,len(candidate)
        reverse=defaultdict(dict)
        covered_by_method=Counter()
        old_file_paths=set()
        dna_paths=set()
        all_individual_fish_mentions=0
        excluded_labels=Counter()
        for e in entries:
            historical=e.get("old",{}).get("fish")
            dna=e.get("edna")
            if historical:
                assert historical not in old_file_paths,"Unexpected shared individual fish path"
                old_file_paths.add(historical)
                doc=json.loads(z.read(historical))
                if e["kind"]=="historical_national_river_survey":
                    assert doc["schema"]=="river-category-historical-v09"
                    assert doc["river_identity"]==e["id"] and doc["category"]=="fish"
                    rows=doc["labels"]
                else:
                    assert e["kind"]=="historical_survey_river_name_multiple_code_candidates"
                    assert doc["schema"]=="v10_provisional_river_name_only"
                    assert doc["river_label_group_key"]==e["id"] and doc["category"]=="fish"
                    rows=doc["records"]
                for row in rows:
                    all_individual_fish_mentions+=1
                    name=row["recorded_name"]
                    if name not in candidate:
                        excluded_labels[name]+=1
                        continue
                    vals=reverse[name]
                    info=vals.setdefault(e["id"],{
                      "river_id":e["id"],"method_flags":set(),
                      "historic_year_bounds":[],"edna_years":set()})
                    info["method_flags"].add("HISTORICAL_SURVEY_SOURCE_NAME")
                    y1=row.get("year_min",row.get("first_year"))
                    y2=row.get("year_max",row.get("last_year"))
                    if y1 is not None or y2 is not None:
                        for yy in (y1,y2):
                            if yy is not None:assert 1900<=int(yy)<=2026,(name,e["id"],yy)
                        info["historic_year_bounds"].append([y1,y2])
                    covered_by_method["historical_original_label_mentions"]+=1
            if dna:
                assert dna not in dna_paths,"Unexpected shared eDNA path"
                dna_paths.add(dna)
                doc=json.loads(z.read(dna))
                assert doc["id"]==e["id"] and doc["water"]==e["water"]
                assert doc["name"]==e["name"] and doc["not_capture_or_visual_survey"]
                for row in doc["records"]:
                    assert row["method"]=="eDNA"
                    if row["group"]!="fish":continue
                    all_individual_fish_mentions+=1
                    name=row["name"]
                    if name not in candidate:
                        excluded_labels[name]+=1
                        continue
                    info=reverse[name].setdefault(e["id"],{
                      "river_id":e["id"],"method_flags":set(),
                      "historic_year_bounds":[],"edna_years":set()})
                    info["method_flags"].add("ENVIRONMENTAL_DNA_DETECTED_NOT_CAPTURED")
                    assert 2023<=int(row["year"])<=2025
                    info["edna_years"].add(int(row["year"]))
                    covered_by_method["edna_original_label_mentions"]+=1
        assert old_file_paths and dna_paths
        groups=[]
        evidence=[]
        methods=Counter()
        unknown_matches=0
        for name,match in sorted(reverse.items()):
            assert name in candidate
            records=[]
            for river_id,rec in sorted(match.items()):
                e=original_by_id[river_id]
                historic=rec["historic_year_bounds"]
                ys=[int(y) for bounds in historic for y in bounds if y is not None]
                edna=sorted(rec["edna_years"])
                flag=sorted(rec["method_flags"])
                assert set(flag)<={
                   "HISTORICAL_SURVEY_SOURCE_NAME","ENVIRONMENTAL_DNA_DETECTED_NOT_CAPTURED"}
                for f in flag:methods[f]+=1
                if any(l["prefecture"]==atlas["unknown_prefecture_bucket"] for l in nav[river_id]):
                    unknown_matches+=1
                records.append({
                  "river_id":river_id,"watershed_name":e["water"],"river_name":e["name"],
                  "source_river_kind":e["kind"],
                  "original_navigation_paths":nav[river_id],
                  "method_flags":flag,
                  "historical_first_last_year_bound":[min(ys),max(ys)] if ys else None,
                  "edna_positive_years":edna,
                  "year_range_is_not_list_of_all_yearly_occurrences":True,
                  "physical_river_identification_approved":False,
                })
                evidence.append({"recorded_fish_name":name,"survey_river_group_id":river_id,
                  "original_water_label":e["water"],"original_river_label":e["name"],
                  "original_prefecture_navigation":"|".join(l["prefecture"] for l in nav[river_id]),
                  "survey_methods":"|".join(flag),
                  "first_last_historical_years":"-".join(str(y) for y in [min(ys),max(ys)]) if ys else "",
                  "eDNA_positive_years":"|".join(str(y) for y in edna),
                  "source_verified_same_physical_river":"NO",
                  "is_source_river_name_group_not_verified_geographic_identity":"YES"})
            groups.append({"recorded_fish_name":name,"reference_count":len(records),
               "editorial_taxon_status":"AI_EDITORIAL_NAMED_FISH_CANDIDATE_NOT_HUMAN_TAXONOMY_APPROVED",
               "river_survey_groups":records})
        assert len({r["recorded_fish_name"] for r in groups})==len(groups)
        assert len({(r["recorded_fish_name"],r["survey_river_group_id"]) for r in evidence})==len(evidence)
        assert all(r["river_id"] in original_by_id for item in groups for r in item["river_survey_groups"])
        assert not any(r["river_id"].startswith("official21_") for item in groups for r in item["river_survey_groups"])
        lookup={"schema":"tsurikue-fish-to-source-river-groups-v24",
          "not_geographic_or_current_presence_claim":True,
          "included_name_filter":"MASTER_CLASSIFICATION_NAMED_FISH_AND_AI_EDITORIAL_DRAFT_ONLY",
          "excluded_alias_and_taxonomy_held_names":True,
          "environmental_DNA_separated_from_historical_fish_survey":True,
          "watershed_wide_reference_not_attached":True,
          "sensitive_exact_sampling_locations_not_included":True,
          "lookups":groups}
        csvbuf=io.StringIO()
        writer=csv.DictWriter(csvbuf,fieldnames=[
          "recorded_fish_name","survey_river_group_id","original_water_label",
          "original_river_label","original_prefecture_navigation","survey_methods",
          "first_last_historical_years","eDNA_positive_years",
          "source_verified_same_physical_river","is_source_river_name_group_not_verified_geographic_identity"],
          lineterminator="\n")
        writer.writeheader();writer.writerows(evidence)
        CSV.write_text(csvbuf.getvalue(),encoding="utf-8-sig")
        # The new lookup is a separate file; the 511 original and 1057 name-only
        # entries, all original evidence JSONs, and fish master are byte-for-byte identical.
        with ZipFile(ZIP,"w",compression=ZIP_DEFLATED,compresslevel=8) as out:
            for name in z.namelist():
                raw=z.read(name)
                if name=="index.html":
                    page=raw.decode("utf-8")
                    marker="<main>\n<section>"
                    assert page.count(marker)==1,"unexpected research viewer structure"
                    html_intro="""<main>
<section id="fishReverseFinderV24">
<h2>🐟 魚の名前から川を探す</h2>
<p class="note">魚の名前を入れると、その名前が載った過去の調査資料や環境DNAの河川名グループが見つかります。資料名の一致は、いまそこで釣れることを保証しません。</p>
<label for="reverseFishV24">調べたい魚の名前</label>
<input id="reverseFishV24" type="search" placeholder="例：アユ・オイカワ" autocomplete="off" maxlength="60">
<p id="reverseStatusV24" class="note" role="status" aria-live="polite">魚名を入力してください。</p>
<div id="reverseResultsV24" aria-live="polite"></div>
<button id="reverseMoreV24" type="button" hidden>さらに30件の記録を見る</button>
</section>
<section>"""
                    page=page.replace(marker,html_intro)
                    js_marker="setup();\n</script>"
                    assert page.count(js_marker)==1
                    script="""// v24 reverse-search only traverses pre-existing survey source group IDs.
// It does NOT derive geographical identity, current presence or edibility.
let reverseIndexV24=null,reverseEpochV24=0,reverseShownV24=30,reverseHitsV24=[];
const reverseMaxResultsV24=30;
function reverseNavV24(nav,id){
 const e=atlas?.entries.find(x=>x.id===id);
 if(!e||e.source_only_name_evidence_v21)return;
 $("pref").value=nav.prefecture;choosePref();
 $("water").value=nav.navigation_water;chooseWater();
 $("river").value=id;chooseRiver();
}
function reverseRenderV24(){
 const box=$("reverseResultsV24"),more=$("reverseMoreV24");
 empty(box);more.hidden=true;
 const found=reverseHitsV24.slice(0,reverseShownV24);
 for(const item of found){
  const e=node("article",undefined,"record");
  e.appendChild(node("strong",item.recorded_fish_name));
  const info=node("p","調査資料の河川名グループ "+item.reference_count+"件（異なる実在河川の本数ではありません）","note");
  e.appendChild(info);
  const tax=master?.taxa?.[item.recorded_fish_name];
  if(tax?.classification_status==="named_fish"){
   const stars=tax?.draft_scores;
   if(stars?.rarity_stars!=null)e.appendChild(node("p","一般レア度 "+"★".repeat(stars.rarity_stars)+"☆".repeat(5-stars.rarity_stars),"note"));
   if(stars?.taste_stars!=null)e.appendChild(node("p","味の目安 "+"★".repeat(stars.taste_stars)+"☆".repeat(5-stars.taste_stars),"note"));
   if(tax.draft_memo)e.appendChild(node("p",tax.draft_memo,"memo"));
  }
  const links=node("div",undefined,"source-river-links");
  e.appendChild(links);
  const expand=node("button","さらに河川名の記録を見る");
  expand.type="button";
  let visible=0;
  const appendRivers=()=>{
   const selected=item.river_survey_groups.slice(visible,visible+14);
   for(const row of selected){
    const nav=row.original_navigation_paths[0];
    if(!nav)continue;
    const pref=nav.prefecture,methods=row.method_flags;
    const method=methods.map(x=>x==="ENVIRONMENTAL_DNA_DETECTED_NOT_CAPTURED"?"DNA検出（捕獲記録ではない）":"過去の魚類調査").join("＋");
    const button=node("button",(pref===atlas.unknown_prefecture_bucket?"所在県未確定":pref)+"｜"+row.watershed_name+"水系・"+row.river_name+"｜"+method);
    button.type="button";
    button.addEventListener("click",()=>reverseNavV24(nav,row.river_id));
    links.appendChild(button);
   }
   visible+=selected.length;
   expand.hidden=visible>=item.river_survey_groups.length;
  };
  expand.addEventListener("click",appendRivers);
  e.appendChild(expand);
  appendRivers();
  box.appendChild(e)
 }
 more.hidden=reverseHitsV24.length>reverseShownV24;
}
async function reverseQueryV24(){
 const seq=++reverseEpochV24;
 const raw=$("reverseFishV24").value.trim().toLocaleLowerCase();
 reverseShownV24=reverseMaxResultsV24;reverseHitsV24=[];
 empty($("reverseResultsV24"));$("reverseMoreV24").hidden=true;
 if(!raw){$("reverseStatusV24").textContent="魚名を入力してください。";return}
 $("reverseStatusV24").textContent="魚の調査記録を検索中…";
 try{
  if(!reverseIndexV24)reverseIndexV24=await load("fish_to_river_reverse_v24.json");
  if(seq!==reverseEpochV24)return;
  if(reverseIndexV24.schema!=="tsurikue-fish-to-source-river-groups-v24"||
     !reverseIndexV24.environmental_DNA_separated_from_historical_fish_survey)throw Error("逆引きデータの検証に失敗");
  reverseHitsV24=reverseIndexV24.lookups.filter(x=>x.recorded_fish_name.toLocaleLowerCase().includes(raw));
  $("reverseStatusV24").textContent=reverseHitsV24.length?"該当する魚名 "+reverseHitsV24.length+"件（原資料の表記名です）":"一致する魚名はありません。未収録の魚がいないという意味ではありません。";
  reverseRenderV24()
 }catch(err){if(seq!==reverseEpochV24)return;$("reverseStatusV24").textContent="逆引きデータを読み込めませんでした。 "+String(err)}
}
function setupReverseV24(){
 $("reverseFishV24").addEventListener("input",reverseQueryV24);
 $("reverseMoreV24").addEventListener("click",()=>{reverseShownV24+=reverseMaxResultsV24;reverseRenderV24()});
}
setup();
setupReverseV24();
</script>"""
                    page=page.replace(js_marker,script)
                    page=page.replace("v0.23","v0.24")
                    raw=page.encode("utf-8")
                elif name=="readme_preview.txt":
                    raw=("つりくえ！全国河川魚図鑑 v0.24 研究専用。\n"
                         "魚名から既存の511資料河川名グループの元調査やeDNA記録を逆引き。\n"
                         "同一河川の地理的同定・現在の生息・採捕の保証ではありません。\n"
                         "種名分類に保留のある原資料名は逆引き魚種一覧には入れません。\n"
                         "水系全体の参考魚名を個別河川へ割り当てていません。\n"
                         "研究ZIPのみ。WordPress本番未反映。\n").encode("utf-8")
                out.writestr(name,raw)
            out.writestr("fish_to_river_reverse_v24.json",serialize(lookup))
            out.writestr("fish_to_river_reverse_evidence_v24.csv",csvbuf.getvalue().encode("utf-8-sig"))
        with ZipFile(ZIP) as verify:
            assert verify.testzip() is None
            checked=json.loads(verify.read("fish_to_river_reverse_v24.json"))
            assert checked==lookup
            assert verify.read("fish_master.json")==z.read("fish_master.json")
            assert verify.read("atlas.json")==z.read("atlas.json")
            assert "reverseQueryV24" in verify.read("index.html").decode("utf-8")
        qa={"version":"v24","research_only":True,"upstream_v23_sha256":sha,
          "fish_editorial_candidate_names":len(candidate),
          "fish_names_with_river_survey_evidence":len(groups),
          "fish_names_without_river_survey_evidence":len(candidate)-len(groups),
          "fish_name_x_original_survey_group_pairs":len(evidence),
          "original_fish_label_occurrences_in_source_json":all_individual_fish_mentions,
          "indexed_historical_original_label_mentions":covered_by_method["historical_original_label_mentions"],
          "indexed_edna_original_label_mentions":covered_by_method["edna_original_label_mentions"],
          "indexed_historical_name_x_group_pairs":methods["HISTORICAL_SURVEY_SOURCE_NAME"],
          "indexed_edna_name_x_group_pairs":methods["ENVIRONMENTAL_DNA_DETECTED_NOT_CAPTURED"],
          "survey_group_pairs_with_unverified_prefecture":unknown_matches,
          "source_labels_excluded_for_taxonomy_or_nonfish":sum(excluded_labels.values()),
          "previous_511_original_survey_groups_preserved":True,
          "previous_1057_official_name_only_groups_preserved":True,
          "previous_195_unverified_prefecture_groups_preserved":True,
          "watershed_level_fish_records_transferred_to_river":0,
          "official_name_only_rivers_with_fish_observations_added":0,
          "commercial_rights_final_check":False,
          "no_wordpress_or_live_api_changes":True,
          "archive":ZIP.name,"archive_sha256":hashlib.sha256(ZIP.read_bytes()).hexdigest()}
        QA.write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(qa,ensure_ascii=False))
if __name__=="__main__":main()
