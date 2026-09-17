#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import urllib.parse
import urllib.request

SITE = "https://tsurikue.com"
UA = "tsurikue-adsense-discovery-20260917/1.0"

TARGET_POST_IDS = [2041, 2152, 2180, 2629, 2664, 3774]
TARGET_PHRASES = {
    2041: [
        "今後つりくえ！でも記事化予定",
        "江田島の記事は今後整理予定です",
        "しっかりまとめる予定です",
        "まだつりくえ！では記事が整っていません",
        "今後の大きな宿題です",
        "今後しっかり増やしていきたい",
    ],
    2152: ["写真データが壊れていたので、少ししかありませんでした。"],
    2180: ["今回回収できた写真は、この1枚だけです。"],
    2629: ["でも実釣結果は未確認"],
    2664: ["このコースは別記事でまとめる予定です。"],
    3774: ["このへんは別記事で、写真を増やして詳しくまとめる予定です。"],
}

def auth_header() -> str:
    user = os.environ["TSURIKUE_WP_USER"]
    password = os.environ["TSURIKUE_WP_APP_PASSWORD"]
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()

def request(method: str, path: str):
    req = urllib.request.Request(
        SITE + path,
        method=method,
        headers={"Authorization": auth_header(), "Accept": "application/json", "User-Agent": UA},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read().decode("utf-8")
        return json.loads(data) if data else None

def raw(row: dict, key: str) -> str:
    v = row.get(key) or {}
    if isinstance(v, dict):
        return v.get("raw") or v.get("rendered") or ""
    return str(v)

def sha256(s: str) -> str:
    return hashlib.sha256((s or "").encode()).hexdigest()

def fetch_html(path: str) -> str:
    req = urllib.request.Request(SITE + path, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", "replace")

def main() -> None:
    root = request("GET", "/wp-json/")
    namespaces = root.get("namespaces") or []
    routes = root.get("routes") or {}
    interesting_routes = sorted(
        x for x in routes
        if any(k in x.lower() for k in ["seo", "swell", "ssp", "robots", "index"])
    )

    cats = request("GET", "/wp-json/wp/v2/categories?context=edit&per_page=100")
    tags = request("GET", "/wp-json/wp/v2/tags?context=edit&per_page=100")
    users = request("GET", "/wp-json/wp/v2/users?context=edit&per_page=100")

    print("=== NAMESPACES ===")
    print(json.dumps(namespaces, ensure_ascii=False, indent=2))
    print("=== INTERESTING ROUTES ===")
    print(json.dumps(interesting_routes, ensure_ascii=False, indent=2))

    print("=== CATEGORY KEYS / META ===")
    for row in cats:
        print(json.dumps({
            "id": row.get("id"),
            "slug": row.get("slug"),
            "name": row.get("name"),
            "count": row.get("count"),
            "keys": sorted(row.keys()),
            "meta": row.get("meta"),
        }, ensure_ascii=False))
    print("=== TAG KEYS / META ===")
    for row in tags[:20]:
        print(json.dumps({
            "id": row.get("id"),
            "slug": row.get("slug"),
            "name": row.get("name"),
            "count": row.get("count"),
            "keys": sorted(row.keys()),
            "meta": row.get("meta"),
        }, ensure_ascii=False))
    print("=== USERS ===")
    for row in users:
        print(json.dumps({
            "id": row.get("id"),
            "slug": row.get("slug"),
            "name": row.get("name"),
            "keys": sorted(row.keys()),
        }, ensure_ascii=False))

    print("=== HTML HEAD CLUES ===")
    for path in ["/category/fishing/", "/category/car/", "/2026/06/"]:
        try:
            html = fetch_html(path)
        except Exception as exc:
            print(path, "ERROR", repr(exc))
            continue
        head = html.split("</head>", 1)[0]
        robots = re.findall(r'<meta[^>]+name=["\']robots["\'][^>]*>', head, re.I)
        gens = re.findall(r'<meta[^>]+name=["\']generator["\'][^>]*>', head, re.I)
        plugins = sorted(set(re.findall(r'/wp-content/plugins/([^/"\']+)', head, re.I)))
        print(json.dumps({
            "path": path,
            "robots": robots,
            "generator": gens,
            "plugins": plugins,
            "head_excerpt": head[:2000],
        }, ensure_ascii=False))

    print("=== TARGET POSTS ===")
    for pid in TARGET_POST_IDS:
        row = request("GET", f"/wp-json/wp/v2/posts/{pid}?context=edit&_fields=id,slug,status,title,content,author,featured_media,categories")
        content = raw(row, "content")
        print(json.dumps({
            "id": pid,
            "slug": row.get("slug"),
            "status": row.get("status"),
            "title": raw(row, "title"),
            "sha256": sha256(content),
            "phrases": {p: content.count(p) for p in TARGET_PHRASES.get(pid, [])},
        }, ensure_ascii=False))

if __name__ == "__main__":
    main()
