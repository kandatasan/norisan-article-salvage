#!/usr/bin/env python3
"""v23 research preview. Add China-region watershed fish references, NOT river occurrences."""
import csv,hashlib,io,json
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
OUT=HERE/"outputs"
V22=ROOT/"research-individual-v22"/"outputs"/"river_fish_navigation_and_review_v22.zip"
V22QA=ROOT/"research-individual-v22"/"outputs"/"same_name_navigation_qa_v22.json"
RAW=ROOT/"official_chugoku_watershed_year_fish_v05.csv"
MANIFEST=ROOT/"official_chugoku_manifest_v05.json"
ZIP=OUT/"river_fish_chugoku_watershed_reference_v23.zip"
QA=OUT/"chugoku_watershed_fish_qa_v23.json"
SOURCE_PREFS={"鳥取県","島根県","岡山県","広島県","山口県"}

def enc(o):
    return (json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode("utf-8")
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    upstream=json.loads(V22QA.read_text(encoding="utf-8"))
    sha=hashlib.sha256(V22.read_bytes()).hexdigest()
    assert sha==upstream["zip_sha256"],"v22 ZIP hash mismatch"
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows=list(csv.DictReader(RAW.open(encoding="utf-8-sig",newline="")))
    assert len(rows)==manifest["aggregated_records"]==2285
    assert len({r["watershed"] for r in rows})==manifest["unique_watersheds"]==13
    assert len({r["recorded_name"] for r in rows})==manifest["distinct_name_labels"]==216
    for r in rows:
        assert r["source_url"]==manifest["source_url"],r
        assert r["source_sha256"]==manifest["source_sha256"],r
        assert int(r["survey_year"]) in range(2006,2024)
        assert r["recorded_name"] and r["watershed"]
    assert len({(r["watershed"],r["survey_year"],r["recorded_name"]) for r in rows})==len(rows)
    # No records from the old mixed fish/benthic year labels, and no sampling-site locations.
    buckets=defaultdict(lambda:defaultdict(set))
    for r in rows:
        buckets[r["watershed"]][r["recorded_name"]].add(int(r["survey_year"]))
    with ZipFile(V22) as source:
        assert source.testzip() is None
        atlas=json.loads(source.read("atlas.json"))
        master=json.loads(source.read("fish_master.json"))
        assert len(atlas["entries"])==1568 and len(master["taxa"])==639
        refs={};known_names=0;unknown_names=0
        for water,fish in sorted(buckets.items()):
            digest=hashlib.sha256(water.encode("utf-8")).hexdigest()[:16]
            path="watershed-reference/"+digest+".json"
            names=[]
            for name,years in sorted(fish.items()):
                tax=master["taxa"].get(name)
                # Neither regulatory certainty nor validated species status is derived from name matching.
                can_score=bool(tax and tax.get("classification_status")=="named_fish" and
                               tax.get("editorial_status")=="AI_DRAFT_UNVERIFIED")
                if can_score:known_names+=1
                else:unknown_names+=1
                names.append({"recorded_name":name,"survey_years":sorted(years),
                   "classification":"UNVERIFIED_SOURCE_LABEL_WITH_GENERAL_EDITORIAL_HINT" if can_score else "SOURCE_LABEL_NOT_CONFIRMED_UNIQUE_SPECIES",
                   "general_rarity":tax["draft_scores"].get("rarity_stars") if can_score else None,
                   "general_taste":tax["draft_scores"].get("taste_stars") if can_score else None,
                   "general_memo":tax.get("draft_memo") if can_score else None})
            pack={"schema":"tsurikue-watershed-reference-v23",
                  "watershed_name_as_recorded":water,
                  "geographic_scope":"WHOLE_WATERSHED_YEAR_NAME_RECORD_NOT_SPECIFIC_RIVER",
                  "name_identity_not_approved":True,
                  "source_region":"中国地方",
                  "survey_type":"MLIT_HISTORICAL_FISH_SURVEY_NAME_NOT_EDNA",
                  "source_url":manifest["source_url"],
                  "source_sha256":manifest["source_sha256"],
                  "source_title":manifest["source_title"],
                  "source_is_edited_aggregate":True,
                  "original_provenance_rows_count":sum(len(y) for y in fish.values()),
                  "name_groups":names}
            refs[water]=(path,pack)
        old_entry_count=0
        source_entry_count=0
        for e in atlas["entries"]:
            w=e["water"]
            if w not in refs:continue
            if e.get("source_only_name_evidence_v21"):
                if e.get("source_prefecture") not in SOURCE_PREFS:continue
                source_entry_count+=1
            else:
                if e.get("region")!="chugoku":continue
                old_entry_count+=1
            e["watershed_fish_reference_v23"]={
                "pack":refs[w][0],
                "match_type":"CHUGOKU_REGION_AND_LITERAL_WATERSHED_NAME_ONLY",
                "river_specific_fish_count_added":0,
                "watched_survey_years":"2006-2023",
                "same_physical_watershed_identity_confirmed":False}
        atlas["watershed_reference_v23"]={
            "source":"MLIT_CHUGOKU_FISH_WATERSHED_YEAR_V05",
            "scope":"WATERSHED_YEAR_NAME_ONLY_NO_RIVER_JOIN",
            "watersheds":13,"source_rows":2285,"original_fish_evidence_associations_unchanged":True,
            "not_a_direct_species_observation_in_selected_tributary":True}
        with ZipFile(ZIP,"w",compression=ZIP_DEFLATED,compresslevel=8) as out:
            for filename in source.namelist():
                raw=source.read(filename)
                if filename=="atlas.json":raw=enc(atlas)
                elif filename=="index.html":
                    html=raw.decode("utf-8")
                    marker="async function chooseRiver(){"
                    assert html.count(marker)==1
                    extra="""function showWaterSystemReferenceV23(e){
 if(!e||!e.watershed_fish_reference_v23)return;
 const ref=e.watershed_fish_reference_v23;
 const details=node("details");
 details.appendChild(node("summary","同名水系の魚記録を参考で見る（個別河川の記録ではありません）"));
 const body=node("div",undefined,"notice");
 body.appendChild(node("p","この一覧は中国地方の国交省調査を水系名ごとにまとめたものです。この川・支流で見つかった魚とは断定できません。調査期間は2006～2023年です。","note"));
 details.appendChild(body);
 let loaded=false;
 details.addEventListener("toggle",async()=>{
  if(!details.open||loaded)return;
  loaded=true;
  try{
   const pack=await load(ref.pack);
   if(pack.schema!=="tsurikue-watershed-reference-v23"||pack.watershed_name_as_recorded!==e.water||
      pack.geographic_scope!=="WHOLE_WATERSHED_YEAR_NAME_RECORD_NOT_SPECIFIC_RIVER")throw Error("水系参考記録の対応を検証できません");
   body.appendChild(node("p","同名水系の資料記載名："+pack.name_groups.length+"件（異なる魚種数ではありません）","note"));
   const container=node("div",undefined,"fishlist-reference");
   body.appendChild(container);
   let shown=0;
   const button=node("button","さらに30件見る");
   button.type="button";
   function append(){
    const part=pack.name_groups.slice(shown,shown+30);
    for(const r of part){
     const c=node("article",undefined,"fish");
     c.appendChild(node("h3",r.recorded_name));
     if(r.general_rarity!==null){c.appendChild(node("p","一般レア度 ★".repeat(0)+"★".repeat(r.general_rarity)+"☆".repeat(5-r.general_rarity),"note"))}
     if(r.general_taste!==null){c.appendChild(node("p","一般的な味 "+"★".repeat(r.general_taste)+"☆".repeat(5-r.general_taste),"note"))}
     if(r.general_memo)c.appendChild(node("p",r.general_memo,"memo"));
     c.appendChild(node("p","水系単位の記録年："+r.survey_years.join("・")+"年（個別河川の記録ではありません）","note"));
     container.appendChild(c)
    }
    shown+=part.length;
    button.hidden=shown>=pack.name_groups.length;
   }
   button.addEventListener("click",append);
   body.appendChild(button);
   const a=node("a","国交省の元資料");a.href=pack.source_url;a.target="_blank";a.rel="noopener noreferrer";body.appendChild(a);
   body.appendChild(node("p","元資料を加工した参考図鑑です。名称と一般★は科学的な種同定・食用安全性・現在の生息を保証しません。","note"));
   append();
  }catch(error){
    body.appendChild(node("p","参考資料の読み込みに失敗しました。"+String(error),"notice"));
  }
 });
 $("fishlist").appendChild(details);
}
const sourceOnlyBeforeWatershedV23=sourceOnlyDetail;
sourceOnlyDetail=function(e){sourceOnlyBeforeWatershedV23(e);showWaterSystemReferenceV23(e);}
const renderBeforeWatershedV23=render;
render=function(){renderBeforeWatershedV23();if(current&&!current.source_only_name_evidence_v21)showWaterSystemReferenceV23(current);}
"""
                    # rendered HTML is source-only, the existing 511 records, and an independent optional watermark.
                    html=html.replace(marker,extra+"\n"+marker)
                    html=html.replace("v0.22","v0.23")
                    anchor='<p class="note">【魚記録あり】は元の調査資料への入口'
                    assert html.count(anchor)==1
                    html=html.replace(anchor,'<p class="note">中国地方13水系の「水系全体の参考魚記録」を別枠で追加。水系全体の名前を個別の川へ割り当てません。出典の商用利用は条件を満たす必要があります。</p>\n'+anchor)
                    raw=html.encode("utf-8")
                elif filename=="readme_preview.txt":
                    raw=("つりくえ！全国河川魚類図鑑v23 研究版。\n"
                         "中国地方13水系・2285の水系×年×魚名レコードは『水系全体の参考』でのみ表示。\n"
                         "選んだ個別河川での捕獲や生息を示さない。元の調査／DNA分類を保持。\n"
                         "重要種の精密位置は含めない。WordPress本番には未反映。\n").encode("utf-8")
                out.writestr(filename,raw)
            for _,(name,pack) in sorted(refs.items()):
                out.writestr(name,enc(pack))
            out.writestr("chugoku_watershed_fish_source_rows_v23.csv",RAW.read_bytes())
        with ZipFile(ZIP) as z:
            assert z.testzip() is None
            a=json.loads(z.read("atlas.json"))
            assert len(a["entries"])==1568
            assert len(json.loads(z.read("fish_master.json"))["taxa"])==639
            assert "showWaterSystemReferenceV23" in z.read("index.html").decode()
            for water,(name,p) in refs.items():
                item=json.loads(z.read(name))
                assert item["original_provenance_rows_count"]==len([r for r in rows if r["watershed"]==water])
            assert z.read("chugoku_watershed_fish_source_rows_v23.csv")==RAW.read_bytes()
        result={"version":"v23","research_only":True,"source_v22_sha256":sha,
          "watersheds_as_distinct_reference_packs":len(refs),
          "source_watershed_year_name_rows":len(rows),
          "unique_source_fish_names_not_distinct_species":len({r["recorded_name"] for r in rows}),
          "water_year_name_record_status":"WHOLE_WATERSHED_NOT_SPECIFIC_RIVER",
          "old_survey_entries_with_reference":old_entry_count,
          "official_name_only_entries_with_reference":source_entry_count,
          "reference_name_groups_with_general_stars":known_names,
          "reference_name_groups_without_verified_master_name":unknown_names,
          "original_511_survey_groups_preserved":511,
          "original_1057_official_name_groups_preserved":1057,
          "original_195_unknown_prefecture_groups_preserved":195,
          "new_direct_river_fish_occurrences":0,
          "no_new_dna_method_claims":True,
          "no_wordpress_or_production_changes":True,
          "zip":ZIP.name,"zip_sha256":hashlib.sha256(ZIP.read_bytes()).hexdigest()}
        QA.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(result,ensure_ascii=False))
if __name__=="__main__":main()
