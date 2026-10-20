#!/usr/bin/env python3
"""Complete one-line draft coverage for all 375 candidate named-fish SOURCE LABELS.
These are AI editorial drafts, NOT checked or approved facts, and source labels
are not validated distinct taxonomic species. Never touch WordPress.
"""
from collections import Counter
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
import csv, hashlib, json, re
ROOT=Path(__file__).resolve().parents[1]
HERE=Path(__file__).resolve().parent
OUT=HERE/"outputs"
V16=ROOT/"research-individual-v16"/"outputs"/"river_fish_with_editorial_drafts_v16.zip"
V16QA=ROOT/"research-individual-v16"/"outputs"/"fish_editorial_data_quality_qa_v16.json"
V17=OUT/"river_fish_full_editorial_drafts_v17.zip"
CSV_FILES=[HERE/f"editorial_additions_0{i}_v17.csv" for i in (1,2,3)]
HEAD=["recorded_name","rarity_stars_draft","taste_stars_draft","short_memo_draft","review_status","review_source"]
# Exact source strings requiring manual taxonomy/name/variety reconciliation.
# Do not label as independently confirmed species or give separate rarity.
HOLD_ALIASES={
 "アカウオ","アメマス（エゾイワナ）","イトヨ太平洋型","エゾイワナ",
 "オオクチバス（ブラックバス）","キンギョ","コイ（イロゴイ）",
 "コイ（カガミゴイ）","コイ（ニシキゴイ）","シマドジョウ",
 "スジシマドジョウ中型種","スジハゼA","スジハゼB",
 "タウナギ（本土産）","タビラ","チカダイ","チカダイ（ナイルティラピア）",
 "チャネルキャットフイッシュ","トウヨシノボリ","ドジョウ（北朝鮮採取）",
 "ニシキゴイ","ヌメリゴチ（ネズッポ）","パロットファイヤー・シクリッド",
 "ヒメダカ","ミナミメダカ（ヒメダカを含む）","メバル"
}
def enc(o):
    return (json.dumps(o,ensure_ascii=False,separators=(",",":"),sort_keys=True)+"\n").encode("utf-8")
def emit(z,name,blob):
    info=ZipInfo(name,date_time=(1980,1,1,0,0,0))
    info.external_attr=0o644<<16
    info.compress_type=ZIP_DEFLATED
    z.writestr(info,blob,compress_type=ZIP_DEFLATED,compresslevel=8)
def parse_stars(s,name,field):
    s=s.strip()
    if not s:return None
    if s not in ("1","2","3","4","5"):
        raise ValueError("Out-of-range star draft "+name+" "+field)
    return int(s)
def read_more():
    result={}
    batch_counts={}
    for file in CSV_FILES:
        if not file.exists():raise FileNotFoundError(file)
        with file.open(encoding="utf-8",newline="") as fp:
            reader=csv.DictReader(fp)
            assert reader.fieldnames==HEAD,reader.fieldnames
            rows=list(reader)
        batch_counts[file.name]=len(rows)
        for row in rows:
            name=row["recorded_name"].strip()
            if not name or name in result:raise ValueError("Missing or duplicated fish source label "+name)
            if row["review_status"]!="AI_DRAFT_UNVERIFIED" or row["review_source"]:
                raise ValueError("No fact checking to be implied at draft stage: "+name)
            memo=row["short_memo_draft"].strip()
            if not 14<=len(memo)<=150:raise ValueError("Unsuitable memo length "+name)
            stars={key:parse_stars(row[c],name,c) for c,key in (("rarity_stars_draft","rarity_stars"),("taste_stars_draft","taste_stars"))}
            if name in HOLD_ALIASES and any(score is not None for score in stars.values()):
                raise ValueError("Name needing taxonomy resolution cannot have stars "+name)
            if ("フグ" in name or name=="キタマクラ") and stars["taste_stars"] is not None:
                raise ValueError("Poisonous fish food score is unsafe: "+name)
            result[name]={"draft_scores":stars,"draft_memo":memo,
                         "editorial_status":"AI_DRAFT_UNVERIFIED",
                         "evidence_source":None,"needs_editor_check":True,
                         "needs_food_safety_review":True,
                         "star_method":"provisional editorial stars, not derived from river sighting counts"}
    assert len(result)==255,(len(result),batch_counts)
    return result,batch_counts
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    additions,bc=read_more()
    audited=json.loads(V16QA.read_text(encoding="utf-8"))
    oldsha=hashlib.sha256(V16.read_bytes()).hexdigest()
    assert oldsha==audited["preview_sha256"]
    with ZipFile(V16) as old:
        assert old.testzip() is None
        master=json.loads(old.read("fish_master.json"))
        atlas=json.loads(old.read("atlas.json"))
        assert len(master["taxa"])==639 and len(atlas["entries"])==511
        original_drafts={name for name,row in master["taxa"].items()
            if row["editorial_status"]=="AI_DRAFT_UNVERIFIED"}
        assert len(original_drafts)==120
        named={name for name,row in master["taxa"].items()
            if row["classification_status"]=="named_fish"}
        assert len(named)==375
        if set(additions)&original_drafts:raise ValueError("Draft record overwritten")
        if set(additions)!=named-original_drafts:
            raise ValueError("Unaccounted source label(s): "+
                repr(sorted((named-original_drafts)^set(additions))[:24]))
        assert HOLD_ALIASES<=set(additions)
        for name,new in additions.items():
            obj=master["taxa"][name]
            assert obj["classification_status"]=="named_fish"
            assert obj["rarity_stars"] is None and obj["taste_stars"] is None
            obj.update(new)
            if name in HOLD_ALIASES:
                obj["classification_status"]="unresolved_taxon"
                obj["editorial_treatment"]="source_alias_variety_or_taxonomic_hold_not_counted_as_independent_species"
        # Audit: all original 120 are untouched, 50 nonfish excluded, other 214 are unresolved.
        assert sum(x["classification_status"]=="not_fish" for x in master["taxa"].values())==50
        assert sum(x["editorial_status"]=="AI_DRAFT_UNVERIFIED" for x in master["taxa"].values())==375
        assert all(x["rarity_stars"] is None and x["taste_stars"] is None
                   for x in master["taxa"].values())
        atlas["editorial_v17_full_source_named_candidate_memos"]=375
        atlas["fish_editorial_work_is_still_unverified"]=True
        with ZipFile(V17,"w",compression=ZIP_DEFLATED,compresslevel=8) as dest:
            for filename in old.namelist():
                blob=old.read(filename)
                if filename=="fish_master.json":
                    blob=enc(master)
                elif filename=="atlas.json":
                    blob=enc(atlas)
                elif filename=="index.html":
                    text=blob.decode("utf-8")
                    text=text.replace("v0.16","v0.17")
                    text=text.replace("種名未確定・星評価なし","種名・別名の確認待ち（星評価なし）")
                    blob=text.encode("utf-8")
                elif filename=="readme_preview.txt":
                    blob=("魚図鑑 v17｜魚名の一言メモ375件、すべて未検証のAI編集草案。\n"
                          "魚名639件=確定魚種数ではありません。非魚類50・分類不確定名称は区別。\n"
                          "現行の独自レア度・味は仮評価。許諾・生態・食味は別途確認。\n"
                          "過去調査と環境DNA陽性は同一視しない。WordPressには未公開。\n"
                          "展開したディレクトリで python -m http.server 8000 を実行。\n").encode("utf-8")
                emit(dest,filename,blob)
    with ZipFile(V17) as check:
        assert check.testzip() is None
        saved=json.loads(check.read("fish_master.json"))
        idx=json.loads(check.read("atlas.json"))
        assert len(idx["entries"])==511
        assert len(saved["taxa"])==639
        assert sum(bool(v.get("draft_memo")) for v in saved["taxa"].values())==375
        assert sum(v["classification_status"]=="not_fish" for v in saved["taxa"].values())==50
        assert all(v["taste_stars"] is None and v["rarity_stars"] is None for v in saved["taxa"].values())
        assert all(saved["taxa"][k]["draft_scores"]["rarity_stars"] is None for k in HOLD_ALIASES)
        assert "DNA検出" in check.read("index.html").decode("utf-8")
    qa={
        "version":"v17","scope":"RESEARCH_ONLY_ALL_AI_EDITORIAL_DRAFTS_UNVERIFIED",
        "v16_archive_sha256":oldsha,
        "source_names_total_not_distinct_fish_species":639,
        "nonfish_exact_names_suppressed":50,
        "initial_unresolved_or_nonspecies_names":214,
        "additional_manually_held_alias_variety_taxonomy_names":len(HOLD_ALIASES),
        "named_fish_candidate_labels_before_manual_hold":375,
        "individual_one_line_memo_drafts_total":375,
        "initial_existing_memo_drafts":120,
        "new_memo_drafts_added":len(additions),
        "new_additions_batches":bc,
        "draft_rarity_star_scores_total":sum(o.get("draft_scores",{}).get("rarity_stars") is not None
              for o in master["taxa"].values()),
        "draft_taste_star_scores_total":sum(o.get("draft_scores",{}).get("taste_stars") is not None
              for o in master["taxa"].values()),
        "human_approved_editorial_count":0,
        "all_stars_marked_provisional":True,
        "conservation_law_and_edibility_audit_incomplete":True,
        "underlying_511_river_name_groups_unchanged":True,
        "original_older_nonfish_data_unmodified":True,
        "no_production_WordPress_or_API_change":True,
        "rights_check_required_before_commercial_publication":True,
        "zip_file":V17.name,"zip_bytes":V17.stat().st_size,
        "zip_sha256":hashlib.sha256(V17.read_bytes()).hexdigest(),
    }
    (OUT/"fish_editorial_coverage_qa_v17.json").write_text(
        json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(qa,ensure_ascii=False))
if __name__=="__main__":main()
