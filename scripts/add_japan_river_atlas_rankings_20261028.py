#!/usr/bin/env python3
"""Guarded addition of three ranking tables to published river atlas post 4240.

PR: authenticated read-only preflight. Main: insert one Gutenberg section only.
Fail closed when WordPress changed, so photos, inline tool, and 47-prefecture
directory remain byte-for-byte identical. Never touch the static atlas deploy.
"""
from __future__ import annotations
import base64
import hashlib
import html
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

BASE = "https://tsurikue.com"
POST_ID = 4240
SPEC = Path("content/revisions/japan-river-atlas-rankings-20261028.json")
MARKER = "tsurikue-river-rankings-20261028"
ANCHOR = ('<!-- wp:heading -->\n'
          '<h2 class="wp-block-heading">川好きの原点は、祖父と釣った「ヤマメ」</h2>\n'
          '<!-- /wp:heading -->')
HEAD = '<!-- wp:heading -->\n<h2 class="wp-block-heading">日本の川ランキング｜長さ・流域面積・水質を比較</h2>\n<!-- /wp:heading -->'
def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
def esc(s):
    return html.escape(str(s), quote=True)
def paragraph(s):
    return '<!-- wp:paragraph -->\n<p>' + s + '</p>\n<!-- /wp:paragraph -->'
def h3(s):
    return '<!-- wp:heading {"level":3} -->\n<h3 class="wp-block-heading">' + esc(s) + '</h3>\n<!-- /wp:heading -->'
def link(name):
    return ('<a class="tsurikue-river-rank-link" href="#tsurikue-river-atlas-inline-v26"'
            ' data-river="' + esc(name) + '" title="' + esc(name) + 'を河川図鑑で検索">'
            + esc(name) + '</a>')
def table(kind, entries):
    if kind in ("length", "area"):
        label = "日本の川の長さランキング" if kind == "length" else "日本の川の流域面積ランキング"
        metric = "長さ" if kind == "length" else "流域面積"
        pref_label = "資料掲載の都道府県" if kind == "length" else "流域の都道府県"
    else:
        label, metric, pref_label = "水質が最も良好な河川13選", "水質評価", "調査対象県"
    out = ['<div class="tsu-rank-scroll" role="region" aria-label="' + label + '（横スクロールできます）" tabindex="0">',
           '<table class="tsu-rank-table ' + kind + '"><thead><tr>',
           '<th scope="col">川名</th><th scope="col">' + metric + '</th><th scope="col">' + pref_label + '</th>',
           '</tr></thead><tbody>']
    for i, entry in enumerate(entries, 1):
        name, number_or_pref = entry[0], entry[1]
        if kind in ("length", "area"):
            pref, measure = entry[2], (f"{number_or_pref:,}km²" if kind == "area" else f"{number_or_pref}km")
            prefix = '<span class="tsu-rank-no">' + str(i) + '</span>'
        else:
            pref, measure = number_or_pref, "最高評価"
            prefix = ''
        out.append('<tr><th scope="row">' + prefix + link(name) +
                   '</th><td class="tsu-rank-value">' + esc(measure) +
                   '</td><td class="tsu-pref">' + esc(pref) + '</td></tr>')
    out.append('</tbody></table></div>')
    return ''.join(out)
def make_block(spec):
    for key, expected in (("lengths",10),("areas",10),("quality",13)):
        data = spec[key]
        if len(data) != expected or len({v[0] for v in data}) != expected:
            raise RuntimeError(key + " count/duplicate mismatch")
    if [x[0] for x in spec["lengths"][:2]] != ["信濃川","利根川"]:
        raise RuntimeError("Bad length ordering")
    if spec["areas"][0][0] != "利根川":
        raise RuntimeError("Bad basin ordering")
    # This is a scoped Gutenberg Custom HTML block; no existing tool JS/CSS is changed.
    css_js = r"""<!-- wp:html -->
<div class="tsurikue-river-rankings-20261028" id="tsurikue-river-rankings-20261028">
<style>
.tsurikue-river-rankings-20261028{margin:18px 0 28px;color:#263b3d;font-size:15px;line-height:1.65}
.tsurikue-river-rankings-20261028 *{box-sizing:border-box}
.tsurikue-river-rankings-20261028 .tsu-rank-guide{font-size:12px;color:#637779;margin:7px 0}
.tsurikue-river-rankings-20261028 .tsu-rank-scroll{max-width:100%;overflow-x:auto;overscroll-behavior-x:contain;-webkit-overflow-scrolling:touch;border:1px solid #dae6e3;border-radius:12px;background:#fff;margin:12px 0;scrollbar-gutter:stable}
.tsurikue-river-rankings-20261028 table.tsu-rank-table{border-collapse:separate;border-spacing:0;min-width:710px;width:100%;table-layout:auto;margin:0;border:0;font-size:14px}
.tsurikue-river-rankings-20261028 .tsu-rank-table th,.tsurikue-river-rankings-20261028 .tsu-rank-table td{padding:11px 12px;line-height:1.5;white-space:nowrap;border:0;border-bottom:1px solid #e6eeeb;vertical-align:middle;text-align:left}
.tsurikue-river-rankings-20261028 .tsu-rank-table thead th{background:#ecf5f3;color:#244c53;font-weight:800}
.tsurikue-river-rankings-20261028 .tsu-rank-table tbody tr:last-child > *{border-bottom:0}
.tsurikue-river-rankings-20261028 .tsu-rank-table th:first-child{position:sticky;left:0;z-index:2;width:146px;min-width:146px;max-width:146px;background:#fff;box-shadow:3px 0 6px -5px #344}
.tsurikue-river-rankings-20261028 .tsu-rank-table thead th:first-child{background:#ecf5f3;z-index:3}
.tsurikue-river-rankings-20261028 .tsu-rank-no{display:inline-block;min-width:23px;margin-right:3px;font-size:11px;color:#647879;font-weight:600}
.tsurikue-river-rankings-20261028 .tsu-rank-table a{font-weight:750;color:#226c77;text-decoration:underline;text-underline-offset:3px}
.tsurikue-river-rankings-20261028 .tsu-rank-value{font-variant-numeric:tabular-nums;font-weight:750}
.tsurikue-river-rankings-20261028 .tsu-pref{min-width:310px}
.tsurikue-river-rankings-20261028 .tsu-rank-table.quality .tsu-pref{min-width:160px}
.tsurikue-river-rankings-20261028 .tsu-rank-table.quality{min-width:560px}
.tsurikue-river-rankings-20261028 .tsu-rank-source{font-size:12px;color:#637779;margin:4px 0 18px;overflow-wrap:anywhere}
.tsurikue-river-rankings-20261028 .tsu-rank-source a{color:#286b75}
@media(max-width:600px){.tsurikue-river-rankings-20261028 .tsu-rank-table th:first-child{width:136px;min-width:136px;max-width:136px}.tsurikue-river-rankings-20261028 .tsu-rank-table th,.tsurikue-river-rankings-20261028 .tsu-rank-table td{padding:10px 9px;font-size:13px}}
</style>
<script>
(function(){
"use strict";
const container=document.getElementById("tsurikue-river-rankings-20261028");
if(!container)return;
container.addEventListener("click",function(event){
  const a=event.target.closest("a[data-river]");
  if(!a||!container.contains(a))return;
  const mount=document.getElementById("tsurikue-river-atlas-inline-v26");
  const root=mount&&mount.shadowRoot;
  const tab=root&&root.getElementById("atlasTabRiver");
  const input=root&&root.getElementById("riverSearchV25");
  if(!tab||!input)return; // Anchor fallback when inline atlas is not ready.
  event.preventDefault();
  tab.click();
  input.value=a.getAttribute("data-river");
  input.dispatchEvent(new Event("input",{bubbles:true}));
  mount.scrollIntoView({behavior:matchMedia("(prefers-reduced-motion:reduce)").matches?"auto":"smooth",block:"start"});
});
})();
</script>
</div>
<!-- /wp:html -->"""
    parts=[
        HEAD,
        paragraph("日本で一番長い川は信濃川。でも、流域面積が一番広いのは利根川。どちらも同じ川が1位というわけではありません。"),
        paragraph("気になる川名をタップすると、上の図鑑でその名前を検索できます。調査資料に載っていない川もあるので、検索結果が出ない場合があります。"),
        h3("日本の長い川ランキングTOP10"),
        paragraph("幹川流路延長で比べたランキングです。信濃川は367km。長野県側では千曲川という名前でも親しまれています。"),
        table("length",spec["lengths"]),
        paragraph('<small>※都道府県は国土交通省北海道開発局の「流れているところ」の掲載に従っています。必ずしも本流がすべての都道府県を通る意味ではありません。</small>'),
        h3("日本の流域面積ランキングTOP10"),
        paragraph("流域面積は、雨や雪どけ水などが川へ集まる土地の広さ。川の水面の広さではありません。"),
        table("area",spec["areas"]),
        paragraph("利根川の流域面積は16,840km²で全国1位。長さランキングとは順位が入れ替わります。淀川も流域面積では全国7位です。"),
        h3("水質が最も良好な川13選｜2025年調査"),
        paragraph("こちらは1位から10位を決めるランキングではなく、国土交通省の2025年調査で<strong>同じ最高評価となった13河川</strong>です。"),
        table("quality",spec["quality"]),
        paragraph("この評価はBOD（生物化学的酸素要求量）に基づきます。水がきれいという評価と、魚の多さ・釣りや川遊びの可否は別の話です。"),
        '<!-- wp:html -->'+ '\n'
        + '<p class="tsu-rank-source">出典：<a href="'+esc(spec["length_source"])+'" target="_blank" rel="noopener noreferrer">国土交通省北海道開発局（長さ・流域面積）</a>／<a href="'+esc(spec["quality_source"])+'" target="_blank" rel="noopener noreferrer">国土交通省 2025年一級河川の水質現況（2026年公表）</a></p>\n'
        + '<!-- /wp:html -->',
        css_js
    ]
    return '\n\n'.join(parts) + '\n\n'
def req(path, auth, payload=None):
    h={"Authorization":auth,"Accept":"application/json","User-Agent":"tsurikue-river-ranking-20261028/1.0"}
    data=None
    if payload is not None:
        data=json.dumps(payload,ensure_ascii=False).encode("utf-8")
        h["Content-Type"]="application/json; charset=utf-8"
    request=urllib.request.Request(BASE+path,headers=h,data=data,method="POST" if data is not None else "GET")
    with urllib.request.urlopen(request,timeout=90) as response:
        return json.load(response)
def fetch(auth):
    return req(f"/wp-json/wp/v2/posts/{POST_ID}?context=edit&_fields=id,slug,status,title,content,excerpt,featured_media,categories,author,template,modified",auth)
def meta(post, spec):
    raw=post["content"]["raw"]
    if (post["id"],post["slug"],post["status"],post["title"]["raw"],post["featured_media"])!=(
       POST_ID,spec["target_slug"],"publish",spec["expected_title"],spec["expected_featured_media"]):
        raise RuntimeError("Post ID, slug, status, title or image mismatch")
    if len(re.findall(r'<!-- wp:html -->.*?<!-- /wp:html -->',raw,re.S)) not in (2,4):
        raise RuntimeError("Unexpected Gutenberg custom HTML structure")
    if "ドロバイ" not in raw or "ミミズ" not in raw or "47都道府県" not in raw:
        raise RuntimeError("Original author prose/directory absent")
    if "tsurikue-river-atlas-inline-v26" not in raw or "tsurikue-pref-list" not in raw:
        raise RuntimeError("Original inline tool/directory changed; review before update")
    return raw
def transformed(raw, spec):
    if MARKER in raw:
        if raw.count('id="'+MARKER+'"')!=1:
            raise RuntimeError("Ranking marker duplicated")
        return raw, "ALREADY_PRESENT"
    if raw.count(ANCHOR)!=1:raise RuntimeError("Insertion heading absent or ambiguous")
    section=make_block(spec)
    after=raw.replace(ANCHOR,section+ANCHOR,1)
    if after.replace(section,"",1)!=raw:
        raise RuntimeError("Existing article changed beyond insertion")
    if raw.count("<!-- wp:html -->")!=2 or after.count("<!-- wp:html -->")!=4:
        raise RuntimeError("Existing atlas tool blocks must be preserved")
    if raw.count("<!-- wp:heading") + 4 != after.count("<!-- wp:heading"):
        raise RuntimeError("Unexpected heading count")
    if any(w not in after for w in ("祖父","ドロバイ","タカハヤ","アマゴ")):
        raise RuntimeError("Author's original experience lost")
    return after,"ADD_RANKINGS"
def main(mode):
    spec=json.loads(SPEC.read_text(encoding="utf-8"))
    if len(spec["lengths"])!=10 or len(spec["areas"])!=10 or len(spec["quality"])!=13:
        raise RuntimeError("Rankings data incomplete")
    user=os.environ.get("TSURIKUE_WP_USER")
    password=os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:raise RuntimeError("Missing WordPress credentials; no mutation")
    auth="Basic "+base64.b64encode((user+":"+password).encode()).decode()
    before_post=fetch(auth)
    before=meta(before_post,spec)
    after,action=transformed(before,spec)
    expected=spec.get("expected_before_sha256","")
    print("RIVER_RANKINGS_PREFLIGHT",json.dumps({
        "post_id":POST_ID,"slug":before_post["slug"],"status":before_post["status"],
        "last_modified":before_post["modified"],"before_sha256":sha(before),
        "new_sha256":sha(after),"action":action,"ranking_rows":[10,10,13],
        "existing_tool_untouched":True,"preview_chars":len(after)-len(before)
    },ensure_ascii=False),flush=True)
    if expected and sha(before)!=expected and action!="ALREADY_PRESENT":
        raise RuntimeError("WP changed since approved preflight; no update")
    if mode=="check":
        return
    if mode!="apply":raise RuntimeError("Expected check or apply")
    if action=="ALREADY_PRESENT":
        print("RIVER_RANKINGS_ALREADY_APPLIED_NO_WRITE")
        return
    if not expected:raise RuntimeError("Expected WP preimage sha must be pinned after PR preflight")
    current=fetch(auth)
    if current["modified"]!=before_post["modified"] or meta(current,spec)!=before:
        raise RuntimeError("Concurrent WordPress edit; no update")
    req(f"/wp-json/wp/v2/posts/{POST_ID}",auth,{"content":after})
    final=fetch(auth)
    for key in ("id","slug","status","title","excerpt","featured_media","categories","author","template"):
        if final[key]!=before_post[key]:raise RuntimeError("Protected WordPress field changed: "+key)
    if final["content"]["raw"]!=after:
        raise RuntimeError("WordPress did not preserve inserted markup")
    if final["content"]["rendered"].count(MARKER)!=1:
        raise RuntimeError("Rendering does not include ranking widget")
    print("RIVER_RANKINGS_WORDPRESS_VERIFIED",json.dumps({
        "post_id":final["id"],"slug":final["slug"],"status":final["status"],
        "title":final["title"]["raw"],"featured_media":final["featured_media"],
        "content_sha256":sha(after),"rows":[10,10,13],"untouched_original_content":True
    },ensure_ascii=False),flush=True)
if __name__=="__main__":
    main(sys.argv[1] if len(sys.argv)>1 else "check")
