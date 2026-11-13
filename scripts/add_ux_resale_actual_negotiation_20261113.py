"""Follow-up from UX owner: the negotiation described as hypothetical really happened.

Insert only the owner's confirmed telephone exchange into already published resale article.
Do not manufacture a company-specific bid, onsite-appraisal count, or outcome.
"""
from __future__ import annotations
from pathlib import Path
import hashlib, html, json, re

POST_ID=2222
SLUG="ux-resale"
TITLE="レクサスUXのリセールは？616万円→427万円、残価率69.3％の売却記録"
EXPECTED_SHA="8498af9ce4a0009533f5ed9be09a867f5c62aec164e0745ce58de28c32e4fcf2"
MARKER="<!-- tsurikue-ux-resale-real-negotiation:20261113 -->"
PARA=re.compile(r'<!-- wp:paragraph(?: [^\n]*?)? -->\s*<p[^>]*>.*?</p>\s*<!-- /wp:paragraph -->', re.S)
BEFORE_ANCHOR="CTNは条件に合う買取店を選び、やり取りは"
NEXT_ANCHOR="カーセブンとネクステージには、どちらにも実際のUXを見てもらいました。"

def digest(body:str)->str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()

def para(text:str)->str:
    return "<!-- wp:paragraph -->\n<p>"+text+"</p>\n<!-- /wp:paragraph -->"

def h3(title:str)->str:
    return '<!-- wp:heading {"level":3} -->\n<h3 class="wp-block-heading">'+title+'</h3>\n<!-- /wp:heading -->'

def protected(body:str)->dict:
    return {
        "wp_image_ids":sorted(re.findall(r'wp-image-(\d+)',body)),
        "image_blocks":body.count("<!-- wp:image"),
        "featured":body.count("wp-image-2231"),
        "table_blocks":re.findall(r'<!-- wp:table\b.*?<!-- /wp:table -->',body,re.S),
        "links":sorted(re.findall(r'href="([^"]+)"',body)),
        "shortcodes":sorted(re.findall(r'\[blog_parts id="\d+"\]',body)),
        "embed_blocks":body.count("<!-- wp:embed"),
        "lists":body.count("<!-- wp:list"),
        "headings":body.count("<!-- wp:heading")
    }

def transform(source:str)->str:
    if MARKER in source:
        if source.count(MARKER)==1 and source.count("ぶっちゃけ、いくらぐらいになりそうですか？")==1 and source.count('[blog_parts id="4521"]')==1:
            return source
        raise RuntimeError("Existing negotiation edit is partial")
    if digest(source)!=EXPECTED_SHA:
        raise RuntimeError("Live WordPress UX resale content drifted; no overwrite")
    if source.count(BEFORE_ANCHOR)!=1 or source.count(NEXT_ANCHOR)!=1:
        raise RuntimeError(f"CTN history anchor not unique: telephone={source.count(BEFORE_ANCHOR)}, onsite={source.count(NEXT_ANCHOR)}")
    items=[m for m in PARA.finditer(source) if BEFORE_ANCHOR in html.unescape(re.sub(r'<[^>]*>','',m.group(0)))]
    next_items=[m for m in PARA.finditer(source) if NEXT_ANCHOR in html.unescape(re.sub(r'<[^>]*>','',m.group(0)))]
    if len(items)!=1 or len(next_items)!=1 or items[0].end()>next_items[0].start():
        raise RuntimeError("Expected telephone setup before vehicle inspections")
    if source[items[0].end():next_items[0].start()].strip():
        raise RuntimeError("Unexpected block between negotiation and onsite paragraph")
    insert=[
        MARKER,
        h3('私が実際にやった交渉｜まず「ぶっちゃけ、いくら？」'),
        para('まず電話で聞いたのが、<br><strong>「ぶっちゃけ、いくらぐらいになりそうですか？」</strong><br>金額の感触と、どの会社が買いたがっているかを探りました。'),
        para('そのあと、手応えのあった会社へこう伝えました。<br>「大体どこも同じ金額ですよね。正直、手間と時間が惜しいので、現地査定は一社にしたい。他社に負けない金額が出せそうなら、他社の現地査定を断ろうと思う」'),
        para('これ、売却後に考えた交渉術じゃなくて、<strong>私がUXを売るときに実際にやった話</strong>です。<br>現地査定を一社に絞りたいと伝えたうえで、結果的には2社ともUXを見てもらいました。'),
    ]
    updated=source[:items[0].end()]+'\n\n'+'\n\n'.join(insert)+'\n\n'+source[items[0].end():]
    before,after=protected(source),protected(updated)
    for field in ["wp_image_ids","image_blocks","featured","table_blocks","links","shortcodes","embed_blocks","lists"]:
        if before[field]!=after[field]:
            raise RuntimeError(f"Unexpected original source change: {field}")
    if after["headings"]!=before["headings"]+1:
        raise RuntimeError("Only one new H3 is allowed")
    if updated.count('2025年2月')!=source.count('2025年2月'):
        raise RuntimeError("Original sale timing unintentionally changed")
    if updated.count('427万円')!=source.count('427万円'):
        raise RuntimeError("Original sale amount unintentionally changed")
    if updated.count('435万円')!=source.count('435万円'):
        raise RuntimeError("Earlier independent appraisal amount unexpectedly changed")
    if updated.count('<!-- wp:paragraph')!=source.count('<!-- wp:paragraph')+3:
        raise RuntimeError("Unexpected paragraph modification")
    if updated.count('一社にしたい')!=1 or updated.count('ぶっちゃけ、いくらぐらいになりそうですか？')!=1:
        raise RuntimeError("Confirmed owner negotiation dialogue missing")
    return updated

def apply_negotiation(config_path:Path,config:dict,auth:str,api):
    if (config.get("operation"),config.get("post_id"),config.get("slug"),config.get("expected_sha256")) != (
        "add_ux_resale_actual_negotiation_20261113", POST_ID, SLUG, EXPECTED_SHA):
        raise RuntimeError("Wrong target config for published UX resale history")
    fetch_post,raw_field,public_counts,post_json,site_url=api
    current=fetch_post(POST_ID,auth)
    for k,v in [("id",POST_ID),("slug",SLUG),("status","publish"),("featured_media",2223),("author",1),("categories",[10,11])]:
        if current.get(k)!=v: raise RuntimeError(f"WordPress post identity differs: {k}")
    if html.unescape(raw_field(current,"title"))!=TITLE:
        raise RuntimeError("Published article title was modified")
    before=raw_field(current,"content")
    after=transform(before)
    counts=public_counts(auth)
    again=fetch_post(POST_ID,auth)
    for k in ["id","slug","status","title","featured_media","categories","author"]:
        if current.get(k)!=again.get(k): raise RuntimeError(f"Concurrent edit to {k}")
    if before!=raw_field(again,"content"): raise RuntimeError("Concurrent edit to article body")
    action="ALREADY_PRESENT" if after==before else "UPDATE"
    if action=="UPDATE":
        response=post_json(site_url+"/wp-json/wp/v2/posts/"+str(POST_ID),auth,{"content":after})
        if (response.get("id"),response.get("status"),response.get("featured_media")) != (POST_ID,"publish",2223):
            raise RuntimeError("WordPress response mismatch")
    saved=fetch_post(POST_ID,auth)
    for k in ["id","slug","status","title","featured_media","categories","author"]:
        if saved.get(k)!=current.get(k):raise RuntimeError(f"Unexpected change after save: {k}")
    if raw_field(saved,"content")!=after:
        raise RuntimeError("WordPress did not retain negotiated wording exactly")
    after_counts=public_counts(auth)
    if counts!=after_counts:raise RuntimeError("Published post count changed unexpectedly")
    result={
       "post_id":POST_ID,"slug":SLUG,"action":action,"status":"publish","write_count":int(action=="UPDATE"),
       "body_sha_before":digest(before),"body_sha_after":digest(after),"heading_added":"私が実際にやった交渉",
       "confirmed_dialogue":True,"ctn_preserved":'[blog_parts id="4521"]' in after,
       "featured_media":2223,"public_counts_before":counts,"public_counts_after":after_counts
    }
    out=Path("reports/ux-resale-real-negotiation-20261113");out.mkdir(parents=True,exist_ok=True)
    (out/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out/"summary.md").write_text("# UX resale: real telephone negotiation\n\n"+json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("UX_RESALE_REAL_NEGOTIATION_RESULT",json.dumps(result,ensure_ascii=False),flush=True)
    return result
