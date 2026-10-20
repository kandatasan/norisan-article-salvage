#!/usr/bin/env python3
"""Package a runnable local HTTP static preview, never publish.

Extract the 9 research category ZIPs into the site ZIP alongside index.html.
The reader initially loads only the ~hundreds-of-KB navigation document;
it fetches exactly one per-river/category JSON only on a user's selection.
This bundle is research-only and must be served from a local HTTP server.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED

def sha(b):
    return hashlib.sha256(b).hexdigest()

def add(z,name,b):
    if name.startswith("/") or ".." in name.split("/") or not re.fullmatch(r"[a-z0-9_./-]+",name):
        raise ValueError("Unsafe package path")
    info=ZipInfo(name,date_time=(1980,1,1,0,0,0))
    info.external_attr=0o644<<16;info.compress_type=ZIP_DEFLATED
    z.writestr(info,b,compress_type=ZIP_DEFLATED,compresslevel=8)

def package(viewer,pack_dir,out):
    viewer=Path(viewer);pack_dir=Path(pack_dir);out=Path(out)
    if out.exists():raise FileExistsError(out)
    index=viewer.read_bytes()
    text=index.decode("utf-8")
    if "fetch(path" not in text or "<iframe" in text:
        raise ValueError("Frontend must lazy-fetch categories without iframe")
    manifest=json.loads((pack_dir/"manifest_v09.json").read_text(encoding="utf-8"))
    if len(manifest["rivers"])!=428 or len(manifest["regions"])!=9:
        raise ValueError("Missing survey regions or river identities")
    target={q["categories"][group]["file"]
            for q in manifest["rivers"] for group in ("fish","benthic_animals","birds","plants")}
    if len(target)!=1712:raise ValueError("Expected 1712 independent river/category static JSON files")
    count=0
    size=0
    out.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(out,"w",compression=ZIP_DEFLATED,compresslevel=8) as combined:
        add(combined,"index.html",index)
        add(combined,"manifest_v09.json",(pack_dir/"manifest_v09.json").read_bytes())
        explanation=(
           "日本の河川大図鑑 / 研究用ブラウザ試作 v0.9\n"
           "研究用ZIPを解凍し、そのフォルダーで次のコマンドを実行：\n"
           "python -m http.server 8000\n"
           "ブラウザで http://localhost:8000/ を開く。\n"
           "ブラウザからindex.htmlをfile://で直接開くとJSON読み込みが拒否される場合があります。\n"
           "※都道府県と水系は公式資料に載る関係であり、すべての川がその県内にあるという意味ではありません。\n"
           "※河川別の生物記録は過去の調査資料の掲載名です。現在生息する種の証明ではありません。\n"
           "※WordPressやXserverには反映・公開していません。\n"
        ).encode("utf-8")
        add(combined,"readme_preview.txt",explanation)
        for region in manifest["regions"]:
            p=pack_dir/region["archive_file"]
            b=p.read_bytes()
            if sha(b)!=region["archive_sha256"]:raise ValueError("Pack archive integrity failed")
            with ZipFile(p) as z:
                for name in z.namelist():
                    if name not in target:raise ValueError("Unexpected JSON path: "+name)
                    row=z.read(name)
                    d=json.loads(row)
                    if d["schema"]!="river-category-historical-v09":
                        raise ValueError("Category schema mismatch")
                    add(combined,name,row)
                    size+=len(row);count+=1
        if count!=len(target):raise ValueError("Not all category files were packed")
    with ZipFile(out) as z:
        members=set(z.namelist())
        if len(members)!=len(target)+3 or target-members:
            raise ValueError("Self-contained site package missing members")
        if "index.html" not in members:raise ValueError("No static viewer")
    info={"version":"v09","research_preview_archive_file":out.name,
          "sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
          "archive_bytes":out.stat().st_size,
          "entry_points":47,"sourced_prefecture_watershed_links":80,
          "river_category_files":count,"plain_json_total_bytes":size,
          "individual_river_name_identities":428,
          "all_labels_initially_loaded":False,
          "requires_http_server":True,"no_wordpress_or_mysql_changes":True}
    (out.parent/"site_integrity_v09.json").write_text(json.dumps(info,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(info,ensure_ascii=False))
    return info

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--viewer",required=True);p.add_argument("--packs",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args();package(a.viewer,a.packs,a.out)
