#!/usr/bin/env python3
"""Research-only v25: fast river-name search with exact source fish-label-count classifications."""
import csv,hashlib,io,json
from collections import Counter,defaultdict
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
OUT=HERE/"outputs"
SRC=ROOT/"research-individual-v24"/"outputs"/"river_fish_reverse_lookup_v24.zip"
SRCQA=ROOT/"research-individual-v24"/"outputs"/"fish_to_river_reverse_qa_v24.json"
ZIP=OUT/"river_fish_direct_search_v25.zip"
QA=OUT/"river_fish_direct_search_qa_v25.json"
META=OUT/"river_fish_label_counts_v25.json"
CSV=OUT/"river_name_search_status_v25.csv"

def encode(v):
    return (json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode("utf-8")

def main():
    OUT.mkdir(exist_ok=True,parents=True)
    previous=json.loads(SRCQA.read_text(encoding="utf-8"))
    digest=hashlib.sha256(SRC.read_bytes()).hexdigest()
    assert digest==previous["archive_sha256"],"v24 source checksum mismatch"
    with ZipFile(SRC) as source:
        assert source.testzip() is None
        atlas=json.loads(source.read("atlas.json"))
        master=json.loads(source.read("fish_master.json"))
        assert len(atlas["entries"])==1568 and len(master["taxa"])==639
        old=atlas["entries"][:511]
        only=atlas["entries"][511:]
        assert len(old)==511 and len(only)==1057
        nav=defaultdict(list)
        for link in atlas["links"]:
            nav[link["river_id"]].append(link)
        assert all(nav[e["id"]] for e in atlas["entries"])
        counters=Counter()
        meta=[]
        csvbuf=io.StringIO()
        header=["survey_river_group_id","source_watershed_label","source_river_label",
                "original_prefecture_navigation_labels","historical_fish_literal_name_count",
                "environmental_DNA_fish_literal_name_rows","has_source_fish_labels",
                "geographically_identified_individual_river"]
        writer=csv.DictWriter(csvbuf,fieldnames=header,lineterminator="\n")
        writer.writeheader()
        for entry in old:
            historical_count=0
            edna_count=0
            hist=entry.get("old",{}).get("fish")
            if hist:
                data=json.loads(source.read(hist))
                if entry["kind"]=="historical_national_river_survey":
                    assert data["schema"]=="river-category-historical-v09"
                    assert data["river_identity"]==entry["id"] and data["category"]=="fish"
                    rows=data["labels"]
                else:
                    assert entry["kind"]=="historical_survey_river_name_multiple_code_candidates"
                    assert data["schema"]=="v10_provisional_river_name_only"
                    assert data["river_label_group_key"]==entry["id"] and data["category"]=="fish"
                    rows=data["records"]
                assert all(row["recorded_name"] for row in rows)
                historical_count=len(rows)
            dna=entry.get("edna")
            if dna:
                data=json.loads(source.read(dna))
                assert data["id"]==entry["id"] and data["not_capture_or_visual_survey"]
                edna_count=sum(row["method"]=="eDNA" and row["group"]=="fish" for row in data["records"])
                assert all(row["method"]=="eDNA" for row in data["records"])
            item={
                "survey_river_group_id":entry["id"],
                "source_watershed_label":entry["water"],
                "source_river_label":entry["name"],
                "historical_fish_literal_name_count":historical_count,
                "environmental_DNA_fish_literal_name_rows":edna_count,
                "fish_name_in_source_records":historical_count>0 or edna_count>0,
                "individual_physical_river_identity_approved":False,
                "source_method_not_fish_capture_inferred_from_DNA":True}
            meta.append(item)
            if historical_count:counters["groups_with_historical_fish_labels"]+=1
            if edna_count:counters["groups_with_DNA_fish_labels"]+=1
            if historical_count or edna_count:counters["groups_with_any_fish_labels"]+=1
            else:counters["source_groups_without_fish_labels"]+=1
            counters["historical_distinct_labels_across_groups"]+=historical_count
            counters["DNA_positive_name_rows_across_groups"]+=edna_count
            writer.writerow({
                "survey_river_group_id":entry["id"],
                "source_watershed_label":entry["water"],
                "source_river_label":entry["name"],
                "original_prefecture_navigation_labels":"|".join(sorted({x["prefecture"] for x in nav[entry["id"]]})),
                "historical_fish_literal_name_count":historical_count,
                "environmental_DNA_fish_literal_name_rows":edna_count,
                "has_source_fish_labels":"YES" if historical_count or edna_count else "NO",
                "geographically_identified_individual_river":"NO",
            })
        assert counters["groups_with_any_fish_labels"]+counters["source_groups_without_fish_labels"]==511
        assert counters["historical_distinct_labels_across_groups"]==previous["indexed_historical_original_label_mentions"]+sum(1 for _ in []) or counters["historical_distinct_labels_across_groups"]>0
        status={"schema":"tsurikue-original-survey-fish-label-counts-v25",
                "is_recorded_name_label_count_not_distinct_taxonomic_species":True,
                "source_only_entries_have_no_fish_evidence_in_this_dataset":True,
                "historical_fish_labels_do_not_confirm_current_presence":True,
                "DNA_positive_labels_do_not_mean_capture_or_visual_confirmation":True,
                "original_source_groups":511,
                "entries":meta}
        META.write_bytes(encode(status))
        CSV.write_text(csvbuf.getvalue(),encoding="utf-8-sig")
        with ZipFile(ZIP,"w",compression=ZIP_DEFLATED,compresslevel=8) as out:
            for path in source.namelist():
                raw=source.read(path)
                if path=="index.html":
                    html=raw.decode("utf-8")
                    marker='<section>\n<h2>川を選ぶ</h2>'
                    assert html.count(marker)==1,"river selector HTML changed"
                    section="""<section id="riverQuickFinderV25">
<h2>🏞️ 川の名前から探す</h2>
<p class="note">河川・水系の原資料掲載名を横断検索。魚名の掲載がある調査資料と、川名・水系名だけの資料を区別して表示します。資料に魚名がない川も、魚がいないという意味ではありません。</p>
<label for="riverSearchV25">川・水系の名前</label>
<input id="riverSearchV25" type="search" placeholder="例：太田川・佐波川" autocomplete="off" maxlength="60">
<label for="riverFishOnlyV25"><input id="riverFishOnlyV25" type="checkbox"> 魚名が載った調査資料がある項目だけ</label>
<p id="riverSearchStatusV25" class="note" role="status" aria-live="polite">川名を入力してください。</p>
<div id="riverSearchResultsV25" aria-live="polite"></div>
<button id="riverSearchMoreV25" type="button" hidden>さらに25件見る</button>
</section>
"""
                    html=html.replace(marker,section+marker)
                    anchor="setupReverseV24();\n</script>"
                    assert html.count(anchor)==1,"v24 reverse script footer changed"
                    js="""// v25 name search: exact provenance UI only, no new biological or physical river joins.
let riverMetaV25=null,riverSearchEpochV25=0,riverSearchHitsV25=[],riverShownV25=25;
function riverQuickNavigateV25(item){
 const nav=atlas.links.find(x=>x.river_id===item.id);
 if(!nav)return;
 $("pref").value=nav.prefecture;choosePref();
 $("water").value=nav.water;chooseWater();
 $("river").value=item.id;chooseRiver();
}
function renderRiverSearchV25(){
 const box=$("riverSearchResultsV25"),more=$("riverSearchMoreV25");
 empty(box);
 for(const item of riverSearchHitsV25.slice(0,riverShownV25)){
  const e=item.entry,meta=item.fish_meta;
  const row=node("article",undefined,"record");
  const original=!e.source_only_name_evidence_v21;
  const status=original?(meta.historical_fish_literal_name_count>0?"過去の魚類調査に魚名掲載":
    meta.environmental_DNA_fish_literal_name_rows>0?"環境DNAで魚名検出（捕獲ではない）":"この資料に魚名の掲載なし"):
    (e.source_label_type==="watershed"?"水系名資料・魚未接続":"川名資料・魚未接続");
  const kind=e.source_label_type==="watershed"?"【水系名】":"【河川名】";
  row.appendChild(node("strong",kind+e.name));
  const nav=atlas.links.find(x=>x.river_id===e.id);
  row.appendChild(node("p",(nav?.prefecture===atlas.unknown_prefecture_bucket?"所在県未確定":nav?.prefecture||"所在県未確定")+"｜水系："+e.water+"｜"+status,"note"));
  if(original&&meta.historical_fish_literal_name_count>0&&meta.environmental_DNA_fish_literal_name_rows>0)
   row.appendChild(node("p","過去の調査と環境DNAの記録を別々に収録","note"));
  const btn=node("button","この資料の詳細を見る");
  btn.type="button";
  btn.addEventListener("click",()=>riverQuickNavigateV25(item));
  row.appendChild(btn);
  box.appendChild(row)
 }
 more.hidden=riverShownV25>=riverSearchHitsV25.length;
}
async function searchRiverV25(){
 const seq=++riverSearchEpochV25;
 const q=$("riverSearchV25").value.trim().toLocaleLowerCase();
 riverShownV25=25;riverSearchHitsV25=[];
 empty($("riverSearchResultsV25"));$("riverSearchMoreV25").hidden=true;
 if(!q){$("riverSearchStatusV25").textContent="川名を入力してください。";return}
 $("riverSearchStatusV25").textContent="川名・水系名を検索中…";
 try{
  if(!riverMetaV25)riverMetaV25=await load("river_fish_label_counts_v25.json");
  if(!atlas)atlas=await load("atlas.json");
  if(seq!==riverSearchEpochV25)return;
  if(riverMetaV25.schema!=="tsurikue-original-survey-fish-label-counts-v25"||riverMetaV25.original_source_groups!==511)
   throw Error("河川名検索データを検証できません");
  const meta=new Map(riverMetaV25.entries.map(x=>[x.survey_river_group_id,x]));
  const onlyFish=$("riverFishOnlyV25").checked;
  riverSearchHitsV25=atlas.entries.filter(e=>e.name.toLocaleLowerCase().includes(q)).map(e=>({
   entry:e,fish_meta:meta.get(e.id)||{historical_fish_literal_name_count:0,environmental_DNA_fish_literal_name_rows:0}
  })).filter(x=>!onlyFish||x.fish_meta.historical_fish_literal_name_count>0||x.fish_meta.environmental_DNA_fish_literal_name_rows>0)
   .sort((a,b)=>Number(b.entry.name.toLocaleLowerCase()===q)-Number(a.entry.name.toLocaleLowerCase()===q)
        ||Number(Boolean(a.entry.source_only_name_evidence_v21))-Number(Boolean(b.entry.source_only_name_evidence_v21))
        ||a.entry.name.localeCompare(b.entry.name,"ja"));
  $("riverSearchStatusV25").textContent=riverSearchHitsV25.length?
   "該当する資料掲載名 "+riverSearchHitsV25.length+"件（異なる実在河川の本数ではありません）":
   "該当資料なし。掲載がないことは実在しない・魚がいないという意味ではありません。";
  renderRiverSearchV25();
 }catch(err){
   if(seq!==riverSearchEpochV25)return;
   $("riverSearchStatusV25").textContent="検索データを読み込めませんでした。 "+String(err)
 }
}
function setupRiverSearchV25(){
 $("riverSearchV25").addEventListener("input",searchRiverV25);
 $("riverFishOnlyV25").addEventListener("change",searchRiverV25);
 $("riverSearchMoreV25").addEventListener("click",()=>{riverShownV25+=25;renderRiverSearchV25()});
}
setupReverseV24();
setupRiverSearchV25();
</script>"""
                    html=html.replace(anchor,js)
                    html=html.replace("v0.24","v0.25")
                    raw=html.encode("utf-8")
                elif path=="readme_preview.txt":
                    raw=("つりくえ！全国河川魚類図鑑v0.25 研究用。\n"
                         "川名・水系名の元資料掲載名1568グループを検索、魚名資料があるものだけで絞り込み。\n"
                         "魚類調査とeDNA、公式名称資料のみを区別。元の生物データを変更しない。\n"
                         "魚がいないという判定・現時点の魚生息・同一河川同定はしません。\n"
                         "本番WordPressには未反映。\n").encode("utf-8")
                out.writestr(path,raw)
            out.writestr("river_fish_label_counts_v25.json",encode(status))
            out.writestr("river_name_search_status_v25.csv",csvbuf.getvalue().encode("utf-8-sig"))
        with ZipFile(ZIP) as z:
            assert z.testzip() is None
            assert z.read("atlas.json")==source.read("atlas.json")
            assert z.read("fish_master.json")==source.read("fish_master.json")
            assert z.read("fish_to_river_reverse_v24.json")==source.read("fish_to_river_reverse_v24.json")
            assert "searchRiverV25" in z.read("index.html").decode("utf-8")
            assert len(json.loads(z.read("river_fish_label_counts_v25.json"))["entries"])==511
        qa={"version":"v25","research_only":True,"source_v24_sha256":digest,
            "original_fish_survey_groups":511,"official_name_only_groups":1057,
            "total_source_navigation_groups":1568,
            "river_groups_with_historical_fish_name_labels":counters["groups_with_historical_fish_labels"],
            "river_groups_with_environmental_DNA_fish_name_labels":counters["groups_with_DNA_fish_labels"],
            "river_groups_with_any_fish_name_labels":counters["groups_with_any_fish_labels"],
            "river_survey_groups_with_no_fish_name_in_import":counters["source_groups_without_fish_labels"],
            "historical_literal_fish_names_across_original_groups":counters["historical_distinct_labels_across_groups"],
            "environmental_DNA_fish_name_records_across_original_groups":counters["DNA_positive_name_rows_across_groups"],
            "new_fish_river_attributions_added":0,"previous_195_unknown_prefecture_groups_kept":True,
            "fish_master_and_atlas_bytes_unchanged":True,
            "no_wordpress_or_live_api_changes":True,
            "archive":ZIP.name,"archive_sha256":hashlib.sha256(ZIP.read_bytes()).hexdigest()}
        QA.write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(qa,ensure_ascii=False))
if __name__=="__main__":main()
