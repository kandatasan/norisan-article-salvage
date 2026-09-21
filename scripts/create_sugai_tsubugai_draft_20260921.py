#!/usr/bin/env python3
from __future__ import annotations

import base64, hashlib, html, json, os, re, socket, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

SITE = "https://tsurikue.com"
UA = "tsurikue-create-sugai-tsubugai-20260921/1.0"
TITLE = '広島で「ツブガイ」と呼ぶスガイはうまい！味・茹で方と磯遊びの思い出'
SLUG = 'sugai-tsubugai'
EXCERPT = '広島で「ツブ」「ツブガイ」と呼ぶことがあるスガイ。磯で見つけたスガイを水から茹で、爪楊枝でクルクル。甘みと磯の風味、わずかな苦味。海水で茹でた3歳ごろの思い出や、イシダタミとの違いも紹介します。'
CONTENT_PATH = Path("packages/sugai-tsubugai/content.html")
SOURCE_AUTHOR_POST_ID = 2654
SOURCE_AUTHOR_SLUG = "sayori-taberu"
CATEGORY_SLUGS = ["wild-food-fish-cooking"]
TAG_SLUGS = ["catch-and-eat", "hiroshima", "seafood"]
REPORT = Path("reports/sugai-tsubugai-create-20260921")

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
        "3歳ごろ、爺ちゃんが空き缶で茹でてくれた",
        "水から入れて沸騰後5〜6分",
        "海水でそのまま茹でる食べ方",
        "味だけならサザエよりスガイのほうが好き",
        "イシダタミ",
        "丸くて石灰質のフタ",
        "https://fishlab.hiroshima-u.ac.jp/setouchi-ikimono/iso-seibutu/iso-seibutu.html",
        "https://www.pref.hiroshima.lg.jp/soshiki/88/siohigariisoasobi.html",
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


def source_author():
    q = urllib.parse.urlencode({"context": "edit", "_fields": "id,slug,status,author"})
    row, _ = request("GET", f"/wp-json/wp/v2/posts/{SOURCE_AUTHOR_POST_ID}?{q}")
    if row.get("slug") != SOURCE_AUTHOR_SLUG or row.get("status") != "publish":
        raise RuntimeError("source author post mismatch")
    author = int(row.get("author") or 0)
    if not author:
        raise RuntimeError("source author missing")
    return author


def term_ids(endpoint, slugs):
    ids = []
    for slug in slugs:
        q = urllib.parse.urlencode({"slug": slug, "per_page": 10, "_fields": "id,slug"})
        rows, _ = request("GET", f"/wp-json/wp/v2/{endpoint}?{q}")
        exact = [r for r in rows if r.get("slug") == slug]
        if len(exact) != 1:
            raise RuntimeError(f"term resolve failed: {endpoint}/{slug}")
        ids.append(int(exact[0]["id"]))
    return ids


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
        "# Sugai / tsubugai fresh article draft create 2026-09-21",
        "",
        f"- result: **{d['result']}**",
        f"- article_action: **{d['action']}**",
        f"- post_id: **{d['post_id']}**",
        f"- status: **{d['status']}**",
        f"- slug: **{SLUG}**",
        f"- title: **{TITLE}**",
        f"- featured_media: **0**",
        f"- category_ids: **{d['categories']}**",
        f"- tag_ids: **{d['tags']}**",
        f"- published posts before/after: **{d['before']['posts']} / {d['after']['posts']}**",
        f"- published pages before/after: **{d['before']['pages']} / {d['after']['pages']}**",
        f"- content sha256: **{d['sha']}**",
        "- media note: **fresh user photos are not yet in WordPress media; no guessed media inserted**",
    ]
    (REPORT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def main():
    content = CONTENT_PATH.read_text(encoding="utf-8").strip() + "\n"
    validate_content(content)
    before = public_counts()
    author = source_author()
    categories = term_ids("categories", CATEGORY_SLUGS)
    tags = term_ids("tags", TAG_SLUGS)
    rows = find_post()

    if rows:
        if len(rows) != 1:
            raise RuntimeError("slug collision")
        row = rows[0]
        if row.get("status") != "draft":
            raise RuntimeError(f"existing slug is not draft: {row.get('status')}")
        exact = (
            html.unescape(raw(row, "title")) == TITLE
            and raw(row, "content").strip() == content.strip()
            and norm_excerpt(raw(row, "excerpt")) == EXCERPT
            and int(row.get("author") or 0) == author
            and int(row.get("featured_media") or 0) == 0
            and sorted(row.get("categories") or []) == sorted(categories)
            and sorted(row.get("tags") or []) == sorted(tags)
        )
        if not exact:
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
            "author": author,
            "featured_media": 0,
            "categories": categories,
            "tags": tags,
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
    if int(check.get("author") or 0) != author:
        raise RuntimeError("final author mismatch")
    if int(check.get("featured_media") or 0) != 0:
        raise RuntimeError("unexpected featured media")
    if sorted(check.get("categories") or []) != sorted(categories):
        raise RuntimeError("final categories mismatch")
    if sorted(check.get("tags") or []) != sorted(tags):
        raise RuntimeError("final tags mismatch")

    after = public_counts()
    if after != before:
        raise RuntimeError(f"public counts changed: {before}->{after}")

    write_report({
        "result": "SUCCESS",
        "action": action,
        "post_id": pid,
        "status": "draft",
        "categories": categories,
        "tags": tags,
        "before": before,
        "after": after,
        "sha": sha256(raw(check, "content")),
    })


if __name__ == "__main__":
    main()
