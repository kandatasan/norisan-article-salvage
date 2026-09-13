#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

SITE="https://tsurikue.com"
UA="tsurikue-fj-published-mitsumori-fix/1.0"
POST_ID=3767
SLUG="landcruiser-fj-price"
TITLE="ランドクルーザーFJの乗り出し価格はいくら？実際の支払総額は550万516円"
CONTENT_PATH=Path("packages/landcruiser-fj-price/content.html")
FEATURED=3757
CATEGORY_ID=10
EXPECTED_OLD_SHA="96e70c5ea76bc55269f2780a01d074f12f04d788fa0590f4c319d03224dcebd7"
OLD_EXCERPT="ランドクルーザーFJ VXは車両価格450万100円。実際に購入したFJはオプション・用品・諸費用を含めて現金販売時の支払総額550万516円でした。購入時の価格明細メモをもとに、約100万円増えた内訳や支払いプランを紹介します。"
NEW_EXCERPT="ランドクルーザーFJ VXは車両価格450万100円。実際の見積もりでは、オプション・用品・諸費用を含めて現金販売時の支払総額550万516円でした。約100万円増えた内訳や支払いプランを紹介します。"

def auth():
    user=os.environ["TSURIKUE_WP_USER"]
    pw=os.environ["TSURIKUE_WP_APP_PASSWORD"]
    token=base64.b64encode(f"{user}:{pw}".encode()).decode()
    return "Basic "+token

def req(url, method="GET", payload=None):
    headers={"Authorization":auth(),"Accept":"application/json","User-Agent":UA}
    data=None
    if payload is not None:
        data=json.dumps(payload,ensure_ascii=False).encode()
        headers["Content-Type"]="application/json; charset=utf-8"
    r=urllib.request.Request(url,data=data,headers=headers,method=method)
    with urllib.request.urlopen(r,timeout=60) as resp:
        raw=resp.read().decode()
        return (json.loads(raw) if raw else None),dict(resp.headers)

def raw_field(row,key):
    v=row.get(key) or {}
    if isinstance(v,dict):
        return v.get("raw") or v.get("rendered") or ""
    return str(v)

def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()

def norm_excerpt(value):
    return re.sub(r"<[^>]+>","",html.unescape(value or "")).strip()

def public_counts():
    out={}
    for ep in ("posts","pages"):
        q=urllib.parse.urlencode({"status":"publish","per_page":1,"_fields":"id"})
        _,h=req(f"{SITE}/wp-json/wp/v2/{ep}?{q}")
        out[ep]=int(h.get("X-WP-Total","0"))
    out["total"]=out["posts"]+out["pages"]
    return out

def get_post():
    q=urllib.parse.urlencode({
        "context":"edit",
        "_fields":"id,slug,status,title,content,excerpt,featured_media,categories,link"
    })
    row,_=req(f"{SITE}/wp-json/wp/v2/posts/{POST_ID}?{q}")
    return row

def assert_identity(row):
    if int(row.get("id") or 0)!=POST_ID:
        raise RuntimeError("post id mismatch")
    if row.get("slug")!=SLUG:
        raise RuntimeError("slug mismatch")
    if row.get("status")!="publish":
        raise RuntimeError(f"expected published post, got {row.get('status')}")
    if html.unescape(raw_field(row,"title"))!=TITLE:
        raise RuntimeError("title mismatch")
    if int(row.get("featured_media") or 0)!=FEATURED:
        raise RuntimeError("featured media mismatch")
    if CATEGORY_ID not in (row.get("categories") or []):
        raise RuntimeError("car category missing")

def main():
    desired=CONTENT_PATH.read_text(encoding="utf-8").strip()+"\n"
    desired_sha=sha(desired)

    # Wording guard: this one-off task must only make the requested terminology change.
    if "実際の見積もりでは支払総額550万516円" not in desired:
        raise RuntimeError("desired H2 wording missing")
    if "実際の見積もりを見ながら紹介します。" not in desired:
        raise RuntimeError("desired intro wording missing")
    if "購入時の価格明細メモ" in desired or "見積ではなくメモ" in desired:
        raise RuntimeError("old defensive memo wording still present")

    before_counts=public_counts()
    before=get_post()
    assert_identity(before)

    current=raw_field(before,"content")
    current_sha=sha(current)
    current_excerpt=norm_excerpt(raw_field(before,"excerpt"))

    if current_sha==desired_sha and current_excerpt==NEW_EXCERPT:
        action="ALREADY_UP_TO_DATE"
    else:
        if current_sha!=EXPECTED_OLD_SHA:
            raise RuntimeError(f"published content changed unexpectedly: {current_sha}")
        if current_excerpt not in {OLD_EXCERPT,NEW_EXCERPT}:
            raise RuntimeError("published excerpt changed unexpectedly")
        # Do not send a status field. This preserves the user's already-published state.
        updated,_=req(
            f"{SITE}/wp-json/wp/v2/posts/{POST_ID}",
            method="POST",
            payload={"content":desired,"excerpt":NEW_EXCERPT},
        )
        if int(updated.get("id") or 0)!=POST_ID:
            raise RuntimeError("update response id mismatch")
        action="UPDATE_PUBLISHED_WORDING"

    after=get_post()
    assert_identity(after)
    after_counts=public_counts()

    if after_counts!=before_counts:
        raise RuntimeError(f"public counts changed: {before_counts} -> {after_counts}")
    if raw_field(after,"content").strip()!=desired.strip():
        raise RuntimeError("content verification failed")
    if norm_excerpt(raw_field(after,"excerpt"))!=NEW_EXCERPT:
        raise RuntimeError("excerpt verification failed")

    print("# FJ published wording fix")
    print(f"- result: **SUCCESS**")
    print(f"- action: **{action}**")
    print(f"- post_id: **{POST_ID}**")
    print(f"- status: **{after.get('status')}**")
    print(f"- slug: **{after.get('slug')}**")
    print(f"- public_before: **{before_counts}**")
    print(f"- public_after: **{after_counts}**")
    print(f"- content_sha256: **{sha(raw_field(after,'content'))}**")
    print("- terminology: **見積もり**")
    print("- publish_state_preserved: **True**")

if __name__=="__main__":
    main()
