#!/usr/bin/env python3
"""Research-only v22: link same-name survey *references*, never biological evidence to official-name rows."""
from __future__ import annotations
import csv
import hashlib
import io
import json
from collections import defaultdict, Counter
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
OUT=HERE/"outputs"
V21=ROOT/"research-individual-v21"/"outputs"/"river_fish_47pref_official_name_directory_v21.zip"
V21QA=ROOT/"research-individual-v21"/"outputs"/"river_official_directory_qa_v21.json"
ZIP=OUT/"river_fish_navigation_and_review_v22.zip"
QA=OUT/"same_name_navigation_qa_v22.json"
CANDIDATES=OUT/"same_name_fish_record_references_v22.csv"

def encoded(o):
    return (json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode("utf-8")

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    qa21=json.loads(V21QA.read_text(encoding="utf-8"))
    sha=hashlib.sha256(V21.read_bytes()).hexdigest()
    assert sha==qa21["zip_sha256"],"v21 SHA mismatch"
    with ZipFile(V21) as previous:
        assert previous.testzip() is None
        atlas=json.loads(previous.read("atlas.json"))
        master=json.loads(previous.read("fish_master.json"))
        original=atlas["entries"][:511]
        named=atlas["entries"][511:]
        assert len(original)==511 and len(named)==1057 and len(master["taxa"])==639
        old_links=list(atlas["links"][:-len(named)])
        old_by_id={x["id"]:x for x in original}
        old_matching=defaultdict(set)
        original_unknown=set()
        for l in old_links:
            o=old_by_id[l["river_id"]]
            if l["prefecture"]==atlas["unknown_prefecture_bucket"]:
                original_unknown.add(o["id"])
            else:
                old_matching[(l["prefecture"],o["water"],o["name"])].add(o["id"])
        assert len(original_unknown)==195
        matched_entries=0
        total_links=0
        categories=Counter()
        export=[]
        for e in named:
            assert e["source_only_name_evidence_v21"]
            assert not e["old"] and e["edna"] is None
            assert e["fish_occurrences_linked_from_this_source"]==0
            assert e["river_code"] is None
            if e["source_label_type"]=="river":
                matches=sorted(old_matching[(e["source_prefecture"],e["water"],e["name"])] - original_unknown)
            else:
                matches=[]
            if matches:
                matched_entries+=1
                total_links+=len(matches)
                categories["multiple" if len(matches)>1 else "single"]+=1
                e["same_name_survey_reference_v22"]={
                    "candidate_ids":matches,
                    "status":"UNVERIFIED_SAME_PREFECTURE_WATERSHED_AND_RIVER_LABEL_NOT_SAME_PHYSICAL_RIVER",
                    "display_purpose":"NAVIGATION_TO_SEPARATE_ORIGINAL_SURVEY_RECORD_ONLY",
                    "fish_data_copied_to_official_source_entry":False,
                    "survey_river_geographic_identity_approved":False}
                for m in matches:
                    old=old_by_id[m]
                    export.append({
                        "source_only_id":e["id"],"prefecture":e["source_prefecture"],
                        "watershed_source_label":e["water"],"river_source_label":e["name"],
                        "source_evidence_ids":"|".join(e["source_evidence_ids"]),
                        "source_urls":"|".join(e["official_source_urls"]),
                        "separate_survey_group_id":m,
                        "survey_group_kind":old["kind"],
                        "survey_group_river_code":old.get("river_code") or "",
                        "review_status":"SAME_NAME_SEARCH_HINT_ONLY_NOT_PHYSICAL_IDENTITY_VERIFIED",
                        "fish_transferred":"NO",
                    })
        header=["source_only_id","prefecture","watershed_source_label","river_source_label",
                "source_evidence_ids","source_urls","separate_survey_group_id","survey_group_kind",
                "survey_group_river_code","review_status","fish_transferred"]
        s=io.StringIO()
        writer=csv.DictWriter(s,fieldnames=header,lineterminator="\n")
        writer.writeheader()
        writer.writerows(export)
        CANDIDATES.write_text(s.getvalue(),encoding="utf-8-sig")
        atlas["same_name_navigation_v22"]={
            "purpose":"NAVIGATION_TO_SEPARATE_SURVEY_SOURCE_ONLY",
            "matched_official_name_entries":matched_entries,
            "matched_reference_paths":total_links,
            "never_auto_merged_biota":True,
            "original_195_prefecture_unknown_still_unresolved":True,
        }
        with ZipFile(ZIP,"w",compression=ZIP_DEFLATED,compresslevel=8) as z:
            for path in previous.namelist():
                b=previous.read(path)
                if path=="atlas.json":b=encoded(atlas)
                elif path=="index.html":
                    page=b.decode("utf-8")
                    # Existing evidence associations stay exactly as-is: only decorate official-name cards.
                    anchor="async function chooseRiver(){"
                    assert page.count(anchor)==1
                    injected="""const originalSourceOnlyDetailV21=sourceOnlyDetail;
function sourceOnlyWithSurveyReferencesV22(e){
 originalSourceOnlyDetailV21(e);
 const ref=e.same_name_survey_reference_v22;
 if(!ref||!ref.candidate_ids||!ref.candidate_ids.length)return;
 const note=node("div",undefined,"notice");
 note.appendChild(node("p","同じ県・水系名・川名で登録された別の魚類調査資料があります。ただし同じ河川・区間とはまだ確認できていません。","note"));
 for(const id of ref.candidate_ids){
   const x=atlas.entries.find(v=>v.id===id);
   if(!x)continue;
   const b=node("button","同名の魚類調査記録を見る（同一河川未確認）");
   b.type="button";
   b.addEventListener("click",()=>{
     $("pref").value=e.source_prefecture;choosePref();
     $("water").value=x.water;chooseWater();
     $("river").value=id;chooseRiver();
   });
   note.appendChild(b)
 }
 $("fishlist").appendChild(note);
}
sourceOnlyDetail=sourceOnlyWithSurveyReferencesV22;
"""
                    page=page.replace(anchor,injected+"\n"+anchor)
                    label='opt($("river"),e.id,e.name+(e.kind==="historical_survey_river_name_multiple_code_candidates"?"（区間未特定）":""));'
                    assert page.count(label)==1,"v21 option label changed"
                    page=page.replace(label,'opt($("river"),e.id,e.name+(e.source_only_name_evidence_v21?(e.source_label_type==="watershed"?"【水系資料・魚未接続】":"【川名資料・魚未接続】"):(e.kind==="historical_survey_river_name_multiple_code_candidates"?"【魚記録あり・区間未特定】":"【魚記録あり】")));')
                    sorter='atlas.entries.filter(x=>ids.has(x.id)).sort((a,b)=>a.name.localeCompare(b.name,"ja"))'
                    assert page.count(sorter)==1,"v21 chooser sorter changed"
                    page=page.replace(sorter,'atlas.entries.filter(x=>ids.has(x.id)).sort((a,b)=>Number(Boolean(a.source_only_name_evidence_v21))-Number(Boolean(b.source_only_name_evidence_v21))||a.name.localeCompare(b.name,"ja"))')
                    page=page.replace("v0.21","v0.22")
                    note='<p class="note">公式資料で名前だけ確認した川・水系を追加。'
                    assert page.count(note)==1
                    page=page.replace(note,'<p class="note">【魚記録あり】は元の調査資料への入口、【川名資料・魚未接続】は名称の出典のみ。同じ名前の魚調査ページへのリンクは同一河川を確認した証拠ではありません。</p>\n'+note)
                    b=page.encode("utf-8")
                elif path=="readme_preview.txt":
                    b=("全国河川魚類図鑑 v22 研究専用。\n"
                       "同じ県・水系・川名の別資料から、魚の調査記録への参考リンクを追加。\n"
                       "一致は名称の検索ヒントであり、同一河川の地理的同定や魚の生息証拠ではありません。\n"
                       "元の511魚記録グループ、1057公式掲載名グループ、195所在県未確定は保持。\n"
                       "研究用以外に同期しません。\n").encode("utf-8")
                z.writestr(path,b)
            z.writestr("same_name_fish_record_references_v22.csv",s.getvalue().encode("utf-8-sig"))
        with ZipFile(ZIP) as verify:
            assert verify.testzip() is None
            a=json.loads(verify.read("atlas.json"))
            assert a["entries"][:511]==original
            assert a["links"]==atlas["links"]
            assert a["entries"]==atlas["entries"]
            assert a["same_name_navigation_v22"]["never_auto_merged_biota"]
            assert len(json.loads(verify.read("fish_master.json"))["taxa"])==639
            assert "sourceOnlyWithSurveyReferencesV22" in verify.read("index.html").decode()
        qa={"version":"v22","research_only":True,"v21_sha256":sha,
            "old_fish_evidence_name_groups_unchanged":511,
            "official_source_name_groups_unchanged":1057,
            "old_unknown_prefecture_groups_unchanged":195,
            "source_name_reference_groups":matched_entries,
            "source_name_reference_paths":total_links,
            "single_candidate_groups":categories["single"],
            "multiple_candidate_groups":categories["multiple"],
            "name_only_reference_not_verified_same_river":True,
            "fish_biology_joins_created":0,
            "source_fish_record_bytes_unchanged":True,
            "no_WordPress_or_production_changes":True,
            "zip":ZIP.name,"zip_sha256":hashlib.sha256(ZIP.read_bytes()).hexdigest(),
            "candidate_csv":CANDIDATES.name}
        QA.write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(qa,ensure_ascii=False))
if __name__=="__main__":main()
