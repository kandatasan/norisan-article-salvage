#!/usr/bin/env python3
"""Research-only v19 overlay: preserve v18, partial primary-source memo audit."""
import csv
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
V18 = ROOT / "research-individual-v18" / "outputs" / "river_fish_editorial_with_official_flags_v18.zip"
V18QA = ROOT / "research-individual-v18" / "outputs" / "official_fish_law_scope_qa_v18.json"
OUT = HERE / "outputs"
EVIDENCE = HERE / "memo_primary_source_checks_v19.json"
ZIP = OUT / "river_fish_evidence_review_v19.zip"
QUEUE = OUT / "fish_editorial_review_queue_v19.csv"
QA = OUT / "fish_editorial_evidence_qa_v19.json"

def dump(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")

def main():
    OUT.mkdir(exist_ok=True)
    original_qa = json.loads(V18QA.read_text(encoding="utf-8"))
    assert hashlib.sha256(V18.read_bytes()).hexdigest() == original_qa["zip_sha256"], "v18 SHA mismatch"
    reviews = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert reviews["editor_human_approved_count"] == 0
    edits = {x["recorded_name"]: x for x in reviews["memo_revisions"]}
    assert len(edits) == len(reviews["memo_revisions"]) == 12
    with ZipFile(V18, "r") as z:
        assert z.testzip() is None
        master = json.loads(z.read("fish_master.json"))
        atlas = json.loads(z.read("atlas.json"))
        taxa = master["taxa"]
        assert len(taxa) == 639 and len(atlas["entries"]) == 511
        old_scores = {name: (obj["draft_scores"].copy() if obj.get("draft_scores") else None)
                      for name, obj in taxa.items()}
        new_edit_count = 0
        for name, record in edits.items():
            assert name in taxa and taxa[name].get("editorial_status") == "AI_DRAFT_UNVERIFIED", name
            assert record["source"].startswith("https://") and record["memo"] and record["check"]
            obj = taxa[name]
            obj["draft_memo_previous_v18"] = obj["draft_memo"]
            obj["draft_memo"] = record["memo"]
            obj["memo_evidence_review_v19"] = {
                "check": record["check"],
                "reference_url": record["source"],
                "review_stage": "AI_PARTIAL_PRIMARY_SOURCE_CROSS_CHECK_NOT_HUMAN_APPROVED",
                "checked_on": reviews["checked_on"],
            }
            new_edit_count += 1
        assert all((obj["draft_scores"] if obj.get("draft_scores") else None) == old_scores[name]
                   for name, obj in taxa.items()), "draft stars must be untouched"
        candidates = [(name, obj) for name, obj in taxa.items()
                      if obj.get("editorial_status") == "AI_DRAFT_UNVERIFIED"]
        assert len(candidates) == 375
        assert sum(obj.get("draft_scores", {}).get("rarity_stars") is not None
                   for _, obj in candidates) == 349
        assert sum(obj.get("draft_scores", {}).get("taste_stars") is not None
                   for _, obj in candidates) == 134
        assert sum(obj.get("official_regulatory_review_v18") is not None
                   for obj in taxa.values()) == 9
        assert all(obj.get("human_approved") is not True for obj in taxa.values())
        sio = io.StringIO()
        writer = csv.writer(sio, lineterminator="\n")
        writer.writerow(["recorded_name","review_priority","reason","rarity_draft","taste_draft",
                         "rarity_evidence","taste_evidence","memo_source","human_approved"])
        priority_counts = {"P0":0,"P1":0,"P2":0}
        for name, obj in sorted(candidates, key=lambda x:x[0]):
            stars = obj.get("draft_scores", {})
            poison_name = ("フグ" in name or name == "キタマクラ")
            law = bool(obj.get("official_regulatory_review_v18") or
                       obj.get("possible_regulated_alias_needs_name_review"))
            conservation = bool(obj.get("environmental_conservation_review_priority"))
            if law or poison_name:
                priority, reason = "P0", "LEGAL_OR_POTENTIAL_TOXIC_FISH_REVIEW"
            elif conservation or stars.get("taste_stars") is not None:
                priority, reason = "P1", "CONSERVATION_OR_TASTE_EVIDENCE_REVIEW"
            else:
                priority, reason = "P2", "TAXONOMY_MEMO_AND_RARITY_EVIDENCE_REVIEW"
            priority_counts[priority] += 1
            evidence = obj.get("memo_evidence_review_v19") or {}
            writer.writerow([name, priority, reason,
                            stars.get("rarity_stars") if stars.get("rarity_stars") is not None else "",
                            stars.get("taste_stars") if stars.get("taste_stars") is not None else "",
                            "NOT_ASSESSED", "NOT_ASSESSED",
                            evidence.get("reference_url",""), "NO"])
        QUEUE.write_text(sio.getvalue(), encoding="utf-8-sig")
        atlas["research_editorial_evidence_review_v19"] = True
        with ZipFile(ZIP, "w", compression=ZIP_DEFLATED, compresslevel=8) as out:
            for filename in z.namelist():
                raw = z.read(filename)
                if filename == "fish_master.json":
                    raw = dump(master)
                elif filename == "atlas.json":
                    raw = dump(atlas)
                elif filename == "index.html":
                    page = raw.decode("utf-8").replace("v0.18","v0.19")
                    needle = 'const draft=editorial?.editorial_status==="AI_DRAFT_UNVERIFIED";'
                    assert page.count(needle) == 1, "HTML injection location changed"
                    page = page.replace(needle, needle + "\n if(editorial?.memo_evidence_review_v19){card.appendChild(node(\"p\",\"一言メモの一部を公的資料と照合済み（最終承認前）。\",\"note\"));}")
                    raw = page.encode("utf-8")
                out.writestr(filename, raw)
            out.writestr("fish_editorial_review_queue_v19.csv", sio.getvalue().encode("utf-8-sig"))
            out.writestr("memo_primary_source_checks_v19.json", EVIDENCE.read_bytes())
    with ZipFile(ZIP) as z:
        assert z.testzip() is None
        check = json.loads(z.read("fish_master.json"))
        assert len(check["taxa"]) == 639
        assert sum(bool(obj.get("memo_evidence_review_v19")) for obj in check["taxa"].values()) == 5
        assert 'memo_evidence_review_v19' in z.read("index.html").decode("utf-8")
    qa = {"version":"v19","research_only":True,
          "based_on_v18_zip_sha256":original_qa["zip_sha256"],
          "source_name_labels":639,"fish_draft_memos":375,"memo_primary_source_partial_cross_checks":new_edit_count,
          "human_approved_memos":0,"rarity_draft_stars_unchanged":349,
          "taste_draft_stars_unchanged":134,
          "score_supporting_evidence_verified":0,
          "priority_count":priority_counts,
          "no_WordPress_or_production_changes":True,
          "archive":ZIP.name,"archive_sha256":hashlib.sha256(ZIP.read_bytes()).hexdigest()}
    QA.write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(qa,ensure_ascii=False))

if __name__ == "__main__":
    main()
