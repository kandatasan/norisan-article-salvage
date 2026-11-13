"""Change only Lexus goodbuy CTA placements to the current standard CTN/Gulliver exits.

CTN common part 4521 is ALREADY in this article; leave it untouched.
Remove an old Gulliver banner in option section and replace the old Gulliver
button + microcopy with the published latest purchasing funnel (part 4507).
All other original post bytes must be preserved.
"""
from __future__ import annotations
import hashlib
import html
import json
import re
from pathlib import Path

POST_ID=3835
SLUG="goodbuy"
TITLE="レクサスを安く買う方法5選｜値引きなしでも購入負担を減らすコツ"
CONTENT_SHA="49ac985c9d157c9384d125a673e9188e94997e055c6f995f8fb126ee892024ad"
IDENTITY={"id":3835,"slug":"goodbuy","status":"publish","featured_media":2231,"categories":[10,11],"author":1}
BANNER_MARKER="<!-- tsurikue-goodbuy-retired-old-gulliver-banner:20261113 -->"
FUNNEL_MARKER="<!-- tsurikue-goodbuy-gulliver-exit-v2:20261113 -->"
NEW_FUNNEL=FUNNEL_MARKER+'\n<!-- wp:shortcode -->\n[blog_parts id="4507"]\n<!-- /wp:shortcode -->'

BANNER_PATTERN=re.compile(r'<!-- wp:shortcode -->\s*\[blog_parts id="2843"\]\s*<!-- /wp:shortcode -->')
OLD_FUNNEL_PATTERN=re.compile(
    r'<!-- wp:html -->\s*<div class="tsq-gulliver-micro-20261014 top"[\s\S]*?<!-- /wp:html -->'
    r'\s*<!-- wp:shortcode -->\s*\[blog_parts id="4172"\]\s*<!-- /wp:shortcode -->'
    r'\s*<!-- wp:html -->\s*<div class="tsq-gulliver-micro-20261014 bottom"[\s\S]*?<!-- /wp:html -->'
)

def sha(body:str)->str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()

def safe_identity(row:dict)->dict:
    return {k:row.get(k) for k in IDENTITY}

def protected(body:str)->dict:
    return {
        "headings":re.findall(r'<!-- wp:heading\b.*?<!-- /wp:heading -->',body,re.S),
        "original_table_blocks":re.findall(r'<!-- wp:table\b.*?<!-- /wp:table -->',body,re.S),
        "original_image_blocks":re.findall(r'<!-- wp:image\b.*?<!-- /wp:image -->',body,re.S),
        "original_list_blocks":re.findall(r'<!-- wp:list(?:\s|>).*?<!-- /wp:list -->',body,re.S),
        "original_paragraph_blocks":re.findall(r'<!-- wp:paragraph\b.*?<!-- /wp:paragraph -->',body,re.S),
        "affiliate_CTN":body.count('[blog_parts id="4521"]'),
        "links":re.findall(r'href="([^"]+)"',body),
        "word_count":body.count('シエンタ'),
        "old_purchase_parts":sorted(re.findall(r'\[blog_parts id="(?:2843|4172)"\]',body)),
    }

def transform(source:str)->str:
    if BANNER_MARKER in source or FUNNEL_MARKER in source:
        if (source.count(BANNER_MARKER)==source.count(FUNNEL_MARKER)==1
            and source.count('[blog_parts id="4521"]')==1
            and source.count('[blog_parts id="4507"]')==1
            and '[blog_parts id="2843"]' not in source
            and '[blog_parts id="4172"]' not in source):
            return source
        raise RuntimeError("Incomplete or duplicated CTA replacement markers")
    if sha(source)!=CONTENT_SHA:raise RuntimeError("Goodbuy WordPress body drifted; refusing to overwrite other edits")
    if source.count('[blog_parts id="4521"]')!=1:raise RuntimeError("Latest CTN blog part 4521 is missing")
    if source.count('[blog_parts id="2843"]')!=1 or source.count('[blog_parts id="4172"]')!=1:
        raise RuntimeError("Legacy Gulliver parts 2843 and 4172 not uniquely present")
    if '[blog_parts id="4507"]' in source:raise RuntimeError("New Gulliver part already embedded unexpectedly")
    old_banner=list(BANNER_PATTERN.finditer(source))
    old_funnel=list(OLD_FUNNEL_PATTERN.finditer(source))
    if len(old_banner)!=1 or len(old_funnel)!=1:raise RuntimeError("Exactly one old banner and one old funnel expected")
    a,b=old_banner[0],old_funnel[0]
    if not (a.end()<b.start()):raise RuntimeError("Banner and purchase funnel locations inconsistent")
    method4=source.find("方法4｜不要なオプション")
    method5=source.find("方法5｜新車が予算を超えるなら")
    summary=source.find("レクサスを安く買う方法は「一番安い仕様")
    if not (method4<a.start()<method5<b.start()<summary):
        raise RuntimeError("Unexpected source section layout; abort")
    old_banner_text=a.group(0)
    old_funnel_text=b.group(0)
    # Replacing later range first keeps earlier offsets reliable.
    result=source[:b.start()]+NEW_FUNNEL+source[b.end():]
    result=result[:a.start()]+BANNER_MARKER+result[a.end():]
    if result.count('[blog_parts id="4521"]')!=1 or result.count('[blog_parts id="4507"]')!=1:
        raise RuntimeError("New CTN and Gulliver placements missing or duplicated")
    if '[blog_parts id="2843"]' in result or '[blog_parts id="4172"]' in result:
        raise RuntimeError("Old Gulliver ads remain")
    # Formal complete byte-for-byte preservation of every unrelated block.
    rewound=result.replace(BANNER_MARKER,old_banner_text,1).replace(NEW_FUNNEL,old_funnel_text,1)
    if rewound!=source or sha(rewound)!=CONTENT_SHA:
        raise RuntimeError("Original body outside two CTA regions unexpectedly changed")
    check_a,check_b=protected(source),protected(result)
    for key in ("headings","original_table_blocks","original_image_blocks","original_list_blocks","original_paragraph_blocks","affiliate_CTN","links","word_count"):
        if check_a[key]!=check_b[key]:raise RuntimeError(f"Unintended original content mutation: {key}")
    return result

def apply_exit_design(config_path:Path,cfg:dict,auth:str,api):
    if (cfg.get('operation'),cfg.get('post_id'),cfg.get('slug'),cfg.get('expected_sha256')) != (
        'replace_goodbuy_outlets_20261113',POST_ID,SLUG,CONTENT_SHA):
        raise RuntimeError('Invalid CTA-only editing config')
    fetch_post,raw_field,public_counts,post_json,site_url,get_json=api
    before=fetch_post(POST_ID,auth)
    if safe_identity(before)!=IDENTITY:raise RuntimeError('Protected post identity/status changed')
    if html.unescape(raw_field(before,'title'))!=TITLE:raise RuntimeError('Title changed')
    original=raw_field(before,'content')
    revised=transform(original)
    # Confirm both existing WP blog parts are published and carry correct approved copy.
    for part_id,needles in [
        (4521,("複数社で比べるから、高値が出やすい。","お試しだけでもOK！","【CTN一括車査定】","最大でも3社まで")),
        (4507,("カーセンサーでUXの中古相場を見る","ガリバーなら一般公開前の車両も探せる！","ガリバーで希望のUXを探してみる","4B65SD+8DUSHE+9QU+NVHCY"))
    ]:
        part,_=get_json(f"{site_url}/wp-json/wp/v2/blog_parts/{part_id}?context=edit&_fields=id,status,title,content",auth)
        if part.get("id")!=part_id or part.get("status")!="publish":
            raise RuntimeError(f"Reusable outlet blog part {part_id} not published")
        content=raw_field(part,'content')
        if any(phrase not in content for phrase in needles):
            raise RuntimeError(f"Reusable outlet blog part {part_id} changed")
    counts_before=public_counts(auth)
    fresh=fetch_post(POST_ID,auth)
    if safe_identity(fresh)!=IDENTITY or raw_field(fresh,'content')!=original or raw_field(fresh,'title')!=raw_field(before,'title'):
        raise RuntimeError('WordPress article was edited concurrently')
    action="ALREADY_PRESENT" if revised==original else "UPDATE"
    if action=="UPDATE":
        response=post_json(site_url+"/wp-json/wp/v2/posts/"+str(POST_ID),auth,{"content":revised})
        if safe_identity(response)!=IDENTITY:raise RuntimeError('WordPress save response changed post metadata')
    after=fetch_post(POST_ID,auth)
    if safe_identity(after)!=IDENTITY or html.unescape(raw_field(after,'title'))!=TITLE:
        raise RuntimeError('Unexpected post metadata/title change after save')
    if raw_field(after,'content')!=revised:raise RuntimeError('Saved WP body does not match approved CTA replacement')
    rendered=(after.get('content') or {}).get('rendered') or ''
    if rendered:
        if ('ガリバーなら一般公開前の車両も探せる！' not in rendered
            or 'お試しだけでもOK！' not in rendered
            or 'ガリバーで希望のUXを探してみる' not in rendered
            or 'data-partsID="4507"' not in rendered
            or 'data-partsID="4521"' not in rendered):
            raise RuntimeError('Rendered WordPress body does not contain both latest expanded CTA components')
    counts_after=public_counts(auth)
    if counts_before!=counts_after:raise RuntimeError('Unexpected site-wide published count difference')
    report={
        "post_id":POST_ID,"slug":SLUG,"status":"publish","title":TITLE,
        "action":action,"writes":int(action=="UPDATE"),
        "source_sha256":sha(original),"new_sha256":sha(revised),
        "ctn_latest_blog_part":4521,"gulliver_latest_blog_part":4507,
        "retired_gulliver_parts":[2843,4172],
        "all_non_CTA_original_text_preserved":True,
        "original_images":len(protected(original)["original_image_blocks"]),
        "original_tables":len(protected(original)["original_table_blocks"]),
        "original_paragraphs":len(protected(original)["original_paragraph_blocks"]),
        "rendered_cta_verified":bool(rendered),
        "published_count_before":counts_before,"published_count_after":counts_after,
    }
    dest=Path('reports/goodbuy-new-ctn-gulliver-20261113');dest.mkdir(parents=True,exist_ok=True)
    (dest/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (dest/'summary.md').write_text('# Lexus goodbuy new exit designs\n\n'+json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('GOODBUY_EXIT_RESULT',json.dumps(report,ensure_ascii=False),flush=True)
    return report
