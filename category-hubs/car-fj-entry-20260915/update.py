#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import urllib.parse
import urllib.request

SITE="https://tsurikue.com"
BASE=f"{SITE}/wp-json/wp/v2"
PAGE_ID=3294
PAGE_SLUG="car-guide"
CAR_CATEGORY_ID=10
FJ_CATEGORY_ID=25
MARKER="<!-- tsurikue-fj-category-entry:v1 -->"
HUB_MARKER="tsurikue-category-hub:v1:car-blocks"

ANCHOR='<!-- /wp:cover -->\n<!-- wp:group {"className":"tq-car-choose tq-car-section"} -->'

ENTRY_TEMPLATE="""<!-- tsurikue-fj-category-entry:v1 -->
<!-- wp:group {"align":"full","style":{"color":{"background":"#eef2f4"},"spacing":{"padding":{"top":"28px","right":"20px","bottom":"28px","left":"20px"}}},"layout":{"type":"constrained"}} -->
<div class="wp-block-group alignfull has-background" style="background-color:#eef2f4;padding-top:28px;padding-right:20px;padding-bottom:28px;padding-left:20px">
<!-- wp:paragraph {"align":"center"} -->
<p class="has-text-align-center"><strong>ランドクルーザーFJの記事はこちら。</strong><br>実際に購入したFJの価格・レビュー・使い勝手をまとめています。</p>
<!-- /wp:paragraph -->

<!-- wp:buttons {"layout":{"type":"flex","justifyContent":"center"}} -->
<div class="wp-block-buttons"><!-- wp:button {"className":"is-style-outline"} -->
<div class="wp-block-button is-style-outline"><a class="wp-block-button__link wp-element-button" href="{fj_link}">ランドクルーザーFJを見る →</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons -->
</div>
<!-- /wp:group -->
"""

def auth_header():
    user=os.environ.get("TSURIKUE_WP_USER")
    pw=os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not pw:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    token=base64.b64encode(f"{user}:{pw}".encode()).decode()
    return "Basic "+token

def request(path, method="GET", payload=None, timeout=60):
    headers={
        "Authorization":auth_header(),
        "Accept":"application/json",
        "User-Agent":"tsurikue-add-fj-entry-car-top-20260915/1.0",
    }
    data=None
    if payload is not None:
        data=json.dumps(payload,ensure_ascii=False).encode()
        headers["Content-Type"]="application/json; charset=utf-8"
    req=urllib.request.Request(BASE+path,data=data,headers=headers,method=method)
    with urllib.request.urlopen(req,timeout=timeout) as resp:
        raw=resp.read().decode()
        return (json.loads(raw) if raw else None),dict(resp.headers)

def raw_field(item,key):
    v=item.get(key) or {}
    if isinstance(v,dict):
        return v.get("raw") or v.get("rendered") or ""
    return str(v)

def count_published(endpoint):
    _,headers=request(f"/{endpoint}?status=publish&per_page=1&_fields=id")
    return int(headers.get("X-WP-Total","0"))

def public_counts():
    posts=count_published("posts")
    pages=count_published("pages")
    return {"published_posts":posts,"published_pages":pages,"published_total":posts+pages}

def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()

def main():
    before_counts=public_counts()

    page,_=request(
        f"/pages/{PAGE_ID}?context=edit&_fields=id,slug,status,title,content,link"
    )
    before_raw=raw_field(page,"content")
    before_title=raw_field(page,"title")

    if (page.get("slug"),page.get("status"))!=(PAGE_SLUG,"publish"):
        raise SystemExit("PAGE_IDENTITY_GUARD_FAILED")
    if HUB_MARKER not in before_raw:
        raise SystemExit("CAR_HUB_MARKER_GUARD_FAILED")
    if before_raw.count(ANCHOR)!=1:
        raise SystemExit(f"ANCHOR_COUNT_FAILED_{before_raw.count(ANCHOR)}")

    fj,_=request(
        f"/categories/{FJ_CATEGORY_ID}?context=edit&_fields=id,name,slug,parent,count,link"
    )
    if int(fj.get("id") or 0)!=FJ_CATEGORY_ID:
        raise SystemExit("FJ_CATEGORY_ID_FAILED")
    if fj.get("slug")!="landcruiser-fj" or int(fj.get("parent") or 0)!=CAR_CATEGORY_ID:
        raise SystemExit("FJ_CATEGORY_IDENTITY_FAILED")
    fj_link=fj.get("link") or ""
    if not fj_link.startswith(SITE+"/"):
        raise SystemExit("FJ_CATEGORY_LINK_FAILED")

    entry=ENTRY_TEMPLATE.format(fj_link=html.escape(fj_link,quote=True)).rstrip()+"\n"

    if MARKER in before_raw:
        if before_raw.count(MARKER)!=1 or fj_link not in before_raw:
            raise SystemExit("EXISTING_ENTRY_GUARD_FAILED")
        action="ALREADY_UP_TO_DATE"
        after_raw=before_raw
    else:
        expected=before_raw.replace(ANCHOR,entry+ANCHOR,1)
        updated,_=request(
            f"/pages/{PAGE_ID}",
            method="POST",
            payload={"content":expected},
            timeout=90,
        )
        if int(updated.get("id") or 0)!=PAGE_ID:
            raise SystemExit("UPDATE_RESPONSE_ID_FAILED")
        action="UPDATE_PUBLISHED_PAGE"
        after_raw=expected

    verify,_=request(
        f"/pages/{PAGE_ID}?context=edit&_fields=id,slug,status,title,content,link"
    )
    live_raw=raw_field(verify,"content")
    live_title=raw_field(verify,"title")

    if verify.get("status")!="publish" or verify.get("slug")!=PAGE_SLUG:
        raise SystemExit("PUBLISH_STATE_CHANGED")
    if live_title!=before_title:
        raise SystemExit("PAGE_TITLE_CHANGED")
    if live_raw!=after_raw:
        raise SystemExit("CONTENT_VERIFY_FAILED")
    if live_raw.count(MARKER)!=1:
        raise SystemExit("ENTRY_MARKER_COUNT_FAILED")
    if live_raw.count(fj_link)!=1:
        raise SystemExit("FJ_LINK_COUNT_FAILED")
    if "ランドクルーザーFJの記事はこちら。" not in live_raw:
        raise SystemExit("FJ_COPY_MISSING")
    if "実際に購入したFJの価格・レビュー・使い勝手をまとめています。" not in live_raw:
        raise SystemExit("FJ_SUBCOPY_MISSING")

    after_counts=public_counts()
    if before_counts!=after_counts:
        raise SystemExit(f"PUBLIC_COUNTS_CHANGED {before_counts} -> {after_counts}")

    report={
        "result":"SUCCESS",
        "action":action,
        "page_id":PAGE_ID,
        "slug":PAGE_SLUG,
        "status":"publish",
        "title":before_title,
        "fj_category_id":FJ_CATEGORY_ID,
        "fj_category_link":fj_link,
        "fj_category_count":fj.get("count"),
        "entry_marker_count":live_raw.count(MARKER),
        "published_before":before_counts,
        "published_after":after_counts,
        "content_sha256_before":sha(before_raw),
        "content_sha256_after":sha(live_raw),
        "wordpress_write_count":0 if action=="ALREADY_UP_TO_DATE" else 1,
        "publish_count":0,
        "targeted_insertion_only":True,
        "publish_state_preserved":True,
    }
    print("# Car top FJ category entry")
    for k,v in report.items():
        print(f"- {k}: **{v}**")

if __name__=="__main__":
    main()
