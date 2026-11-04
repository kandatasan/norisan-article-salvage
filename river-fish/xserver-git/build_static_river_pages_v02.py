#!/usr/bin/env python3
"""Build reviewed v02 fish-evidence pages without changing river identities."""
from __future__ import annotations

from collections import defaultdict
from html import escape
import json
from pathlib import Path
import re
import shutil
from xml.etree import ElementTree


HERE = Path(__file__).resolve().parent
ROOT = HERE / "source"
DATA = ROOT / "data"
DETAIL_MINIMUM = 10
CANONICAL = "https://tsurikue.com/river-fish-atlas/"
START = "<!-- v02-static-start -->"
END = "<!-- v02-static-end -->"
SOURCE_LAYER = "fish_source_connections_v02"

STYLE = """:root{color-scheme:light;--ink:#22383a;--muted:#546a6b;--blue:#276e75;--wash:#f3f8f7;--line:#d6e5e2}
*{box-sizing:border-box}body{margin:0;background:var(--wash);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Hiragino Kaku Gothic ProN","Yu Gothic",Meiryo,sans-serif;line-height:1.75}
a{color:#12606b;text-underline-offset:3px}a:hover{color:#103f49}a:focus-visible{outline:3px solid #e9b438;outline-offset:3px}
.wrap{max-width:980px;padding:24px 18px 70px;margin:auto}header,.panel,footer{background:white;border:1px solid var(--line);border-radius:16px;padding:25px 28px;margin:0 0 18px}
nav{font-size:.85rem;color:var(--muted);margin-bottom:14px}h1{font-size:clamp(1.55rem,4vw,2.3rem);line-height:1.43;margin:0 0 12px}h2{font-size:clamp(1.18rem,3vw,1.5rem);margin:0 0 12px;line-height:1.5}h3{font-size:1.02rem;margin:0 0 8px}
p{margin:0 0 12px}.lead{font-size:1rem}.muted,small{color:var(--muted)}.chip{display:inline-block;border-radius:50px;background:#e6f3ef;color:#23575d;font-size:.78rem;font-weight:700;padding:3px 12px;margin:4px 6px 0 0}
.fish-grid{list-style:none;padding:0;margin:18px 0 0;display:grid;grid-template-columns:repeat(auto-fill,minmax(205px,1fr));gap:9px}.fish-grid li{background:#f7faf9;border:1px solid var(--line);padding:9px 12px;border-radius:9px;min-width:0;overflow-wrap:anywhere}.fish-grid b{display:block;font-size:.94rem}.fish-grid small{display:block;font-size:.74rem;line-height:1.5}
.river-list{list-style:none;padding:0;margin:8px 0;display:grid;grid-template-columns:repeat(auto-fill,minmax(215px,1fr));gap:10px}.river-list li{border:1px solid var(--line);border-radius:11px;padding:10px 13px;min-width:0;background:#fff}.river-list small{display:block;font-size:.78rem}
.note{background:#fff8e9;border-left:4px solid #d7ae52;padding:14px 17px;border-radius:6px;font-size:.87rem;margin:16px 0 0}.source{overflow-wrap:anywhere;font-size:.88rem}.pill{display:inline-block;text-decoration:none;background:#287279;color:#fff;padding:10px 18px;border-radius:9px;font-weight:750;margin:6px 10px 5px 0}.pill:hover{background:#185760;color:#fff}
footer{font-size:.83rem;color:var(--muted)}@media(max-width:560px){.wrap{padding:12px 10px 45px}header,.panel,footer{padding:19px 17px;border-radius:12px}.fish-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}.fish-grid li{padding:8px}.river-list{grid-template-columns:repeat(1,minmax(0,1fr))}}"""


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, value, *, compact: bool = False) -> None:
    kwargs = {"ensure_ascii": False, "sort_keys": False}
    text = json.dumps(value, separators=(",", ":") if compact else None,
                      indent=None if compact else 2, **kwargs)
    path.write_text(text + "\n", encoding="utf-8")


def evidence_label(record: dict) -> str:
    return {
        "A": "魚類調査記録",
        "B": "資料に掲載された生息魚",
    }[record["evidence_class"]]


def water_label(group: dict) -> str:
    if group["watershed"].startswith("水系未確認"):
        return "水系名は既存グループで未確認"
    return f"資料上の水系名：{group['watershed']}"


def unique_sources(records: list[dict]) -> list[dict]:
    found = {}
    for record in records:
        key = (record["source_id"], record["source_url"], record["source_locator"])
        found.setdefault(key, record)
    return list(found.values())


def render_page(group: dict, eligible: list[dict]) -> str:
    e = escape
    river = group["river"]
    pref = group["prefecture"]
    water = group["watershed"]
    river_id = group["navigation_target_id"]
    count = len(group["records"])
    canonical = f"{CANONICAL}river/{river_id}/"
    title = f"{pref}・{river}の魚類資料記録｜つりくえ！"
    description = (f"{pref}の{river}について、公的資料に掲載された魚名{count}件を、"
                   "根拠区分と出典付きで紹介します。")
    schema = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "url": canonical,
        "description": description,
        "isPartOf": {"@type": "WebSite", "name": "つりくえ！", "url": "https://tsurikue.com/"},
        "breadcrumb": {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "つりくえ！", "item": "https://tsurikue.com/"},
                {"@type": "ListItem", "position": 2, "name": "河川の魚類資料一覧", "item": f"{CANONICAL}river/"},
                {"@type": "ListItem", "position": 3, "name": f"{pref}・{river}", "item": canonical},
            ],
        },
    }
    fish_items = []
    for record in group["records"]:
        year = f"／調査年：{e(str(record['survey_year']))}" if record.get("survey_year") else ""
        fish_items.append(
            f"<li><b>{e(record['recorded_name'])}</b>"
            f"<small>{evidence_label(record)}（{e(record['evidence_class'])}）{year}<br>"
            f"{e(record['source_title'])}・{e(record['source_locator'])}</small></li>"
        )
    sources = []
    for record in unique_sources(group["records"]):
        sources.append(
            f'<li class="source"><a target="_blank" rel="noopener noreferrer" href="{e(record["source_url"], quote=True)}">'
            f'{e(record["source_title"])}</a>（{e(record["publisher"])}）<br>'
            f'<small>根拠箇所：{e(record["source_locator"])}／区分：{evidence_label(record)}（{e(record["evidence_class"])}）</small></li>'
        )
    related = [g for g in eligible if g["navigation_target_id"] != river_id
               and g["prefecture"] == pref and g["watershed"] == water][:4]
    related_html = "".join(
        f'<li><a href="../{e(g["navigation_target_id"])}/">{e(g["river"])}</a>'
        f'<small>{e(g["prefecture"])}／掲載魚名{len(g["records"])}件</small></li>' for g in related
    ) or '<li>同じ都道府県・水系の追加詳細ページはありません。</li>'
    return f'''<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(description, quote=True)}">
<meta name="robots" content="index,follow,max-image-preview:large">
<link rel="canonical" href="{e(canonical, quote=True)}">
<meta property="og:type" content="article"><meta property="og:title" content="{e(title, quote=True)}"><meta property="og:description" content="{e(description, quote=True)}"><meta property="og:url" content="{e(canonical, quote=True)}">
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')}</script>
<style>{STYLE}</style></head><body><div class="wrap"><header><nav><a href="https://tsurikue.com/">つりくえ！</a> › <a href="../">河川の魚類資料一覧</a> › {e(pref)}・{e(river)}</nav>
<span class="chip">{e(pref)}の公的資料</span><span class="chip">{e(water_label(group))}</span>
<h1>{e(river)}の魚類資料記録</h1><p class="lead">公的資料で「{e(river)}」に結びつけて掲載された魚名を、資料の表記のまま整理しています。</p>
<p class="muted">掲載魚名：{count}件 ／ 既存河川名グループID：{e(river_id)}</p>
<a class="pill" href="../../index.html">河川検索ツールを開く</a><a href="../">魚類資料の一覧へ</a></header>
<section class="panel"><h2>資料に掲載された魚名</h2><p>Aは魚類調査で確認・採集・観察された記録、Bは河川環境資料でその川の生息魚として明記された記述です。</p>
<ul class="fish-grid">{''.join(fish_items)}</ul>
<p class="note"><strong>読み方の注意：</strong>資料の記述を既存の河川名グループへ接続した記録です。現在の生息、河川全区間での生息、釣果を保証しません。魚名の「属」「類」や旧分類は原資料から確定種へ置き換えていません。希少種の詳細地点は掲載していません。</p></section>
<section class="panel"><h2>出典</h2><ul>{''.join(sources)}</ul><p class="muted">発行主体・資料名・根拠箇所は原資料に基づきます。元資料にない年・地点・分類は補完していません。</p></section>
<section class="panel"><h2>関連する追加資料</h2><ul class="river-list">{related_html}</ul><p><a href="../">一覧からほかの河川資料を探す</a></p></section>
<footer>追加魚類資料v02の公開審査済みA/B記録から生成しています。既存の同名河川グループとは自動統合していません。<p><a href="../">河川資料一覧</a> ／ <a href="../../index.html">日本の河川図鑑・検索ツール</a></p></footer></div></body></html>
'''


def render_index_section(groups: list[dict], eligible_ids: set[str]) -> str:
    by_pref = defaultdict(list)
    for group in groups:
        by_pref[group["prefecture"]].append(group)
    sections = []
    for pref in sorted(by_pref):
        items = []
        for group in sorted(by_pref[pref], key=lambda g: (g["watershed"], g["river"])):
            name = escape(group["river"])
            if group["navigation_target_id"] in eligible_ids:
                name = f'<a href="{escape(group["navigation_target_id"])}/">{name}</a>'
            evidence = "/".join(sorted({r["evidence_class"] for r in group["records"]}))
            fish_names = "、".join(r["recorded_name"] for r in group["records"])
            source_names = "、".join(dict.fromkeys(
                f'{r["source_title"]}（{r["publisher"]}）' for r in group["records"]
            ))
            items.append(
                f'<li data-river-group-id="{escape(group["navigation_target_id"], quote=True)}">{name}'
                f'<small>{escape(group["watershed"])}／掲載魚名{len(group["records"])}件／根拠{evidence}<br>'
                f'魚名：{escape(fish_names)}<br>資料：{escape(source_names)}</small></li>'
            )
        sections.append(f'<h3>{escape(pref)}（{len(items)}グループ）</h3><ul class="river-list">{"".join(items)}</ul>')
    return (f'{START}<section class="panel" id="additional-v02"><h2>追加調査で接続した河川資料</h2>'
            '<p>国・自治体などの公的資料から、既存の河川名グループへ新たに接続した魚名の一覧です。'
            '魚名が10件以上ある7グループは個別ページ、1〜9件の96グループはこの一覧に掲載しています。</p>'
            '<p class="note">ここでいう103グループは既存データ上の資料グループ数です。103本の実在河川を新たに確定した意味ではありません。水系未確認のグループや、同名異河川を自動統合していないグループを含みます。</p>'
            + ''.join(sections) + f'</section>{END}')


def patch_index(groups: list[dict], eligible_ids: set[str], total_pages: int) -> None:
    path = ROOT / "river/index.html"
    text = path.read_text(encoding="utf-8")
    text = re.sub(re.escape(START) + r".*?" + re.escape(END), "", text, flags=re.DOTALL)
    text = text.replace("公開資料に掲載された273グループ", f"公開資料に掲載された{total_pages}グループ")
    text = text.replace("公開資料に掲載された280グループ", f"公開資料に掲載された{total_pages}グループ")
    text = re.sub(
        r'<p>この一覧は出典付きの魚名ラベルが10件以上ある<strong>\d+資料グループ</strong>を掲載しています。\d+本の実在河川が確定したという意味ではありません。</p>',
        f'<p>この一覧は出典付きの魚名ラベルが10件以上ある<strong>{total_pages}資料グループ</strong>の個別ページを掲載しています。{total_pages}本の実在河川が確定したという意味ではありません。</p>',
        text,
    )
    section = render_index_section(groups, eligible_ids)
    if "<footer>" not in text:
        raise ValueError("river index footer marker missing")
    path.write_text(text.replace("<footer>", section + "<footer>", 1), encoding="utf-8")


def patch_sitemap(old_supplemental_ids: set[str], eligible: list[dict]) -> int:
    path = ROOT / "sitemap.xml"
    ElementTree.register_namespace("", "http://www.sitemaps.org/schemas/sitemap/0.9")
    tree = ElementTree.parse(path)
    root = tree.getroot()
    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    remove_urls = {f"{CANONICAL}river/{river_id}/" for river_id in old_supplemental_ids}
    for element in list(root):
        loc = element.find(f"{ns}loc")
        if loc is not None and loc.text in remove_urls:
            root.remove(element)
    existing = {loc.text for loc in root.findall(f".//{ns}loc")}
    for group in eligible:
        url = f"{CANONICAL}river/{group['navigation_target_id']}/"
        if url not in existing:
            node = ElementTree.SubElement(root, f"{ns}url")
            ElementTree.SubElement(node, f"{ns}loc").text = url
            existing.add(url)
    ElementTree.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)
    return len(existing)


def main() -> None:
    additions = load_json(DATA / "fish_source_connections_v02_additions.json")
    manifest_path = ROOT / "seo-build-manifest-v029.json"
    manifest = load_json(manifest_path)
    groups = additions["groups"]
    eligible = [g for g in groups if len(g["records"]) >= DETAIL_MINIMUM]
    eligible_ids = {g["navigation_target_id"] for g in eligible}
    base_pages = [p for p in manifest["generated_pages"] if p.get("source_layer") != SOURCE_LAYER]
    old_supplemental_ids = {
        p["river_id"] for p in manifest["generated_pages"] if p.get("source_layer") == SOURCE_LAYER
    }

    for river_id in old_supplemental_ids - eligible_ids:
        folder = ROOT / "river" / river_id
        if folder.is_dir():
            shutil.rmtree(folder)
    for group in eligible:
        folder = ROOT / "river" / group["navigation_target_id"]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "index.html").write_text(render_page(group, eligible), encoding="utf-8")

    total_pages = len(base_pages) + len(eligible)
    patch_index(groups, eligible_ids, total_pages)
    sitemap_count = patch_sitemap(old_supplemental_ids | eligible_ids, eligible)
    detail_ids = sorted(p.parent.name for p in (ROOT / "river").glob("*/index.html"))
    dump_json(DATA / "river_detail_page_ids_v01.json", {"schema": "river-detail-page-ids-v01", "ids": detail_ids}, compact=True)

    supplemental_pages = []
    for group in eligible:
        supplemental_pages.append({
            "river_id": group["navigation_target_id"],
            "name": group["river"],
            "watershed": group["watershed"],
            "prefecture": group["prefecture"],
            "fish_name_labels": len(group["records"]),
            "url": f"{CANONICAL}river/{group['navigation_target_id']}/",
            "source_layer": SOURCE_LAYER,
            "evidence_classes": sorted({r["evidence_class"] for r in group["records"]}),
            "source_urls": sorted({r["source_url"] for r in group["records"]}),
        })
    manifest.update({
        "release": "xserver-v0.29-seo-v02-static-20261104",
        "source": additions["release"],
        "number_of_indexable_data_groups": total_pages,
        "number_of_sitemap_urls": sitemap_count,
        "minimum_fish_label_count": DETAIL_MINIMUM,
        "eligibility": "original 273 historical survey groups plus reviewed v02 A/B groups with >= 10 published fish labels",
        "existing_json_unchanged": True,
        "current_wordpress_article_unchanged": True,
        "browser_search_app_original_code_unchanged_except_visible_listing_link": False,
        "browser_search_app_change": "detail page inventory cache key updated and expected detail page count changed from 273 to 280",
        "generated_pages": base_pages + supplemental_pages,
        "v02_supplemental_summary": {
            "source_groups": len(groups),
            "source_records": sum(len(g["records"]) for g in groups),
            "individual_detail_pages": len(eligible),
            "aggregate_list_only_groups": len(groups) - len(eligible),
            "identity_policy": "exact existing navigation_target_id; no same-name river merging",
        },
    })
    dump_json(manifest_path, manifest)
    print(json.dumps({
        "v02_groups": len(groups),
        "v02_records": sum(len(g["records"]) for g in groups),
        "new_detail_pages": len(eligible),
        "detail_pages_total": len(detail_ids),
        "sitemap_urls": sitemap_count,
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
