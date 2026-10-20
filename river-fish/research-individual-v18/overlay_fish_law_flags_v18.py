#!/usr/bin/env python3
"""Official fish legal-status names overlays for the fish atlas; scope-limited exact matches.
Source lists independently verified as of 2026-10-20. Not a substitute for
taxonomic legal review, region-specific fishery law, or edible-fish guidance.
"""
from pathlib import Path
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
HERE=Path(__file__).resolve().parent
OUT=HERE/"outputs"
V17=ROOT/"research-individual-v17"/"outputs"/"river_fish_full_editorial_drafts_v17.zip"
V17QA=ROOT/"research-individual-v17"/"outputs"/"fish_editorial_coverage_qa_v17.json"
ZIPPED=OUT/"river_fish_editorial_with_official_flags_v18.zip"
ENV_INV="https://www.env.go.jp/nature/intro/2outline/list.html"
ENV_NEW="https://www.env.go.jp/press/press_05633.html"
ENV_RARE="https://www.env.go.jp/nature/kisho/domestic/list.html"
ENV_RL="https://www.env.go.jp/nature/kisho/hozen/redlist/index.html"
# Exact labels, NOT fuzzy matches. No status inferred from substring or eDNA data.
# Atractosteus spatula is regulated via "ガー科の全種" listing.
INVASIVE={
 "アリゲーターガー":(ENV_INV,"ガー科全種の指定対象"),
 "オオタナゴ":(ENV_INV,"特定外来生物（魚類）"),
 "コウライギギ":(ENV_INV,"特定外来生物（魚類）"),
 "チャネルキャットフィッシュ":(ENV_INV,"特定外来生物（魚類）"),
 "カダヤシ":(ENV_INV,"特定外来生物（魚類）"),
 "ブルーギル":(ENV_INV,"特定外来生物（魚類）"),
 "コクチバス":(ENV_INV,"特定外来生物（魚類）"),
 "オオクチバス":(ENV_INV,"特定外来生物（魚類）"),
 "コウライオヤニラミ":(ENV_NEW,"特定外来生物（2026年9月1日指定）"),
}
# Official 2025-02 domestic rare list; source confirmed no exact species label
# is present in the current 639-name corpus. Still do not mark all fish safe.
DOMESTIC_RARE_FISH={
 "ハカタスジシマドジョウ","タンゴスジシマドジョウ","アユモドキ",
 "イタセンパラ","セボシタビラ","ゼニタナゴ","カワバタモロコ",
 "シナイモツゴ","スイゲンゼニタナゴ","ミヤコタナゴ",
 "コシノハゼ","アリアケヒメシラウオ"}
# These words are ambiguous original aliases/variants, not directly verified names.
ALIAS_PENDING={"オオクチバス（ブラックバス）":"オオクチバス",
               "チャネルキャットフイッシュ":"チャネルキャットフィッシュ"}
# Conservative editorial priority queue; presence DOES NOT imply a given
# current Red List category. Need original species-level match and experts.
CONSERVATION_REVIEW={
 "オヤニラミ","キタドジョウ","ギバチ","ホトケドジョウ",
 "ミナミスナヤツメ","キタスナヤツメ","イシカワシラウオ",
 "ニホンウナギ","ビワコオオナマズ","オオウナギ"}
def encode(o):
    return (json.dumps(o,ensure_ascii=False,separators=(",",":"),sort_keys=True)+"\n").encode("utf-8")
def emit(z,name,raw):
    info=ZipInfo(name,date_time=(1980,1,1,0,0,0))
    info.external_attr=0o644<<16
    info.compress_type=ZIP_DEFLATED
    z.writestr(info,raw,compress_type=ZIP_DEFLATED,compresslevel=8)
def main():
    OUT.mkdir(exist_ok=True,parents=True)
    prior=json.loads(V17QA.read_text(encoding="utf-8"))
    sha=hashlib.sha256(V17.read_bytes()).hexdigest()
    assert sha==prior["zip_sha256"]
    with ZipFile(V17) as z:
        assert z.testzip() is None
        atlas=json.loads(z.read("atlas.json"))
        master=json.loads(z.read("fish_master.json"))
        taxa=master["taxa"]
        assert len(atlas["entries"])==511 and len(taxa)==639
        assert set(INVASIVE)<=set(taxa),sorted(set(INVASIVE)-set(taxa))
        assert set(ALIAS_PENDING)<=set(taxa)
        assert set(CONSERVATION_REVIEW)<=set(taxa)
        rare_match=set(taxa)&DOMESTIC_RARE_FISH
        # Do not infer that older broader source labels exclude designated species.
        for label,obj in taxa.items():
            obj["official_regulatory_review_v18"]=None
            obj["legal_taxonomy_needs_review"]=bool(obj["classification_status"]=="unresolved_taxon")
            if label in INVASIVE:
                source,status=INVASIVE[label]
                obj["official_regulatory_review_v18"]={
                    "status":"SOURCE_EXACT_NAME_MATCH_ONLY",
                    "legal_category":status,"reference_url":source,
                    "checked_on":"2026-10-20",
                    "note":"外来生物法の指定対象。飼養・運搬・放流等の規制を確認してください"}
                obj["legal_taxonomy_needs_review"]=True
            if label in rare_match:
                obj["official_domestic_rare_name_match_v18"]={
                   "status":"SOURCE_EXACT_NAME_MATCH_ONLY",
                   "reference_url":ENV_RARE,
                   "note":"国内希少野生動植物種への該当を確認。採捕・譲渡等の規制を要確認"}
                obj["legal_taxonomy_needs_review"]=True
            if label in ALIAS_PENDING:
                obj["possible_regulated_alias_needs_name_review"]={
                    "match_candidate":ALIAS_PENDING[label],
                    "reference_url":ENV_INV,
                    "status":"NOT_LEGALLY_IDENTIFIED_PENDING_ALIAS_REVIEW"}
                obj["legal_taxonomy_needs_review"]=True
            if label in CONSERVATION_REVIEW:
                obj["environmental_conservation_review_priority"]=True
                obj["review_reference_url"]=ENV_RL
                # Add no unsupported "EN", "CR" or "VU" categories.
        atlas["research_official_flag_review_v18"]=True
        with ZipFile(ZIPPED,"w",compression=ZIP_DEFLATED,compresslevel=8) as out:
            for filename in z.namelist():
                content=z.read(filename)
                if filename=="fish_master.json":content=encode(master)
                elif filename=="atlas.json":content=encode(atlas)
                elif filename=="index.html":
                    html=content.decode("utf-8")
                    html=html.replace("v0.17","v0.18")
                    html=html.replace(
                        'const draft=editorial?.editorial_status==="AI_DRAFT_UNVERIFIED";',
                        'const draft=editorial?.editorial_status==="AI_DRAFT_UNVERIFIED";\n'
                        ' if(editorial?.official_regulatory_review_v18){\n'
                        '  const law=editorial.official_regulatory_review_v18;\n'
                        '  const warning=node("p","⚠ "+law.legal_category+"。"+law.note,"notice");\n'
                        '  card.appendChild(warning)\n'
                        ' }\n'
                        ' if(editorial?.possible_regulated_alias_needs_name_review){\n'
                        '  card.appendChild(node("p","規制対象の別名・表記揺れの可能性。種名を確認中。","note"))\n'
                        ' }\n'
                        ' if(editorial?.environmental_conservation_review_priority){\n'
                        '  card.appendChild(node("p","保全情報の確認を優先中（正式な指定区分は未記載）。","note"))\n'
                        ' }'
                    )
                    assert "official_regulatory_review_v18" in html
                    content=html.encode("utf-8")
                elif filename=="readme_preview.txt":
                    content=("全国河川魚類図鑑 v18｜研究専用。\n"
                        "375件の編集草案は未校閲、349件のレア度と134件の味は仮評価。\n"
                        "環境省の2026年10月時点の特定外来生物等の確認リストで部分照合。\n"
                        "国内希少指定種の一覧とは完全一致0でも、指定種が存在しないと断定しない。\n"
                        "生き物と環境DNAの別、希少種情報、出典・利用条件は要確認。\n"
                        "商用公開は未許可、WordPressに未反映。\n").encode("utf-8")
                emit(out,filename,content)
    with ZipFile(ZIPPED) as z:
        assert z.testzip() is None
        d=json.loads(z.read("fish_master.json"))
        assert len(d["taxa"])==639
        assert sum(x["official_regulatory_review_v18"] is not None for x in d["taxa"].values())==len(INVASIVE)
        assert not any(x.get("official_domestic_rare_name_match_v18") for x in d["taxa"].values()) or rare_match
        assert len(z.read("atlas.json"))>0
        html=z.read("index.html").decode()
        assert "外来生物法の指定対象" not in html # live generated from JSON
        assert 'official_regulatory_review_v18' in html
    qa={"version":"v18","source_v17_sha256":sha,
        "research_only":True,"site_fish_name_labels_not_verified_species":639,
        "draft_memos_unreviewed":375,
        "fish_source_exact_matches_to_official_invasive_species_list":len(INVASIVE),
        "domestic_rare_exact_name_matches_current_source_names":len(rare_match),
        "domestic_rare_absence_is_not_exhaustive_species_clearance":True,
        "invasive_source":ENV_INV,"2026_new_invasive_source":ENV_NEW,
        "domestic_rare_source":ENV_RARE,"conservation_review_source":ENV_RL,
        "source_name_aliases_held_for_regulatory_review":len(ALIAS_PENDING),
        "other_conservation_priority_labels":len(CONSERVATION_REVIEW),
        "all_original_draft_scores_remain_provisional":True,
        "no_conservation_status_assumed_from_rarity_stars":True,
        "no_WordPress_or_live_API_mutation":True,
        "zip":ZIPPED.name,"zip_bytes":ZIPPED.stat().st_size,
        "zip_sha256":hashlib.sha256(ZIPPED.read_bytes()).hexdigest()}
    (OUT/"official_fish_law_scope_qa_v18.json").write_text(
       json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(qa,ensure_ascii=False))
if __name__=="__main__":main()
