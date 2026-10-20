#!/usr/bin/env python3
"""v20 research-only general editorial stars; never deploys to WordPress."""
import csv, hashlib, io, json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
OUT=HERE/"outputs"
V19=ROOT/"research-individual-v19"/"outputs"/"river_fish_evidence_review_v19.zip"
V19QA=ROOT/"research-individual-v19"/"outputs"/"fish_editorial_evidence_qa_v19.json"
POLICY=HERE/"general_editorial_star_policy_v20.json"
ZIP=OUT/"river_fish_general_editorial_stars_v20.zip"
CSV=OUT/"fish_general_star_coverage_v20.csv"
QA=OUT/"fish_general_star_qa_v20.json"

def encode(data):
    return (json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode("utf-8")

def main():
    OUT.mkdir(exist_ok=True,parents=True)
    prevqa=json.loads(V19QA.read_text(encoding="utf-8"))
    assert hashlib.sha256(V19.read_bytes()).hexdigest()==prevqa["archive_sha256"], "v19 source checksum mismatch"
    policy=json.loads(POLICY.read_text(encoding="utf-8"))
    assert policy["human_individual_approval_count"]==0 and policy["official_scientific_star_evidence_count"]==0
    entries=policy["new_taste_star_edits"]
    added={row["recorded_name"]:row for row in entries}
    assert len(entries)==len(added)==26, "no duplicate or missing manual general taste ratings"
    with ZipFile(V19,"r") as src:
        assert src.testzip() is None
        atlas=json.loads(src.read("atlas.json"))
        master=json.loads(src.read("fish_master.json"))
        taxa=master["taxa"]
        assert len(taxa)==639 and len(atlas["entries"])==511
        assert all(row["recorded_name"] in taxa for row in entries)
        original={name:dict(obj.get("draft_scores") or {}) for name,obj in taxa.items()}
        candidate={name:obj for name,obj in taxa.items() if obj.get("editorial_status")=="AI_DRAFT_UNVERIFIED"}
        assert len(candidate)==375
        assert sum(x.get("draft_scores",{}).get("rarity_stars") is not None for x in candidate.values())==349
        assert sum(x.get("draft_scores",{}).get("taste_stars") is not None for x in candidate.values())==134
        assert sum(bool(obj.get("memo_evidence_review_v19")) for obj in taxa.values())==12
        assert sum(bool(obj.get("official_regulatory_review_v18")) for obj in taxa.values())==9
        for name,change in added.items():
            obj=candidate.get(name)
            assert obj is not None and obj["classification_status"]=="named_fish",name
            assert obj["draft_scores"]["rarity_stars"] is not None,name
            assert obj["draft_scores"]["taste_stars"] is None,"never overwrite an existing editorial star"
            assert 1<=change["taste_stars_general"]<=5 and len(change["basis"])>=6
            assert "フグ" not in name and name!="キタマクラ"
            assert not obj.get("possible_regulated_alias_needs_name_review")
            obj["draft_scores"]["taste_stars"]=change["taste_stars_general"]
            obj["taste_general_basis_v20"]=change["basis"]
            obj["taste_score_added_in_v20"]=True
        assert all(obj.get("draft_scores",{}).get("rarity_stars")==original[name].get("rarity_stars")
                   for name,obj in taxa.items()), "rarity must not change"
        assert all(obj.get("draft_scores",{}).get("taste_stars")==original[name].get("taste_stars")
                   for name,obj in taxa.items() if name not in added), "unrelated taste rating edited"
        summary={"version":"v20","method":"GENERAL_EDITORIAL_GUIDE","scientific_rarity_measure":False,
                 "food_safety_or_legality_indicator":False,"human_approved_individual_entries":0}
        master["general_star_policy_v20"]=summary
        table=io.StringIO()
        wr=csv.writer(table,lineterminator="\n")
        wr.writerow(["recorded_name","taxon_status","rarity_stars","taste_stars","taste_status","taste_basis",
                     "score_method","human_approved"])
        count={"rarity":0,"taste":0,"taste_new":0,"taxon_holds":0,"taste_no_general_baseline":0}
        for name,obj in sorted(candidate.items()):
            r=obj.get("draft_scores",{}).get("rarity_stars")
            t=obj.get("draft_scores",{}).get("taste_stars")
            hold=obj.get("classification_status")!="named_fish"
            if hold:
                assert r is None and t is None,name
                count["taxon_holds"]+=1
                status="TAXONOMY_HOLD"
            elif "フグ" in name or name=="キタマクラ":
                assert t is None,name
                status="TOXICITY_OR_FUGU_SAFETY_HOLD"
            elif t is None:
                count["taste_no_general_baseline"]+=1
                status="NO_GENERAL_CULINARY_RATING"
            else:status="GENERAL_CULINARY_EDITORIAL"
            if r is not None:count["rarity"]+=1
            if t is not None:count["taste"]+=1
            if name in added:count["taste_new"]+=1
            obj["general_star_review_v20"]={
                "score_method":"GENERAL_EDITORIAL_ESTIMATE_NOT_SCIENTIFIC",
                "rarity_is_not_red_list_status":True,
                "taste_is_not_a_food_safety_claim":True,
                "taste_status":status,
                "human_approved":False,
            }
            wr.writerow([name,obj["classification_status"],r if r is not None else "",
                      t if t is not None else "",status,obj.get("taste_general_basis_v20",""),
                      "GENERAL_EDITORIAL_ESTIMATE_NOT_SCIENTIFIC","NO"])
        assert count["rarity"]==349 and count["taste"]==160
        assert count["taste_new"]==26 and count["taxon_holds"]==26
        assert all(not (obj.get("human_approved") is True) for obj in taxa.values())
        CSV.write_text(table.getvalue(),encoding="utf-8-sig")
        atlas["editorial_general_star_policy_v20"]="GENERAL_ESTIMATE_RESEARCH_ONLY"
        with ZipFile(ZIP,"w",compression=ZIP_DEFLATED,compresslevel=8) as out:
            for path in src.namelist():
                raw=src.read(path)
                if path=="fish_master.json":raw=encode(master)
                elif path=="atlas.json":raw=encode(atlas)
                elif path=="index.html":
                    html=raw.decode("utf-8")
                    assert "仮評価・要確認" in html,"Unexpected viewer revision"
                    html=html.replace("v0.19","v0.20")
                    html=html.replace("仮評価・要確認","★は一般的な目安・メモは草案")
                    html=html.replace("★と一言メモは、現在AIが個別に作成した<strong>編集草案（仮評価）</strong>を含みます。",
                        "★は「つりくえ！」独自の一般的な目安（暫定）です。一言メモは編集草案です。")
                    html=html.replace("研究画面内の仮評価は事実確認と人の承認を終えておらず、本番公開しません。",
                        "★は生息数・絶滅危惧度の統計ではありません。味の★は食用の安全性を示しません。個別の分類・文章や権利は審査前で、本番公開はしていません。")
                    raw=html.encode("utf-8")
                elif path=="readme_preview.txt":
                    raw=("全国河川魚類図鑑v20 研究版。一般的な出会いやすさの目安349件、味の目安160件。\n"
                         "食味の未評価は無理に埋めず、種名未確定26件の星は保留。\n"
                         "星は希少種の法的指定、食べてよい魚、食用安全性を表しません。\n"
                         "元の記録名639件と河川名グループ511件は保持。調査記録とDNA検出は区別。\n"
                         "メモ、権利、法令等の最終審査前。本番WordPressには反映していません。\n").encode("utf-8")
                out.writestr(path,raw)
            out.writestr("general_editorial_star_policy_v20.json",POLICY.read_bytes())
            out.writestr("fish_general_star_coverage_v20.csv",table.getvalue().encode("utf-8-sig"))
        with ZipFile(ZIP) as test:
            assert test.testzip() is None
            check=json.loads(test.read("fish_master.json"))
            assert len(check["taxa"])==639
            assert sum(o.get("draft_scores",{}).get("taste_stars") is not None
                       for o in check["taxa"].values())==160
        qa={**summary,"research_only":True,"source_v19_sha256":prevqa["archive_sha256"],
            "fish_source_labels":639,"river_display_groups":511,"candidate_memos":375,
            "rarity_general_stars":count["rarity"],"taste_general_stars":count["taste"],
            "new_taste_general_stars":count["taste_new"],"taxon_hold_without_stars":count["taxon_holds"],
            "taste_without_general_rating":375-count["taste"],"official_fish_flags_preserved":9,
            "v19_partial_memo_source_checks_preserved":12,"no_WordPress_or_API_changes":True,
            "zip":ZIP.name,"zip_sha256":hashlib.sha256(ZIP.read_bytes()).hexdigest()}
        QA.write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(qa,ensure_ascii=False))
if __name__=="__main__":main()
