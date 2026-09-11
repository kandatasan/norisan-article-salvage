#!/usr/bin/env python3
import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

SITE_URL = "https://tsurikue.com"
PATCH_DIR = Path(__file__).resolve().parents[1] / "packages" / "affiliate-layout-20260911"
REPORT_DIR = Path(__file__).resolve().parents[1] / "reports" / "affiliate-layout-20260911"
EXPECTED_COUNT = 22


def norm(s: str) -> str:
    return (s or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def sha(s: str) -> str:
    return hashlib.sha256(norm(s).encode("utf-8")).hexdigest()


def load_package():
    posts = []
    files = sorted(PATCH_DIR.glob("patches-*.json"))
    if not files:
        raise RuntimeError("patch package files are missing")
    for path in files:
        part = json.loads(path.read_text(encoding="utf-8"))
        posts.extend(part.get("posts", []))
    if len(posts) != EXPECTED_COUNT:
        raise RuntimeError(f"package count mismatch: {len(posts)}")
    ids = [p["id"] for p in posts]
    if len(ids) != len(set(ids)):
        raise RuntimeError("duplicate post IDs in patch package")
    return {"name": "tsurikue-affiliate-layout-20260911", "post_count": len(posts), "posts": posts}


def apply_patch_to_text(original: str, diff_text: str) -> str:
    source = original if original.endswith("\n") else original + "\n"
    with tempfile.TemporaryDirectory() as td:
        content_path = Path(td) / "content.html"
        patch_path = Path(td) / "change.patch"
        content_path.write_text(source, encoding="utf-8")
        patch_path.write_text(diff_text, encoding="utf-8")
        proc = subprocess.run(["patch", "--batch", "--silent", "-u", str(content_path), "-i", str(patch_path)], capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"local patch failed: {proc.stdout} {proc.stderr}".strip())
        return content_path.read_text(encoding="utf-8")


class WP:
    def __init__(self, site_url: str):
        user = os.environ.get("TSURIKUE_WP_USER")
        password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
        if not user or not password:
            raise RuntimeError("WordPress credentials are missing")
        token = base64.b64encode(f"{user}:{password}".encode()).decode()
        self.site_url = site_url.rstrip("/")
        self.headers = {"Authorization": f"Basic {token}", "User-Agent": "tsurikue-affiliate-layout-20260911/1.0", "Accept": "application/json"}

    def request(self, method: str, path: str, payload=None):
        url = self.site_url + path
        headers = dict(self.headers)
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json; charset=utf-8"
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                body = resp.read().decode("utf-8")
                return (json.loads(body) if body else None), dict(resp.headers.items())
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {e.code} {method} {url}: {body[:1200]}") from e

    def get_post(self, post_id: int):
        obj, _ = self.request("GET", f"/wp-json/wp/v2/posts/{post_id}?context=edit")
        return obj

    def update_content(self, post_id: int, content: str):
        obj, _ = self.request("POST", f"/wp-json/wp/v2/posts/{post_id}", {"content": content})
        return obj

    def public_count(self, kind: str):
        _, headers = self.request("GET", f"/wp-json/wp/v2/{kind}?status=publish&per_page=1&_fields=id")
        for k, v in headers.items():
            if k.lower() == "x-wp-total":
                return int(v)
        raise RuntimeError(f"X-WP-Total missing for {kind}")


def raw_content(post):
    c = post.get("content") or {}
    if isinstance(c, dict):
        if "raw" in c:
            return c.get("raw") or ""
        return c.get("rendered") or ""
    return str(c)


def classify_current(post, spec):
    current_hash = sha(raw_content(post))
    if current_hash == spec["original_sha256"]:
        return "original"
    if current_hash == spec["revised_sha256"]:
        return "revised"
    return "unknown"


def inspect_all(wp, pkg):
    rows, originals = [], {}
    for spec in pkg["posts"]:
        post = wp.get_post(spec["id"])
        current = raw_content(post)
        state = classify_current(post, spec)
        originals[spec["id"]] = current
        rows.append({"id": spec["id"], "slug_expected": spec["slug"], "slug_current": post.get("slug"), "status": post.get("status"), "content_state": state, "content_sha256": sha(current), "title": (post.get("title") or {}).get("raw") or (post.get("title") or {}).get("rendered") or spec["title"]})
    return rows, originals


def validate_preflight(rows):
    errors = []
    for r in rows:
        if r["status"] != "publish":
            errors.append(f"post {r['id']}: status={r['status']} (expected publish)")
        if r["slug_current"] != r["slug_expected"]:
            errors.append(f"post {r['id']}: slug={r['slug_current']} (expected {r['slug_expected']})")
        if r["content_state"] == "unknown":
            errors.append(f"post {r['id']}: current content differs from both reviewed original and reviewed revision")
    states = {r["content_state"] for r in rows}
    if "unknown" not in states and len(states) > 1:
        errors.append(f"mixed content states detected: {sorted(states)}; no writes allowed")
    return errors, states


def write_report(payload):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "result.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# Affiliate layout 2026-09-11", "", f"- result: **{payload['result']}**", f"- mode: `{payload['mode']}`", f"- target posts: **{payload['target_count']}**"]
    if payload.get("public_before"):
        lines += [f"- public posts before/after: **{payload['public_before']['posts']} / {payload.get('public_after', {}).get('posts', '-')}**", f"- public pages before/after: **{payload['public_before']['pages']} / {payload.get('public_after', {}).get('pages', '-')}**"]
    lines.append(f"- updated IDs: `{payload.get('updated_ids', [])}`")
    if payload.get("rolled_back_ids"):
        lines.append(f"- rolled back IDs: `{payload['rolled_back_ids']}`")
    if payload.get("errors"):
        lines += ["", "## Errors"] + [f"- {e}" for e in payload["errors"]]
    lines += ["", "## Per-post verification", "", "|ID|slug|status|state|", "|---:|---|---|---|"]
    for r in payload.get("rows", []):
        lines.append(f"|{r['id']}|{r['slug_current']}|{r['status']}|{r['content_state']}|")
    (REPORT_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["preflight", "apply"], default="preflight")
    args = parser.parse_args()
    pkg = load_package()
    wp = WP(SITE_URL)
    rows, originals = inspect_all(wp, pkg)
    errors, states = validate_preflight(rows)
    public_before = {"posts": wp.public_count("posts"), "pages": wp.public_count("pages")}
    base_report = {"mode": args.mode, "target_count": len(pkg["posts"]), "rows": rows, "public_before": public_before, "updated_ids": [], "rolled_back_ids": [], "errors": errors}
    if errors:
        base_report["result"] = "ABORTED_NO_WRITES"
        write_report(base_report)
        return 2
    if states == {"revised"}:
        base_report["result"] = "ALREADY_APPLIED"
        base_report["public_after"] = public_before
        write_report(base_report)
        return 0
    if states != {"original"}:
        base_report["result"] = "ABORTED_NO_WRITES"
        base_report["errors"].append(f"unexpected state set: {sorted(states)}")
        write_report(base_report)
        return 2
    revised = {}
    for spec in pkg["posts"]:
        generated = apply_patch_to_text(originals[spec["id"]], spec["diff"])
        if sha(generated) != spec["revised_sha256"]:
            base_report["result"] = "ABORTED_NO_WRITES"
            base_report["errors"].append(f"post {spec['id']}: locally generated revision hash mismatch")
            write_report(base_report)
            return 2
        revised[spec["id"]] = generated
    if args.mode == "preflight":
        base_report["result"] = "PREFLIGHT_OK_NO_WRITES"
        base_report["public_after"] = public_before
        write_report(base_report)
        return 0
    updated = []
    try:
        for spec in pkg["posts"]:
            post_id = spec["id"]
            wp.update_content(post_id, revised[post_id])
            check = wp.get_post(post_id)
            if check.get("status") != "publish" or check.get("slug") != spec["slug"] or sha(raw_content(check)) != spec["revised_sha256"]:
                raise RuntimeError(f"post {post_id}: post-write verification failed")
            updated.append(post_id)
    except Exception as apply_error:
        rollback_errors, rolled_back = [], []
        for post_id in reversed(updated):
            try:
                wp.update_content(post_id, originals[post_id])
                check = wp.get_post(post_id)
                spec = next(p for p in pkg["posts"] if p["id"] == post_id)
                if sha(raw_content(check)) != spec["original_sha256"]:
                    raise RuntimeError("rollback hash verification failed")
                rolled_back.append(post_id)
            except Exception as rb_error:
                rollback_errors.append(f"post {post_id}: {rb_error}")
        rows_after, _ = inspect_all(wp, pkg)
        report = dict(base_report)
        report.update({"result": "APPLY_FAILED_ROLLBACK_ATTEMPTED", "updated_ids": updated, "rolled_back_ids": rolled_back, "rows": rows_after, "public_after": {"posts": wp.public_count("posts"), "pages": wp.public_count("pages")}, "errors": [str(apply_error)] + rollback_errors})
        write_report(report)
        return 3
    rows_after, _ = inspect_all(wp, pkg)
    final_errors, final_states = validate_preflight(rows_after)
    public_after = {"posts": wp.public_count("posts"), "pages": wp.public_count("pages")}
    if final_states != {"revised"}:
        final_errors.append(f"final state set is {sorted(final_states)}, expected revised")
    if public_after != public_before:
        final_errors.append(f"public count changed: before={public_before}, after={public_after}")
    report = dict(base_report)
    report.update({"result": "APPLIED_OK" if not final_errors else "APPLIED_BUT_FINAL_VERIFY_FAILED", "updated_ids": updated, "rows": rows_after, "public_after": public_after, "errors": final_errors})
    write_report(report)
    return 0 if not final_errors else 4


if __name__ == "__main__":
    sys.exit(main())
