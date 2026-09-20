#!/usr/bin/env python3
from __future__ import annotations

import base64, hashlib, html, json, os, re, socket, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

SITE = "https://tsurikue.com"
UA = "tsurikue-create-lbx-cheap-20260920/1.0"
TITLE = "レクサスLBXを安く買う方法｜欲しいオプションを諦めず負担を減らす5つのコツ"
SLUG = "lexus-lbx-cheap"
EXCERPT = "レクサスLBXを安く買うなら、値引きやオプション削減だけを見るのはもったいない。実際にLBXへ試乗・見積もりを取った元UXオーナーが、売却額、グレード、中古車、ローン、オプションの順で負担を減らす方法を整理します。"
CONTENT_PATH = Path("packages/lexus-lbx-cheap/content.html")
SOURCE_POST_ID = 3611
SOURCE_SLUG = "lexus-lbx-options"
REPORT = Path("reports/lexus-lbx-cheap-create-20260920")

TOKEN = re.compile(r"<!--\s+/?wp:[\s\S]*?-->")
OPEN = re.compile(r"<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->")
CLOSE = re.compile(r"<!--\s+/wp:([\w\-/]+)\s+-->")


def auth_header():
    u = os.environ.get("TSURIKUE_WP_USER")
    p = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not u or not p:
        raise RuntimeError("missing WordPress secrets")
    return "Basic " + base64.b64encode(f"{u}:{p}".encode()).decode()


def request(method, path, payload=None):
    headers = {"Authorization": auth_header(), "Accept": "application/json", "User-Agent": UA}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    last = None
    for n in range(8):
        req = urllib.request.Request(SITE + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                body = resp.read().decode("utf-8")
                return (json.loads(body) if body else None), dict(resp.headers.items())
        except urllib.error.HTTPError as exc:
            last = exc
            if 400 <= exc.code < 500 and exc.code not in {408, 429}:
                raise
        except (urllib.error.URLError, TimeoutError, socket.gaierror, OSError) as exc:
            last = exc
        if n < 7:
            time.sleep(min(3 + n, 10))
    raise last


def raw(row, key):
    v = row.get(key) or {}
    return (v.get("raw") or v.get("rendered") or "") if isinstance(v, dict) else str(v)


def sha256(text):
    return hashlib.sha256((text or "").encode()).hexdigest()


def gutenberg_ok(text):
    stack = []
    for m in TOKEN.finditer(text):
        tok = m.group(0)
        op = OPEN.fullmatch(tok)
        cl = CLOSE.fullmatch(tok)
        if op and not op.group(2):
            stack.append(op.group(1))
        elif cl:
            if not stack or stack[-1] != cl.group(1):
                return False
            stack.pop()
    return not stack


def validate_content(c):
    if "<h1" in c.casefold() or '"level":1' in c:
        raise RuntimeError("body h1 forbidden")
    if not gutenberg_ok(c):
        raise RuntimeError("Gutenberg mismatch")
    if any(x in c for x in ["普通に", "🔥", "🤣", "😁", "😏", "😂", "😊"]):
        raise RuntimeError("banned wording/emoji")
    required = [
        "25万6,300円", "4,856,300円", "4,200,000円", "4,600,000円",
        "344.8万円〜777.7万円", "2026年9月20日", "差は25万円",
        "カーセブンへ427万円", '[blog_parts id="2846"]', '[blog_parts id="2843"]',
        "https://tsurikue.com/car-sell-high/", "https://tsurikue.com/lexus-lbx-options/",
        "https://lexus.jp/models/lbx/features/price_package/",
        "https://www.goo-net.com/usedcar/brand-LEXUS/car-LBX/",
        "https://cpo.lexus.jp/cposearch/result_list?Cn=LBX"
    ]
    for x in required:
        if x not in c:
            raise RuntimeError(f"required phrase missing: {x}")


def public_count(endpoint):
    q = urllib.parse.urlencode({"status": "publish", "per_page": 1, "_fields": "id"})
    _, headers = request("GET", f"/wp-json/wp/v2/{endpoint}?{q}")
    for k, v in headers.items():
        if k.lower() == "x-wp-total":
            return int(v)
    raise RuntimeError("missing public count")


def public_counts():
    return {"posts": public_count("posts"), "pages": public_count("pages")}


def source_meta():
    q = urllib.parse.urlencode({
        "context": "edit",
        "_fields": "id,slug,status,author,featured_media,categories,tags"
    })
    row, _ = request("GET", f"/wp-json/wp/v2/posts/{SOURCE_POST_ID}?{q}")
    if row.get("slug") != SOURCE_SLUG or row.get("status") != "publish":
        raise RuntimeError("source LBX post mismatch")
    if not int(row.get("author") or 0):
        raise RuntimeError("source author missing")
    if not int(row.get("featured_media") or 0):
        raise RuntimeError("source featured media missing")
    return {
        "author": int(row["author"]),
        "featured_media": int(row["featured_media"]),
        "categories": list(row.get("categories") or []),
        "tags": list(row.get("tags") or []),
    }


def find_post():
    q = urllib.parse.urlencode({
        "context": "edit",
        "slug": SLUG,
        "status": "any",
        "per_page": 10,
        "_fields": "id,slug,status,title,content,author,featured_media,categories,tags,excerpt"
    })
    rows, _ = request("GET", f"/wp-json/wp/v2/posts?{q}")
    return rows


def norm_excerpt(v):
    return re.sub(r"<[^>]+>", "", html.unescape(v or "")).strip()


def write_report(d):
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / "result.json").write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# LBX cheap-buying revenue draft create 2026-09-20",
        "",
        f"- result: **{d['result']}**",
        f"- article_action: **{d['action']}**",
        f"- post_id: **{d['post_id']}**",
        f"- status: **{d['status']}**",
        f"- slug: **{SLUG}**",
        f"- published posts before/after: **{d['before']['posts']} / {d['after']['posts']}**",
        f"- published pages before/after: **{d['before']['pages']} / {d['after']['pages']}**",
        f"- content sha256: **{d['sha']}**",
    ]
    (REPORT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def main():
    content = CONTENT_PATH.read_text(encoding="utf-8").strip() + "\n"
    validate_content(content)
    before = public_counts()
    meta = source_meta()
    rows = find_post()

    if rows:
        if len(rows) != 1:
            raise RuntimeError("slug collision")
        row = rows[0]
        if row.get("status") != "draft":
            raise RuntimeError(f"existing slug is not draft: {row.get('status')}")
        if html.unescape(raw(row, "title")) != TITLE or raw(row, "content").strip() != content.strip():
            raise RuntimeError("existing draft differs")
        post = row
        action = "REUSE_EXACT_DRAFT"
    else:
        payload = {
            "title": TITLE,
            "slug": SLUG,
            "content": content,
            "excerpt": EXCERPT,
            "status": "draft",
            **meta,
        }
        post, _ = request("POST", "/wp-json/wp/v2/posts", payload)
        action = "CREATE_DRAFT"

    pid = int(post.get("id") or 0)
    q = urllib.parse.urlencode({
        "context": "edit",
        "_fields": "id,slug,status,title,content,author,featured_media,categories,tags,excerpt"
    })
    check, _ = request("GET", f"/wp-json/wp/v2/posts/{pid}?{q}")

    if check.get("slug") != SLUG or check.get("status") != "draft":
        raise RuntimeError("final identity/status mismatch")
    if html.unescape(raw(check, "title")) != TITLE or raw(check, "content").strip() != content.strip():
        raise RuntimeError("final title/content mismatch")
    if norm_excerpt(raw(check, "excerpt")) != EXCERPT:
        raise RuntimeError("final excerpt mismatch")
    for key in ["author", "featured_media"]:
        if int(check.get(key) or 0) != int(meta[key]):
            raise RuntimeError(f"final {key} mismatch")
    for key in ["categories", "tags"]:
        if sorted(check.get(key) or []) != sorted(meta[key]):
            raise RuntimeError(f"final {key} mismatch")

    after = public_counts()
    if after != before:
        raise RuntimeError(f"public counts changed: {before}->{after}")

    write_report({
        "result": "SUCCESS",
        "action": action,
        "post_id": pid,
        "status": "draft",
        "before": before,
        "after": after,
        "sha": sha256(raw(check, "content")),
    })


if __name__ == "__main__":
    main()
