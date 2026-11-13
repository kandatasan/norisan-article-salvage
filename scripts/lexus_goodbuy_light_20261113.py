"""Small, guarded cleanup of Lexus 'goodbuy' loan and insurance sections.

Touch only three exact paragraph payloads; protect original first-person stories,
title, headings, links, affiliate CTAs, photos, and every other Gutenberg byte.
"""
from __future__ import annotations
from pathlib import Path
import hashlib, html, json, re

POST_ID=3835
SLUG="goodbuy"
TITLE="レクサスを安く買う方法5選｜値引きなしでも購入負担を減らすコツ"
SOURCE_SHA="7e7190b8f2fa275bef401b3586aacf41d8da8442006df80782b48244949bbaf5"
EXPECTED_METADATA={"id":3835,"slug":"goodbuy","status":"publish","featured_media":2231,"categories":[10,11],"author":1}
MARKER="<!-- tsurikue-lexus-goodbuy-light-cleanup:20261113 -->"

CHANGES=[
 (
  '<p>見るのは月々の数字だけじゃなく、借入条件・返済期間・手数料まで含めた<strong>最終的な総支払額</strong>。<br>同じレクサスを買うなら、利息に多く払うより、車やその後の楽しみに残せる方がうれしいです。</p>',
  '<p>たとえば300万円を5年で借りると、金利2％なら利息約15.5万円、4％なら約31.5万円。<strong>差は約16万円。</strong><br>元利均等返済・ボーナス払いなし・手数料なしの概算ですが、金利だけでもこれだけ違います。</p>'
 ),
 (
  '<p>車両価格だけがカーライフのお金ではありません。</p>',
  '<p>保険は車両価格の値引きではありません。でも、乗り始めてからの固定費は減らせます。</p>'
 ),
 (
  '<p>補償内容をそろえて比べて、納得できる保険料を探す。<br>私の例と同じ月5,000円差なら、年間6万円、5年で30万円です。</p>',
  '<p>比較するときは、車両保険などの補償内容もそろえておきたいところです。</p>'
 )
]

def sha(s:str)->str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def meta(row):
    return {k:row.get(k) for k in EXPECTED_METADATA}

def signature(body:str):
    return {
        "images":re.findall(r'<!-- wp:image\b.*?<!-- /wp:image -->',body,re.S),
        "tables":re.findall(r'<!-- wp:table\b.*?<!-- /wp:table -->',body,re.S),
        "headings":re.findall(r'<!-- wp:heading\b.*?<!-- /wp:heading -->',body,re.S),
        "lists":re.findall(r'<!-- wp:list(?: |\b).*?<!-- /wp:list -->',body,re.S),
        "shortcodes":re.findall(r'\[blog_parts id="\d+"\]',body),
        "urls":re.findall(r'href="([^"]+)"',body),
        "iframe":re.findall(r'<iframe\b.*?</iframe>',body,re.S),
        "paragraph_count":body.count('<!-- wp:paragraph'),
        "html_blocks":re.findall(r'<!-- wp:html(?: [^\n]*?)? -->.*?<!-- /wp:html -->',body,re.S),
    }

def transform(source:str)->str:
    if MARKER in source:
        if (source.count(MARKER)==1 and source.count("金利2％なら利息約15.5万円")==1
            and source.count("補償内容もそろえておきたいところです")==1 and source.count('[blog_parts id="4521"]')==1):
            return source
        raise RuntimeError("Partial goodbuy edit marker")
    if sha(source)!=SOURCE_SHA:
        raise RuntimeError("Published goodbuy body no longer matches approved original; abort")
    updated=source
    for old,new in CHANGES:
        if updated.count(old)!=1:
            raise RuntimeError(f"Expected exactly one target paragraph: {old[:70]}")
        updated=updated.replace(old,new,1)
    # Replacing these same three blocks back MUST recover original byte-for-byte.
    rewind=updated
    for old,new in CHANGES:
        if rewind.count(new)!=1:raise RuntimeError("Patch not reversible")
        rewind=rewind.replace(new,old,1)
    if rewind!=source or sha(rewind)!=SOURCE_SHA:
        raise RuntimeError("Unexpected change to original first-person story")
    before,after=signature(source),signature(updated)
    if before!=after:
        raise RuntimeError("Other Gutenberg blocks, links or affiliates changed")
    if '私の例と同じ月5,000円差なら' in updated or '月5,000円' not in updated:
        raise RuntimeError("Insurance savings should appear exactly once")
    if not ('シエンタ' in updated and '三眼フルLED' in updated and '27万5,000円' in updated and '友人' in updated):
        raise RuntimeError("Owner anecdotes unexpectedly lost")
    return MARKER+"\n"+updated

def apply(config_path:Path,cfg:dict,auth:str,api):
    if (cfg.get("operation"),cfg.get("post_id"),cfg.get("slug"),cfg.get("expected_sha256"))!=(
        "cleanup_lexus_goodbuy_light_20261113",POST_ID,SLUG,SOURCE_SHA
    ):raise RuntimeError("Goodbuy edit config mismatch")
    fetch_post,raw_field,public_counts,post_json,site_url=api
    before=fetch_post(POST_ID,auth)
    if meta(before)!=EXPECTED_METADATA:raise RuntimeError("Protected post identity changed")
    if html.unescape(raw_field(before,'title'))!=TITLE:raise RuntimeError("Title changed")
    original=raw_field(before,'content')
    revised=transform(original)
    counts=public_counts(auth)
    fresh=fetch_post(POST_ID,auth)
    if meta(fresh)!=meta(before) or raw_field(fresh,'content')!=original or raw_field(fresh,'title')!=raw_field(before,'title'):
        raise RuntimeError("Concurrent WordPress edit; do not overwrite")
    action="ALREADY_PRESENT" if revised==original else "UPDATE"
    if action=="UPDATE":
        resp=post_json(site_url+"/wp-json/wp/v2/posts/"+str(POST_ID),auth,{"content":revised})
        if meta(resp)!=EXPECTED_METADATA:raise RuntimeError("Post metadata unexpectedly changed in save response")
    saved=fetch_post(POST_ID,auth)
    if meta(saved)!=EXPECTED_METADATA or html.unescape(raw_field(saved,'title'))!=TITLE:
        raise RuntimeError("Saved title/metadata changed")
    if raw_field(saved,'content')!=revised:
        raise RuntimeError("Saved WordPress body does not match revision")
    counts_after=public_counts(auth)
    if counts_after!=counts:raise RuntimeError("Site published count unexpectedly changed")
    report={
        "post_id":POST_ID,"slug":SLUG,"title":TITLE,"status":"publish",
        "action":action,"writes":int(action=="UPDATE"),
        "original_sha256":sha(original),"revised_sha256":sha(revised),
        "replaced_paragraphs":3,"other_original_bytes_identical":True,
        "original_images":len(signature(original)["images"]),
        "original_tables":len(signature(original)["tables"]),
        "affiliate_parts":signature(revised)["shortcodes"],
        "before_counts":counts,"after_counts":counts_after
    }
    dest=Path("reports/lexus-goodbuy-light-20261113");dest.mkdir(parents=True,exist_ok=True)
    (dest/"result.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (dest/"summary.md").write_text("# Lexus goodbuy tiny cleanup\n\n"+json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("LEXUS_GOODBUY_LIGHT_RESULT",json.dumps(report,ensure_ascii=False),flush=True)
    return report
