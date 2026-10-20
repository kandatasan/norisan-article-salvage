#!/usr/bin/env python3
"""Build fish-first atlas from SHA-verified v12; NO new biology claims or WordPress writes.
Historical fish records remain separate from environmental DNA fish signals.
Non-fish biology records are excluded from this fish-only output, but not deleted
from the parent research archive.
"""
from __future__ import annotations
import csv
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo
ROOT=Path(__file__).resolve().parents[1]
HERE=Path(__file__).resolve().parent
OUT=HERE/"outputs"
SOURCE=ROOT/"research-individual-v12"/"outputs"/"river_atlas_static_preview_v12.zip"
INTEGRITY=ROOT/"research-individual-v12"/"outputs"/"viewer_integrity_v12.json"
EDITORIAL=HERE/"fish_editorial_reviewed_v15.csv"
TARGET=OUT/"river_fish_first_static_preview_v15.zip"
COLUMNS=["recorded_taxon_label","rarity_stars","taste_stars","memo","editorial_reviewer","review_basis","protected_or_sensitive"]

def packed(name, raw):
    info=ZipInfo(name,date_time=(1980,1,1,0,0,0))
    info.external_attr=0o644<<16
    info.compress_type=ZIP_DEFLATED
    return info,raw

def enc(o):
    return (json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode("utf-8")

def ratings():
    with EDITORIAL.open(encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f)
        assert reader.fieldnames==COLUMNS,reader.fieldnames
        data={}
        for row in reader:
            n=row["recorded_taxon_label"].strip()
            if not n or n in data:raise ValueError("Blank/duplicate editorial exact label")
            if not row["editorial_reviewer"].strip() or not row["review_basis"].strip():
                raise ValueError("No evidence/reviewer for rated species label "+n)
            obj={}
            for key in ("rarity_stars","taste_stars"):
                t=row[key].strip()
                if t and (not t.isdigit() or not 1<=int(t)<=5):
                    raise ValueError("Stars must be blank or integer 1–5")
                obj[key]=int(t) if t else None
            obj["memo"]=row["memo"].strip()
            if len(obj["memo"])>135:raise ValueError("Editorial memo exceeds 135 chars")
            flag=row["protected_or_sensitive"].strip().lower()
            if flag not in ("true","false"):raise ValueError("protected_or_sensitive must be true/false")
            if flag=="true" and obj["taste_stars"] is not None:
                raise ValueError("Don't publish food score for protected/sensitive taxa")
            obj.update({"editorial_status":"reviewed","protected_or_sensitive":flag=="true",
                        "review_basis":row["review_basis"].strip()})
            data[n]=obj
        return data

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    integrity=json.loads(INTEGRITY.read_text(encoding="utf-8"))
    original_sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert original_sha==integrity["archive_sha256"]
    assert integrity["unique_research_display_name_groups"]==511
    reviewed=ratings()
    source_labels=set()
    copied_old=0
    copied_dna=0
    dna_record_count_before=0
    dna_fish_record_count=0
    rejected_nonfish=0
    live_files=[]
    with ZipFile(SOURCE) as old:
        assert old.testzip() is None
        atlas=json.loads(old.read("atlas.json"))
        assert atlas["research_display_name_groups"]==511
        assert len(atlas["entries"])==511
        linked={l["river_id"] for l in atlas["links"]}
        assert linked=={e["id"] for e in atlas["entries"]}
        with ZipFile(TARGET,"w",compression=ZIP_DEFLATED,compresslevel=8) as dest:
            def emit(name,data):
                info,raw=packed(name,data)
                dest.writestr(info,raw,compress_type=ZIP_DEFLATED,compresslevel=8)
                live_files.append(name)
            emit("index.html",(HERE/"viewer_fish_first_v15.html").read_bytes())
            emit("readme_preview.txt",("研究用｜つりくえ！ 全国河川魚類図鑑 v0.15\n"
                "ZIP展開後、同一ディレクトリから python -m http.server 8000\n"
                "魚の掲載名は調査時点の記録、DNA陽性は捕獲確認ではありません。\n"
                "511は表示名グループであり魚のいる511河川の確定数ではありません。\n"
                "本番WordPress・APIへの反映なし。研究用データの商用公開は別途権利確認。\n").encode("utf-8"))
            for e in atlas["entries"]:
                fish_path=e.get("old",{}).get("fish")
                e["old"]={"fish":fish_path} if fish_path else {}
                if fish_path:
                    if fish_path not in old.namelist():raise ValueError("Original fish category file missing")
                    blob=old.read(fish_path)
                    doc=json.loads(blob)
                    if e["kind"]=="historical_national_river_survey":
                        assert doc["schema"]=="river-category-historical-v09"
                        assert doc["river_identity"]==e["id"]
                        assert doc["category"]=="fish"
                        labels=doc["labels"]
                    else:
                        assert e["kind"]=="historical_survey_river_name_multiple_code_candidates"
                        assert doc["schema"]=="v10_provisional_river_name_only"
                        assert doc["river_label_group_key"]==e["id"] and doc["category"]=="fish"
                        labels=doc["records"]
                    for row in labels:
                        n=row["recorded_name"]
                        if not isinstance(n,str) or not n.strip():raise ValueError("Invalid original taxon name")
                        source_labels.add(n)
                    emit(fish_path,blob)
                    copied_old+=1
                if e.get("edna"):
                    doc=json.loads(old.read(e["edna"]))
                    assert doc["id"]==e["id"] and doc["not_capture_or_visual_survey"]
                    dna_record_count_before+=len(doc["records"])
                    fish=[rec for rec in doc["records"] if rec["group"]=="fish"]
                    rejected_nonfish+=len(doc["records"])-len(fish)
                    if fish:
                        for rec in fish:
                            assert rec["method"]=="eDNA"
                            n=rec["name"]
                            if not isinstance(n,str) or not n.strip():raise ValueError("Invalid DNA taxon label")
                            source_labels.add(n)
                        doc["records"]=fish
                        emit(e["edna"],enc(doc))
                        copied_dna+=1
                        dna_fish_record_count+=len(fish)
                    else:
                        e["edna"]=None
                e.pop("river_code",None) # Remove source river code; name groups not legal river identities.
            atlas["fish_only_mvp"]=True
            atlas["fish_entries_original_scope"]="original_511_research_display_name_groups_not_distinct_rivers"
            atlas["method_note"]="過去の調査に記録された魚類名と環境DNA陽性の記載を区別。DNA検出は捕獲・目視証明ではない。"
            atlas.pop("method_counts_separate",None)
            emit("atlas.json",enc(atlas))
            unreviewed=source_labels-reviewed.keys()
            if reviewed.keys()-source_labels:
                raise ValueError("Editorial taxa not found in source labels: "+str(sorted(reviewed.keys()-source_labels)[:10]))
            species_master={
                "scope":"SOURCE_RECORDED_FISH_LABELS_NOT_VALIDATED_TAXONOMIC_SPECIES",
                "research_only":True,
                "stars_policy":"ratings null until an editorial reviewer verifies evidence; rarity is national editorial rarity, not river-specific rarity",
                "taste_policy":"taste is editorial and not a safety determination; do not score protected fish",
                "taxa":{name:reviewed.get(name,{
                    "rarity_stars":None,"taste_stars":None,"memo":"",
                    "editorial_status":"unreviewed","protected_or_sensitive":None,
                    "review_basis":None}) for name in sorted(source_labels)}}
            emit("fish_master.json",enc(species_master))
    with ZipFile(TARGET) as z:
        assert z.testzip() is None
        names=z.namelist()
        assert len(names)==len(set(names))
        assert not any("/birds.json" in f or "/plants.json" in f or "/benthic_animals.json" in f for f in names)
        assert len(names)==4+copied_old+copied_dna
        saved=json.loads(z.read("atlas.json"))
        assert all(set(e["old"]).issubset({"fish"}) for e in saved["entries"])
        assert len({link["river_id"] for link in saved["links"]})==511
        for e in saved["entries"]:
            assert all(f in names for f in e["old"].values())
            assert e["edna"] is None or e["edna"] in names
        metadata=json.loads(z.read("fish_master.json"))
        assert len(metadata["taxa"])==len(source_labels)
        for obj in metadata["taxa"].values():
            assert obj["editorial_status"]=="reviewed" or (obj["rarity_stars"] is None and obj["taste_stars"] is None and not obj["memo"])
    qa={
        "version":"v15","fish_only_research_preview":True,
        "baseline_511_group_count_preserved_not_511_verified_physical_rivers":511,
        "source_v12_sha256":original_sha,
        "new_archive":TARGET.name,"new_archive_bytes":TARGET.stat().st_size,
        "new_archive_sha256":hashlib.sha256(TARGET.read_bytes()).hexdigest(),
        "fish_historical_category_packs":copied_old,
        "fish_environmental_dna_packs":copied_dna,
        "eDNA_record_groups_before_fish_filter":dna_record_count_before,
        "eDNA_fish_label_record_groups_after_filter":dna_fish_record_count,
        "eDNA_nonfish_record_groups_excluded_not_reclassified":rejected_nonfish,
        "distinct_verbatim_fish_name_labels_not_taxonomic_species_count":len(source_labels),
        "editorially_reviewed_species_labels":len(reviewed),
        "non_reviewed_rarity_and_taste_never_invented":True,
        "support_for_later_other_biology_categories_retained_in_v12":True,
        "no_WordPress_or_live_API_change":True,
        "site_reuse_rights_still_require_review":True}
    (OUT/"fish_first_integrity_v15.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(qa,ensure_ascii=False))
if __name__=="__main__":
    main()
