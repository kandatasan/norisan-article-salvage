#!/usr/bin/env python3
from __future__ import annotations

import base64, hashlib, html, json, os, re, time, urllib.parse, urllib.request
from pathlib import Path
from typing import Any

SITE_URL="https://tsurikue.com"
USER_AGENT="tsurikue-internal-links-20260905/1.0"
REPORT_DIR=Path("reports/internal-links-20260905")

PATCHES: list[dict[str, Any]] = [
  {
    "id":2983,"endpoint":"pages","slug":"","title":"トップページ",
    "sha":"3312a2dfe3d719412144ca96c9196e5ce84e50fc6e04bd4938e66d712744d0a3",
    "ops":[["replace",'href="/gourmet-guide/"','href="/gourmet/"',3]],
    "targets":["gourmet"],"old_paths":["gourmet-guide"]
  },
  {
    "id":1911,"endpoint":"posts","slug":"hiroshima-bokujyou","title":"広島の遊べる牧場でジェラート食べ比べ！子連れ・ドライブにおすすめ",
    "sha":"01e9cf1e029d4adaa0583bc66adc1cc502e5acb17a372d9f514fb0f89ceeef54",
    "ops":[
      ["replace",'href="https://tsurikue.com/serakankou/"','href="https://tsurikue.com/sera-sightseeing/"',1],
      ["replace",'href="https://tsurikue.com/yukinoasobiba/"','href="https://tsurikue.com/yuki-town-drive/"',1],
      ["insert_after",'<!-- wp:paragraph -->\n<p><a href="https://www.cadore.jp/" target="_blank" rel="noopener">上ノ原牧場カドーレ公式サイト</a></p>\n<!-- /wp:paragraph -->','<!-- wp:paragraph -->\n<p>動物との距離感やジェラート、営業時間まで詳しく見るなら、<a href="https://tsurikue.com/cadore-fukutomi/">上ノ原牧場カドーレの体験記事</a>にまとめています。</p>\n<!-- /wp:paragraph -->',1],
      ["replace",'<p>カドーレ周辺には、道の駅「湖畔の里 福富」もあります。大きな遊具があるので、<strong>牧場で動物を見る → ジェラート → 道の駅で遊ぶ</strong>まで組みやすいです。</p>','<p>カドーレ周辺には、<a href="https://tsurikue.com/kohannosato-fukutomi/">道の駅「湖畔の里 福富」</a>もあります。大きな遊具があるので、<strong>牧場で動物を見る → ジェラート → 道の駅で遊ぶ</strong>まで組みやすいです。</p>',1]
    ],
    "targets":["sera-sightseeing","yuki-town-drive","cadore-fukutomi","kohannosato-fukutomi"],
    "old_paths":["serakankou","yukinoasobiba"]
  },
  {
    "id":2041,"endpoint":"posts","slug":"hiroshima-sightseeing","title":"広島観光・レジャーまとめ｜車で行ける日帰りドライブ先を紹介",
    "sha":"c1907ff6f614ff621588c7dc5627c976dc2e97e710fcebfc597e951fc9736de3",
    "ops":[
      ["insert_after",'<p>海沿いドライブまで楽しむなら<a href="https://tsurikue.com/etajima-sightseeing/">江田島観光まとめ</a>へ。広島市中心部では、実際に行って料金も含めて本音で書いた<a href="https://tsurikue.com/orizuru-tower/">おりづるタワー体験記</a>もあります。</p>\n<!-- /wp:paragraph -->','<!-- wp:paragraph -->\n<p>秋に広島市内で紅葉を楽しむなら、<a href="https://tsurikue.com/mitakidera-autumn/">三滝寺を妻と母と歩いた紅葉散策</a>もあります。遠出しすぎず秋を楽しみたい日にちょうどいい場所でした。</p>\n<!-- /wp:paragraph -->',1]
    ],
    "targets":["mitakidera-autumn"],"old_paths":[]
  },
  {
    "id":2664,"endpoint":"posts","slug":"yamaguchi-drive","title":"山口観光1泊2日モデルコース｜広島発ドライブでムーバレー・萩・元乃隅・角島へ",
    "sha":"b52300362cf93bbb8096bfcea1b1ff02683b9665cda90c0bec0a086f74b6c4b1",
    "ops":[
      ["replace",'<p>秋吉台からも行きやすい場所にある別府弁天池。</p>','<p>秋吉台からも行きやすい場所にある<a href="https://tsurikue.com/beppu-benten-ike/">別府弁天池</a>。</p>',1]
    ],
    "targets":["beppu-benten-ike"],"old_paths":[]
  },
  {
    "id":3540,"endpoint":"posts","slug":"kohannosato-fukutomi","title":"道の駅 湖畔の里福富は巨大遊具がすごい！公園で遊べる東広島の道の駅",
    "sha":"0d26b27bdc76dffad782e9e28f0bf09fa59496f3c11b60b93b00b9f8637e68de",
    "ops":[
      ["replace",'<p>近くには<strong>上ノ原牧場カドーレ</strong>や<strong>十夢ミルクファーム</strong>があります。</p>','<p>近くには<strong><a href="https://tsurikue.com/cadore-fukutomi/">上ノ原牧場カドーレ</a></strong>や<strong>十夢ミルクファーム</strong>があります。</p>',1]
    ],
    "targets":["cadore-fukutomi"],"old_paths":[]
  },
  {
    "id":3514,"endpoint":"posts","slug":"mitakidera-autumn","title":"広島・三滝寺（三瀧寺）の紅葉｜2025年11月の色づきと秋の境内を散策",
    "sha":"79c4e70d1ad7f88fdf268a6d6960cf9c6841645925a0231aba7c0f4dabd1630e",
    "ops":[
      ["insert_after",'<p>コンパクトだけど、紅葉もお寺も瀧もある。<br><strong>近場で秋らしい景色をのんびり楽しみたい日に、かなり良い場所でした。</strong></p>\n<!-- /wp:paragraph -->','<!-- wp:paragraph -->\n<p>三滝寺以外の広島の休日候補は、<a href="https://tsurikue.com/hiroshima-sightseeing/">広島観光・レジャーまとめ</a>に整理しています。</p>\n<!-- /wp:paragraph -->',1]
    ],
    "targets":["hiroshima-sightseeing"],"old_paths":[]
  },
  {
    "id":2222,"endpoint":"posts","slug":"ux-resale","title":"レクサスUXのリセールは？616万円で購入し427万円で売却した記録",
    "sha":"a6869c05399c4edeb52811ff4728117b79c0d635e159647b4cc1747deda536fe",
    "ops":[
      ["replace",'<p>なお、購入額616万円にはオプションや諸費用も含まれます。616万円と427万円の差を、そのまま車両本体の値下がりとして見ることはできません。</p>','<p>なお、<a href="https://tsurikue.com/ux-mitsumori/">購入額616万円の見積もり内訳</a>にはオプションや諸費用も含まれます。616万円と427万円の差を、そのまま車両本体の値下がりとして見ることはできません。</p>',1]
    ],
    "targets":["ux-mitsumori"],"old_paths":[]
  }
]

def auth_header(user:str,password:str)->str:
    return "Basic "+base64.b64encode(f"{user}:{password}".encode()).decode()

def request_json(url:str,auth:str,method:str="GET",payload:dict[str,Any]|None=None):
    data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode("utf-8")
    headers={"Accept":"application/json","Authorization":auth,"User-Agent":USER_AGENT}
    if data is not None: headers["Content-Type"]="application/json; charset=utf-8"
    last=None
    for attempt in range(3):
        try:
            req=urllib.request.Request(url,data=data,headers=headers,method=method)
            with urllib.request.urlopen(req,timeout=60) as r:
                return json.loads(r.read().decode("utf-8")),dict(r.headers)
        except Exception as e:
            last=e
            if attempt<2: time.sleep(2*(attempt+1))
    raise last

def raw(row:dict[str,Any],key:str)->str:
    v=row.get(key) or {}
    return (v.get("raw") or v.get("rendered") or "") if isinstance(v,dict) else str(v)

def fetch_doc(patch,auth):
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,content,featured_media"})
    row,_=request_json(f"{SITE_URL}/wp-json/wp/v2/{patch['endpoint']}/{patch['id']}?{q}",auth)
    return row

def all_published_slugs(auth:str)->set[str]:
    out=set()
    for endpoint in ("posts","pages"):
        page=1
        while True:
            q=urllib.parse.urlencode({"context":"edit","status":"publish","per_page":"100","page":str(page),"_fields":"slug"})
            rows,h=request_json(f"{SITE_URL}/wp-json/wp/v2/{endpoint}?{q}",auth)
            out.update(str(x.get("slug") or "") for x in rows)
            if page>=int(h.get("X-WP-TotalPages","1")): break
            page+=1
    return out

def count_published(endpoint:str,auth:str)->int:
    q=urllib.parse.urlencode({"context":"edit","status":"publish","per_page":"1","_fields":"id"})
    _,h=request_json(f"{SITE_URL}/wp-json/wp/v2/{endpoint}?{q}",auth)
    return int(h.get("X-WP-Total","0"))

def public_counts(auth:str)->dict[str,int]:
    p=count_published("posts",auth); g=count_published("pages",auth)
    return {"posts":p,"pages":g,"total":p+g}

def media_ids(content:str)->list[int]:
    out=[]
    for m in re.finditer(r'wp-image-(\d+)|"id"\s*:\s*(\d+)',content):
        n=int(m.group(1) or m.group(2))
        if n not in out: out.append(n)
    return out

def internal_slugs(content:str)->set[str]:
    out=set()
    for href in re.findall(r'<a\b[^>]*\bhref=["\']([^"\']+)["\']',content,re.I):
        p=urllib.parse.urlsplit(html.unescape(href))
        if href.startswith("/") or (p.hostname or "").lower() in {"tsurikue.com","www.tsurikue.com"}:
            path=p.path.strip("/")
            if path: out.add(path.split("/")[-1])
    return out

def transform(content:str,patch)->str:
    desired=content
    for kind,a,b,count in patch["ops"]:
        actual=desired.count(a)
        if actual!=count:
            raise RuntimeError(f"{patch['id']}: expected {count} occurrence(s), found {actual}")
        if kind=="replace":
            desired=desired.replace(a,b,count)
        elif kind=="insert_after":
            desired=desired.replace(a,a+"\n\n"+b,count)
        else:
            raise RuntimeError(f"unsupported op: {kind}")
    return desired

def write_report(r):
    REPORT_DIR.mkdir(parents=True,exist_ok=True)
    (REPORT_DIR/"result.json").write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=["# Internal links 2026-09-05","",f"- result: **{r['result']}**",f"- planned_documents: **{r['planned_documents']}**",f"- updated_documents: **{r['updated_documents']}**",f"- public_before: **{r.get('public_before')}**",f"- public_after: **{r.get('public_after')}**","", "## Documents",""]
    for x in r.get("documents",[]):
        lines.append(f"- {x['id']} \`{x['slug'] or '/'}\` — **{x['result']}**")
        if x.get("error"): lines.append(f"  - error: \`{x['error']}\`")
    if r.get("error"): lines += ["",f"- error: \`{r['error']}\`"]
    (REPORT_DIR/"summary.md").write_text("\n".join(lines)+"\n",encoding="utf-8")

def main()->int:
    report={"result":"BLOCKED","planned_documents":len(PATCHES),"updated_documents":0,"wordpress_write_count":0,"documents":[],"public_before":"unknown","public_after":"unknown"}
    try:
        user=os.environ.get("TSURIKUE_WP_USER"); password=os.environ.get("TSURIKUE_WP_APP_PASSWORD")
        if not user or not password: raise RuntimeError("missing WordPress secrets")
        auth=auth_header(user,password)
        before=public_counts(auth); report["public_before"]=before["total"]
        published=all_published_slugs(auth)

        preflight=[]
        for patch in PATCHES:
            missing=[x for x in patch["targets"] if x not in published]
            if missing: raise RuntimeError(f"{patch['id']}: destination not published: {missing}")
            row=fetch_doc(patch,auth); current=raw(row,"content"); title=html.unescape(raw(row,"title"))
            if int(row.get("id") or 0)!=patch["id"]: raise RuntimeError(f"{patch['id']}: id mismatch")
            if patch["endpoint"]=="posts" and row.get("slug")!=patch["slug"]: raise RuntimeError(f"{patch['id']}: slug mismatch")
            if row.get("status")!="publish": raise RuntimeError(f"{patch['id']}: source not publish")
            if title!=patch["title"]: raise RuntimeError(f"{patch['id']}: title changed")
            sha=hashlib.sha256(current.encode()).hexdigest()
            if sha!=patch["sha"]: raise RuntimeError(f"{patch['id']}: content hash changed: {sha}")
            desired=transform(current,patch)
            for old in patch["old_paths"]:
                if old in internal_slugs(desired): raise RuntimeError(f"{patch['id']}: old path remains: {old}")
            for target in patch["targets"]:
                if target not in internal_slugs(desired): raise RuntimeError(f"{patch['id']}: intended target missing in desired content: {target}")
            preflight.append((patch,row,current,desired,media_ids(current),int(row.get("featured_media") or 0)))

        for patch,before_row,current,desired,before_media,before_featured in preflight:
            rec={"id":patch["id"],"slug":patch["slug"],"result":"BLOCKED"}
            try:
                response,_=request_json(f"{SITE_URL}/wp-json/wp/v2/{patch['endpoint']}/{patch['id']}",auth,method="POST",payload={"content":desired,"status":"publish"})
                if int(response.get("id") or 0)!=patch["id"] or response.get("status")!="publish": raise RuntimeError("update response validation failed")
                after=fetch_doc(patch,auth); after_content=raw(after,"content")
                if after.get("status")!="publish": raise RuntimeError("status changed after update")
                if html.unescape(raw(after,"title"))!=patch["title"]: raise RuntimeError("title changed after update")
                if int(after.get("featured_media") or 0)!=before_featured: raise RuntimeError("featured_media changed")
                if media_ids(after_content)!=before_media: raise RuntimeError("media ids changed")
                if after_content.strip()!=desired.strip(): raise RuntimeError("content mismatch after update")
                rec["result"]="SUCCESS"; rec["after_sha"]=hashlib.sha256(after_content.encode()).hexdigest()
                report["updated_documents"]+=1; report["wordpress_write_count"]+=1
            except Exception as e:
                rec["error"]=str(e); report["documents"].append(rec); raise
            report["documents"].append(rec)

        after_counts=public_counts(auth); report["public_after"]=after_counts["total"]
        if after_counts!=before: raise RuntimeError(f"published counts changed: {before} -> {after_counts}")
        report["result"]="SUCCESS"
        write_report(report); print(json.dumps(report,ensure_ascii=False,indent=2)); return 0
    except Exception as e:
        report["error"]=str(e)
        try:
            if report["public_before"]!="unknown" and report["public_after"]=="unknown":
                report["public_after"]=public_counts(auth)["total"]
        except Exception: pass
        write_report(report); print(json.dumps(report,ensure_ascii=False,indent=2)); return 1

if __name__=="__main__":
    raise SystemExit(main())
