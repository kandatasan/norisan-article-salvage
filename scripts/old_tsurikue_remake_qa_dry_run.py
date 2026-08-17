#!/usr/bin/env python3
"""Phase 3.1 editorial QA for the 46 old-tsurikue remake artifacts.

Local-only. It regenerates the formal Phase 3 artifacts in a temporary
directory, validates the baseline, and then applies conservative cleanup.
There is no network or WordPress write path.
"""
from __future__ import annotations

import argparse
import csv
import difflib
import html
import json
import re
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

import old_tsurikue_remake_dry_run as phase3

EXPECTED_TARGETS = 46
EXPECTED_SHORT_UNDER_800 = 11
EXPECTED_MATCHED = 110
EXPECTED_PLACEHOLDERS = 29
EXPECTED_OMITTED = 224
WARN_REDUCTION = 0.25
FAIL_REDUCTION = 0.50

GENERIC_STALE_NOTICE = (
    "営業時間・料金・商品仕様などは変更されている場合があります。"
    "利用前に最新の公式情報も確認してください。"
)
BANNED_OUTPUT = ("web.archive.org", "lexus-diary.com", "<script", "<style")
REASONS = ("duplicate", "affiliate", "stale_operational", "work_in_progress", "other")

BROKEN_PRODUCT_PATTERNS = (
    re.compile(r"^価格[:：]\s*[\d,]+円.*時点.*感想\(\d+件\)$"),
    re.compile(r"^【?あす楽対応\s+全国送料無料】?.*(?:GoPro|GOPRO)", re.I),
)
ADDRESS_RE = re.compile(
    r"^(?:〒?\d{3}-?\d{4}\s*)?"
    r"(?:北海道|東京都|京都府|大阪府|.{2,3}県)[^\n]{2,}$"
)
PHONE_RE = re.compile(r"^(?:\d{2,4}[ー－\-]\d{2,4}[ー－\-]\d{3,4}|0\d{8,10})$")


def strip_tags(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", value))


def visible_text(value: str) -> str:
    return re.sub(r"\s+", "", strip_tags(value))


def visible_chars(value: str) -> int:
    return len(visible_text(value))


def split_blocks(content: str) -> list[str]:
    return [x.strip() for x in re.split(r"\n\s*\n", content) if x.strip()]


def block_type(block: str) -> str:
    if "<!-- wp:image" in block:
        return "image"
    if "<!-- wp:heading" in block:
        return "heading"
    if "<!-- wp:paragraph" in block:
        return "paragraph"
    return "other"


def block_text(block: str) -> str:
    return re.sub(r"\s+", " ", strip_tags(block)).strip()


def normalize_compare(value: str) -> str:
    return re.sub(r"[\W_]+", "", html.unescape(value).lower(), flags=re.UNICODE)


def replace_visible_text(block: str, old: str, new: str) -> str:
    for src, dst in (
        (html.escape(old, quote=False), html.escape(new, quote=False)),
        (old, new),
    ):
        if src in block:
            return block.replace(src, dst)
    return block


def replace_block_text(block: str, new_text: str) -> str:
    safe = html.escape(new_text, quote=False)
    typ = block_type(block)
    if typ == "paragraph":
        return re.sub(r"<p>.*?</p>", f"<p>{safe}</p>", block, count=1, flags=re.S)
    if typ == "heading":
        return re.sub(
            r"<h([23])([^>]*)>.*?</h\1>",
            lambda m: f"<h{m.group(1)}{m.group(2)}>{safe}</h{m.group(1)}>",
            block,
            count=1,
            flags=re.S,
        )
    return block


def strip_work_marker(text: str) -> tuple[str, int]:
    out = text
    for marker in (
        "作成中です…",
        "作成中です",
        "作成中…",
        "イカ釣り実釣編に続きます。",
        "続きます…",
        "続きます。",
    ):
        out = out.replace(marker, "")
    out = out.strip()
    removed = max(0, len(re.sub(r"\s+", "", text)) - len(re.sub(r"\s+", "", out)))
    return out, removed


def is_affiliate_remnant(text: str) -> bool:
    if "楽天だとここが安かった" in text:
        return True
    return any(p.search(text) for p in BROKEN_PRODUCT_PATTERNS)


def operational_kind(text: str) -> str | None:
    if text == GENERIC_STALE_NOTICE or text.startswith("訪問当時"):
        return None
    if text == "営業時間" or text.startswith("営業時間"):
        return "営業時間"
    if text.startswith("定休日"):
        return "定休日"
    if text.startswith("電話番号"):
        return "電話番号"
    if text.startswith(("住所", "所在地")):
        return "所在地"
    if re.search(r"(宿泊料金|入場料|料金[:：])", text):
        return "料金"
    compact = text.replace(" ", "").replace("　", "")
    if PHONE_RE.match(compact):
        return "電話番号"
    if ADDRESS_RE.match(text):
        return "所在地"
    if (
        re.search(r"(通常営業|金・土曜|昼の部|夜の部|ラストオーダー)", text)
        and re.search(r"\d{1,2}[：:時].*[〜～\-－].*\d{1,2}", text)
    ):
        return "営業時間"
    return None


def reframe_operational(text: str, kind: str) -> str:
    if kind == "営業時間":
        if text == "営業時間":
            return "訪問当時の営業時間"
        return f"訪問当時の営業時間：{text}"
    if kind == "定休日":
        return f"訪問当時の{text}"
    if kind == "電話番号":
        return f"訪問当時の{text}" if text.startswith("電話番号") else f"訪問当時の電話番号：{text}"
    if kind == "所在地":
        return f"訪問当時の{text}" if text.startswith(("住所", "所在地")) else f"訪問当時の所在地：{text}"
    if kind == "料金":
        return f"訪問当時の料金に関する記録：{text}"
    return text


def apply_known_fixes(slug: str, block: str) -> tuple[str, int]:
    replacements: list[tuple[str, str]] = []
    if slug == "ramenkou":
        replacements.append(("屋根にデカデカ」と書かれた", "屋根にデカデカと書かれた"))
    if slug == "yariika-fishing":
        replacements += [
            ("0.6〜08号", "0.6〜0.8号"),
            ("この4点を意識して探してみましょう。", "この2点を意識して探してみましょう。"),
            ("かなり猪突猛進な正確をしていて", "かなり猪突猛進な性格をしていて"),
            ("変えたて新鮮の塩漬けササミ", "替えたての新鮮な塩漬けササミ"),
        ]
    if slug == "gulp-powder":
        replacements += [
            (
                "なんかね、バラバラにカットされたはずのササミから一体感が出てるの、元の1本のササミだった頃のように。",
                "なんかね、バラバラにカットされたはずのササミがネチャネチャ引っ付いて一体感が出てるの、元の1本のササミだった頃のように。",
            ),
            (
                "そのおかげで、ハードルアーにも味と匂いとヌメリを付与させることができるのですね。",
                "そのおかげで、プラグやシンカーなどのハードルアーにも味と匂いとヌメリを付与させることができるのですね。",
            ),
        ]
    fixes = 0
    for old, new in replacements:
        changed = replace_visible_text(block, old, new)
        if changed != block:
            block = changed
            fixes += 1
    return block, fixes


def duplicate_of_seen(text: str, seen: list[str]) -> bool:
    current = normalize_compare(text)
    if len(current) < 50:
        return False
    for previous in seen:
        if len(previous) < 50:
            continue
        if difflib.SequenceMatcher(None, current, previous).ratio() >= 0.94:
            return True
    return False


def cleanup_article(article: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    slug = article["slug"]
    before_content = article["content"]
    before_chars = visible_chars(before_content)
    original_media_ids = list(article.get("matched_media_ids") or [])
    original_media_urls = list(article.get("matched_media_source_urls") or [])
    original_placeholders = list(article.get("placeholders") or [])
    original_omitted = list(article.get("omitted_photo_positions") or [])

    deleted_blocks = Counter()
    deleted_chars = Counter()
    text_fixes = 0
    stale_reframed = 0
    seen_paragraphs: list[str] = []
    result: list[str] = []

    for block in split_blocks(before_content):
        typ = block_type(block)
        text = block_text(block)

        if slug == "matthewoishii" and typ == "heading" and text == "メニューは日替わり系も豊":
            deleted_blocks["duplicate"] += 1
            deleted_chars["duplicate"] += visible_chars(block)
            text_fixes += 1
            continue

        if text in ("…", "...", "・・・", "…？", "…！"):
            deleted_blocks["work_in_progress"] += 1
            deleted_chars["work_in_progress"] += visible_chars(block)
            text_fixes += 1
            continue

        if any(x in text for x in ("作成中です", "作成中…", "続きます。", "続きます…")):
            kept, removed = strip_work_marker(text)
            deleted_blocks["work_in_progress"] += 1
            deleted_chars["work_in_progress"] += removed
            text_fixes += 1
            if not kept:
                continue
            block = replace_block_text(block, kept)
            text = kept

        if typ == "paragraph" and text.startswith("このブログにはPRが含まれています"):
            kept = re.sub(r"^このブログにはPRが含まれています。[ 　]*", "", text).strip()
            deleted_blocks["affiliate"] += 1
            deleted_chars["affiliate"] += len("このブログにはPRが含まれています。")
            if not kept:
                continue
            block = replace_block_text(block, kept)
            text = kept

        if typ == "paragraph" and is_affiliate_remnant(text):
            deleted_blocks["affiliate"] += 1
            deleted_chars["affiliate"] += visible_chars(block)
            continue

        block, fixes = apply_known_fixes(slug, block)
        text_fixes += fixes
        text = block_text(block)

        if typ == "paragraph":
            kind = operational_kind(text)
            if kind:
                block = replace_block_text(block, reframe_operational(text, kind))
                text = block_text(block)
                stale_reframed += 1

        if typ == "paragraph":
            if duplicate_of_seen(text, seen_paragraphs):
                deleted_blocks["duplicate"] += 1
                deleted_chars["duplicate"] += visible_chars(block)
                continue
            seen_paragraphs.append(normalize_compare(text))

        result.append(block)

    # Multi-source join: merge useful wording into the completed first account,
    # then remove the repeated second account.
    if slug == "gulp-powder":
        merged: list[str] = []
        completion_heading_seen = False
        completion_paragraph_kept = False
        for block in result:
            text = block_text(block)
            if completion_heading_seen and completion_paragraph_kept:
                if block_type(block) == "image":
                    merged.append(block)
                else:
                    reason = "affiliate" if is_affiliate_remnant(text) else "duplicate"
                    deleted_blocks[reason] += 1
                    deleted_chars[reason] += visible_chars(block)
                continue
            merged.append(block)
            if block_type(block) == "heading" and text == "完成！ガルプササミ":
                completion_heading_seen = True
            elif completion_heading_seen and block_type(block) == "paragraph":
                completion_paragraph_kept = True
        result = merged

    # Multi-source join: after the real conclusion a shorter copy starts again.
    if slug == "totoya-iiyo":
        merged = []
        summary_seen = False
        cut_tail = False
        for block in result:
            text = block_text(block)
            if cut_tail:
                if block_type(block) == "image":
                    merged.append(block)
                else:
                    reason = "affiliate" if "コチラ" in text else "duplicate"
                    deleted_blocks[reason] += 1
                    deleted_chars[reason] += visible_chars(block)
                continue
            if block_type(block) == "heading" and text == "まとめ":
                summary_seen = True
            elif summary_seen and text.startswith("鳥取市にある魚と屋、ここはお手頃価格"):
                cut_tail = True
                deleted_blocks["duplicate"] += 1
                deleted_chars["duplicate"] += visible_chars(block)
                continue
            merged.append(block)
        result = merged

    # Collapse the repeated butter-cooking procedure while keeping species-
    # specific notes and firsthand tasting impressions.
    if slug == "kotamagairyouri":
        merged = []
        second_cooking = False
        collapsed = False
        for block in result:
            text = block_text(block)
            if block_type(block) == "heading" and text == "調理編":
                second_cooking = True
                merged.append(block)
                continue
            if second_cooking and not collapsed and block_type(block) == "paragraph":
                merged.append(
                    replace_block_text(
                        block,
                        "オキアサリも基本の調理手順はコタマガイと同じです。"
                        "殻をこすり合わせて砂や汚れを丁寧に落とし、バターで炒めます。"
                        "洗いが甘いと砂が残るので、ここは手を抜かないのが大事です。",
                    )
                )
                collapsed = True
                continue
            if (
                second_cooking
                and collapsed
                and block_type(block) == "paragraph"
                and (
                    text.startswith("バターをフライパンで熱して")
                    or text.startswith("バターを熱したらオキアサリを投入")
                )
            ):
                deleted_blocks["duplicate"] += 1
                deleted_chars["duplicate"] += visible_chars(block)
                continue
            merged.append(block)
        result = merged

    content = "\n\n".join(result).strip() + "\n"
    after_chars = visible_chars(content)
    reduction = 0.0 if before_chars == 0 else max(0.0, (before_chars - after_chars) / before_chars)

    lowered = content.lower()
    for bad in BANNED_OUTPUT:
        if bad in lowered:
            raise ValueError(f"{slug}: banned output {bad}")
    if "lexus" in lowered:
        raise ValueError(f"{slug}: Lexus text leaked")

    out = dict(article)
    out["content"] = content
    out["wordpress_write_count"] = 0
    out["draft_creation_count"] = 0
    out["media_upload_count"] = 0
    if list(out.get("matched_media_ids") or []) != original_media_ids:
        raise ValueError(f"{slug}: confirmed media ids changed")
    if list(out.get("matched_media_source_urls") or []) != original_media_urls:
        raise ValueError(f"{slug}: confirmed media URLs changed")
    if list(out.get("placeholders") or []) != original_placeholders:
        raise ValueError(f"{slug}: placeholder policy changed")
    if list(out.get("omitted_photo_positions") or []) != original_omitted:
        raise ValueError(f"{slug}: omitted-photo disposition changed")

    reasons = [x for x in REASONS if deleted_blocks[x]]
    qa = {
        "slug": slug,
        "visible_chars_before": before_chars,
        "visible_chars_after": after_chars,
        "reduction_ratio": round(reduction, 6),
        "deletion_reasons": reasons,
        "deleted_blocks": int(sum(deleted_blocks.values())),
        "deleted_chars": int(sum(deleted_chars.values())),
        "deleted_blocks_by_reason": {x: int(deleted_blocks[x]) for x in REASONS},
        "deleted_chars_by_reason": {x: int(deleted_chars[x]) for x in REASONS},
        "text_fixes": text_fixes,
        "stale_operational_info_reframed": stale_reframed,
        "under_800_before": before_chars < 800,
        "under_800_after": after_chars < 800,
        "became_under_800": before_chars >= 800 and after_chars < 800,
        "requires_review_25pct": reduction >= WARN_REDUCTION,
        "fails_50pct": reduction >= FAIL_REDUCTION,
    }
    out["phase31_qa"] = qa
    return out, qa


def validate_phase3_baseline(phase3_dir: Path, report: dict[str, Any]) -> list[dict[str, Any]]:
    summary = report["summary"]
    expected = {
        "targets": EXPECTED_TARGETS,
        "lexus_targets": 0,
        "articles_generated": EXPECTED_TARGETS,
        "matched_images_used": EXPECTED_MATCHED,
        "placeholders_used": EXPECTED_PLACEHOLDERS,
        "unmatched_photos_omitted": EXPECTED_OMITTED,
        "wordpress_write_count": 0,
        "draft_creation_count": 0,
        "media_upload_count": 0,
    }
    for key, expected_value in expected.items():
        if summary.get(key) != expected_value:
            raise ValueError(
                f"Phase 3 baseline mismatch: {key}={summary.get(key)!r}, expected {expected_value!r}"
            )
    paths = sorted((phase3_dir / "articles").glob("*.json"))
    if len(paths) != EXPECTED_TARGETS:
        raise ValueError("Phase 3 baseline must contain exactly 46 article JSON files")
    articles = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    if len({article["slug"] for article in articles}) != EXPECTED_TARGETS:
        raise ValueError("Phase 3 baseline slugs must be unique")
    short = [article["slug"] for article in articles if visible_chars(article["content"]) < 800]
    if len(short) != EXPECTED_SHORT_UNDER_800:
        raise ValueError(
            f"Phase 3 short-article baseline mismatch: {len(short)}, "
            f"expected {EXPECTED_SHORT_UNDER_800}"
        )
    return articles


def write_artifacts(output_dir: Path, articles: list[dict[str, Any]], qa_rows: list[dict[str, Any]]) -> dict[str, Any]:
    article_dir = output_dir / "articles"
    article_dir.mkdir(parents=True, exist_ok=True)
    index_rows = []
    for article in articles:
        slug = article["slug"]
        (article_dir / f"{slug}.html").write_text(article["content"], encoding="utf-8")
        (article_dir / f"{slug}.json").write_text(
            json.dumps(article, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        index_rows.append({
            "slug": slug,
            "title": article["title"],
            "characters": visible_chars(article["content"]),
            "matched_images": len(article.get("matched_media_ids") or []),
            "placeholders": len(article.get("placeholders") or []),
            "omitted_photos": len(article.get("omitted_photo_positions") or []),
            "status": "QA_GENERATED",
        })

    reason_blocks = Counter()
    reason_chars = Counter()
    for row in qa_rows:
        reason_blocks.update(row["deleted_blocks_by_reason"])
        reason_chars.update(row["deleted_chars_by_reason"])

    short_before = [row["slug"] for row in qa_rows if row["under_800_before"]]
    short_after = [row["slug"] for row in qa_rows if row["under_800_after"]]
    became_short = [row["slug"] for row in qa_rows if row["became_under_800"]]
    review_25 = [row["slug"] for row in qa_rows if row["requires_review_25pct"]]
    fail_50 = [row["slug"] for row in qa_rows if row["fails_50pct"]]

    summary = {
        "targets": EXPECTED_TARGETS,
        "lexus_targets": 0,
        "articles_generated": len(articles),
        "matched_images_used": sum(len(a.get("matched_media_ids") or []) for a in articles),
        "placeholders_used": sum(len(a.get("placeholders") or []) for a in articles),
        "unmatched_photos_omitted": sum(len(a.get("omitted_photo_positions") or []) for a in articles),
        "duplicate_blocks_removed": int(reason_blocks["duplicate"]),
        "text_fixes": int(sum(row["text_fixes"] for row in qa_rows)),
        "stale_operational_info_reframed": int(sum(row["stale_operational_info_reframed"] for row in qa_rows)),
        "affiliate_remnants_removed": int(reason_blocks["affiliate"]),
        "short_articles_under_800_before": len(short_before),
        "short_articles_under_800_after": len(short_after),
        "newly_under_800": len(became_short),
        "articles_reduced_25pct_or_more": len(review_25),
        "articles_reduced_50pct_or_more": len(fail_50),
        "wordpress_write_count": 0,
        "draft_creation_count": 0,
        "media_upload_count": 0,
    }
    if summary["matched_images_used"] != EXPECTED_MATCHED:
        raise ValueError("Phase 3.1 changed confirmed image count")
    if summary["placeholders_used"] != EXPECTED_PLACEHOLDERS:
        raise ValueError("Phase 3.1 changed placeholder count")
    if summary["unmatched_photos_omitted"] != EXPECTED_OMITTED:
        raise ValueError("Phase 3.1 changed omitted-photo count")
    if len(short_before) != EXPECTED_SHORT_UNDER_800:
        raise ValueError("Phase 3.1 did not start from formal Phase 3 baseline")
    unexplained = [row["slug"] for row in qa_rows if row["became_under_800"] and not row["deletion_reasons"]]
    if unexplained:
        raise ValueError(f"new short articles without deletion reason: {unexplained}")
    if fail_50:
        raise ValueError(f"Phase 3.1 excessive reduction >=50%: {fail_50}")

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "index.json").write_text(
        json.dumps({"summary": summary, "articles": index_rows}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with (output_dir / "index.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(index_rows[0].keys()))
        writer.writeheader()
        writer.writerows(index_rows)

    qa_report = {
        "summary": summary,
        "deletion_blocks_by_reason": {x: int(reason_blocks[x]) for x in REASONS},
        "deletion_chars_by_reason": {x: int(reason_chars[x]) for x in REASONS},
        "short_articles_under_800_before": short_before,
        "short_articles_under_800_after": short_after,
        "newly_under_800": became_short,
        "review_25pct": review_25,
        "fail_50pct": fail_50,
        "articles": qa_rows,
    }
    (output_dir / "qa-report.json").write_text(
        json.dumps(qa_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    qa_lines = [
        "# Phase 3.1 本文QA dry-run", "",
        f"- targets: **{summary['targets']}**",
        f"- Lexus targets: **{summary['lexus_targets']}**",
        f"- matched images: **{summary['matched_images_used']}**",
        f"- placeholders: **{summary['placeholders_used']}**",
        f"- unmatched photos omitted: **{summary['unmatched_photos_omitted']}**",
        f"- under 800 before / after: **{len(short_before)} / {len(short_after)}**",
        f"- newly under 800: **{len(became_short)}**",
        f"- WordPress writes / drafts / media uploads: **0 / 0 / 0**",
        "", "## 25%以上減少した記事",
    ]
    if review_25:
        for row in qa_rows:
            if row["requires_review_25pct"]:
                qa_lines.append(
                    f"- `{row['slug']}`: {row['visible_chars_before']} → {row['visible_chars_after']} "
                    f"({row['reduction_ratio']:.2%}) / {', '.join(row['deletion_reasons']) or 'reason none'}"
                )
    else:
        qa_lines.append("- なし")
    qa_lines += [
        "", "## 800文字未満（入力）",
        ", ".join(f"`{x}`" for x in short_before) if short_before else "なし",
        "", "## 800文字未満（出力）",
        ", ".join(f"`{x}`" for x in short_after) if short_after else "なし",
        "", "## 削除理由別",
    ]
    for reason in REASONS:
        qa_lines.append(f"- {reason}: {reason_blocks[reason]} blocks / {reason_chars[reason]} chars")
    (output_dir / "qa-report.md").write_text("\n".join(qa_lines) + "\n", encoding="utf-8")

    summary_lines = ["# 旧つりくえ！46記事 Phase 3.1 QA dry-run", ""]
    summary_lines += [f"- {key}: **{value}**" for key, value in summary.items()]
    (output_dir / "summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    return {"summary": summary, "articles": index_rows, "qa": qa_rows}


def build(output_dir: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="old-tsurikue-phase3-") as tmp:
        phase3_dir = Path(tmp) / "formal-phase3"
        phase3_report = phase3.build(phase3_dir)
        baseline_articles = validate_phase3_baseline(phase3_dir, phase3_report)
        cleaned = []
        qa_rows = []
        for article in baseline_articles:
            out, qa = cleanup_article(article)
            cleaned.append(out)
            qa_rows.append(qa)
        return write_artifacts(output_dir, cleaned, qa_rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path("reports/old-tsurikue-remake-qa-dry-run"),
    )
    args = parser.parse_args()
    report = build(args.output_dir)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
