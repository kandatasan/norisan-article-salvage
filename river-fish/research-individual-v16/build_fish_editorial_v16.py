#!/usr/bin/env python3
"""Audit fish source labels; create explicit UNVERIFIED draft display, never a published fact."""
from pathlib import Path
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
from collections import Counter
import csv,hashlib,io,json,re
ROOT=Path(__file__).resolve().parents[1]
HERE=Path(__file__).resolve().parent
OUT=HERE/"outputs"
ORIGINAL=ROOT/"research-individual-v15"/"outputs"/"river_fish_first_static_preview_v15.zip"
QA15=ROOT/"research-individual-v15"/"outputs"/"fish_first_integrity_v15.json"
EXTRACTED=OUT/"fish_639_taxon_labels_for_editor_v16.csv"
DRAFTS=HERE/"fish_editorial_drafts_v16.csv"
NONFISH=HERE/"nonfish_source_labels_v16.txt"
ZIPPED=OUT/"river_fish_with_editorial_drafts_v16.zip"
NONFISH_TERMS=("甲殻類","カニ","貝","エビ")
UNRESOLVED_RE=re.compile(r"(?:属|科|類|sp\.?|種群|の一種|種不明|型不明|旧|系統|未記載種|または|/|／|×|飼育|改良|[（(].*型|[（(].*種|(?:^| )[AB]$|広域分布種|複数)")
def encode(o):
    return (json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode("utf-8")
def emit(archive,name,blob):
    info=ZipInfo(name,date_time=(1980,1,1,0,0,0))
    info.external_attr=0o644<<16
    info.compress_type=ZIP_DEFLATED
    archive.writestr(info,blob,compress_type=ZIP_DEFLATED,compresslevel=8)
def get_source_labels():
    with EXTRACTED.open(encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader(f))
    assert len(rows)==639
    assert len({x["recorded_name"] for x in rows})==639
    return {x["recorded_name"]:x for x in rows}
def get_nonfish(names):
    seq=[line.strip() for line in NONFISH.read_text(encoding="utf-8").splitlines()
         if line.strip() and not line.startswith("#")]
    assert len(seq)==len(set(seq))==50
    if set(seq)-set(names):raise ValueError("Non-fish exact-list label not found")
    # Avoid pattern errors like ビワヒガイ (fish) and ギンガメアジ (fish).
    assert not {"ビワヒガイ","ギンガメアジ","ズナガニゴイ","ヒガイ属"}&set(seq)
    return set(seq)
def get_drafts(names,nonfish):
    with DRAFTS.open(encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f)
        assert reader.fieldnames==["recorded_name","rarity_stars_draft","taste_stars_draft",
             "short_memo_draft","draft_status","memo_evidence_source","edibility_review_required"]
        rows=list(reader)
    assert len(rows)>=100
    found={}
    for row in rows:
        name=row["recorded_name"]
        if name in found or name not in names or name in nonfish or UNRESOLVED_RE.search(name):
            raise ValueError("Draft label not a unique, exact, named fish "+name)
        r,t=row["rarity_stars_draft"],row["taste_stars_draft"]
        if r not in "12345" or (t and t not in "12345"):raise ValueError("Draft star score invalid: "+name)
        if row["draft_status"]!="AI_EDITORIAL_DRAFT_NOT_FACT_CHECKED":
            raise ValueError("Must preserve unverified editorial status")
        if row["edibility_review_required"]!="yes":raise ValueError("Review flag missing")
        memo=row["short_memo_draft"].strip()
        if not (12<=len(memo)<=130):raise ValueError("Memo length invalid: "+name)
        found[name]={"draft_scores":{"rarity_stars":int(r),"taste_stars":int(t) if t else None},
                     "draft_memo":memo,"editorial_status":"AI_DRAFT_UNVERIFIED",
                     "star_method":"AI tentative 1-5, national rarity not source-river occurrence rate",
                     "evidence_source":row["memo_evidence_source"] or None,
                     "needs_editor_check":True,"needs_food_safety_review":True}
    return found
def main():
    OUT.mkdir(exist_ok=True)
    prior=json.loads(QA15.read_text(encoding="utf-8"))
    sha=hashlib.sha256(ORIGINAL.read_bytes()).hexdigest()
    assert sha==prior["new_archive_sha256"] and prior["distinct_verbatim_fish_name_labels_not_taxonomic_species_count"]==639
    names=get_source_labels();excluded=get_nonfish(names);drafts=get_drafts(names,excluded)
    state=Counter()
    with ZipFile(ORIGINAL) as src:
        assert src.testzip() is None
        master=json.loads(src.read("fish_master.json"))
        assert set(master["taxa"])==set(names)
        for label,obj in master["taxa"].items():
            if label in excluded:
                category="not_fish"
            elif UNRESOLVED_RE.search(label) or re.match(r"^[A-Za-z][A-Za-z\s.-]+$",label):
                category="unresolved_taxon"
            else:
                category="named_fish"
            state[category]+=1
            obj["classification_status"]=category
            if label in drafts:
                assert category=="named_fish"
                obj.update(drafts[label])
            elif category=="unresolved_taxon":
                obj["editorial_status"]="unresolved_taxon"
        atlas=json.loads(src.read("atlas.json"))
        assert len(atlas["entries"])==511
        atlas["source_name_review"]="v16 research manual fish vs nonfish name audit"
        atlas["unverified_editorial_drafts_count"]=len(drafts)
        atlas["unverified_editorial_stars_explicitly_marked"]=True
        with ZipFile(ZIPPED,"w",compression=ZIP_DEFLATED,compresslevel=8) as dest:
            for name in src.namelist():
                if name=="fish_master.json":emit(dest,name,encode(master))
                elif name=="index.html":emit(dest,name,(HERE/"viewer_fish_editorial_v16.html").read_bytes())
                elif name=="atlas.json":emit(dest,name,encode(atlas))
                elif name=="readme_preview.txt":emit(dest,name,(
                    "つりくえ！魚図鑑 v16｜研究用の仮評価プレビュー。\n"
                    "AI作成の星・メモは人の検証・利用条件の審査前であり、本番公開は禁止。\n"
                    "生物の原資料に混入した非魚類50記載名をカード表示から除外。\n"
                    "原資料は別アーカイブで保持し、これまでの魚以外のデータも削除しない。\n"
                    "ZIPを展開し、python -m http.server 8000 で起動。\n").encode("utf-8"))
                else:emit(dest,name,src.read(name))
    assert sum(state.values())==639
    assert len(drafts)==120,len(drafts)
    with ZipFile(ZIPPED) as z:
        assert z.testzip() is None
        m=json.loads(z.read("fish_master.json"))
        a=json.loads(z.read("atlas.json"))
        assert len(a["entries"])==511
        assert len(m["taxa"])==639
        assert sum(x["classification_status"]=="not_fish" for x in m["taxa"].values())==50
        assert sum(x["editorial_status"]=="AI_DRAFT_UNVERIFIED" for x in m["taxa"].values())==120
        assert all(x["rarity_stars"] is None and x["taste_stars"] is None for x in m["taxa"].values())
        assert b'classificatio' not in z.read("index.html")[:1] # only sanity, no string substitution
        assert b'classification_status==="not_fish"' in z.read("index.html")
        assert b'AI_DRAFT_UNVERIFIED' in z.read("index.html")
    qa={"version":"v16","original_archive_v15_sha256":sha,"research_only":True,
        "source_taxon_labels_before_cleanup":639,
        "source_nonfish_exact_names_excluded_from_visible_cards":state["not_fish"],
        "source_unresolved_taxon_labels_not_treated_as_confirmed_fish_species":state["unresolved_taxon"],
        "named_fish_recorded_labels_still_not_guaranteed_distinct_species":state["named_fish"],
        "provisional_unique_fish_name_labels_not_species_count":639-state["not_fish"],
        "individual_editorial_rarity_and_memo_drafts":len(drafts),
        "taste_draft_scores":sum(x["draft_scores"]["taste_stars"] is not None for x in drafts.values()),
        "all_draft_star_scores_require_human_review":True,
        "no_fabricated_source_species_identification":True,
        "original_fish_data_and_nonfish_biology_retained_in_prior_archives":True,
        "preview_archive":ZIPPED.name,"preview_bytes":ZIPPED.stat().st_size,
        "preview_sha256":hashlib.sha256(ZIPPED.read_bytes()).hexdigest(),
        "no_WordPress_or_public_API_change":True,"rights_review_before_commercial_publication":True}
    (OUT/"fish_editorial_data_quality_qa_v16.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(qa,ensure_ascii=False))
if __name__=="__main__":main()
