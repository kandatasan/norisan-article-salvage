"""Guarded 2026-11-13 follow-up: first-person 616万円 realization and intentional soft/hard breaks.

Do not touch other posts, original figures, media, CTN/Gulliver links, or source tables.
"""
from __future__ import annotations
import hashlib, html, json, re
from pathlib import Path

POST_ID=2948
SLUG="lexus-ux-used"
TITLE="レクサスUXの中古は狙い目？新車と比べて中古をおすすめしたい理由"
EXPECTED_SHA="b815b42e22ff3d22a237035da0e992af04bca3822123d7b31934060d23b8c73d"
MARKER="<!-- tsurikue-ux-used-voice-breaks:20261113 -->"
INTRO_ANCHOR='<!-- wp:image {"id":2587,"sizeSlug":"large","linkDestination":"none"} -->'
PARA=re.compile(r'<!-- wp:paragraph(?: [^\n]*?)? -->\s*<p[^>]*>(.*?)</p>\s*<!-- /wp:paragraph -->',re.S)


def p(inner:str)->str:
    return "<!-- wp:paragraph -->\n<p>"+inner+"</p>\n<!-- /wp:paragraph -->"


def replace_one(body:str,old:str,new:str)->str:
    if body.count(old)!=1:
        raise RuntimeError(f"Not an unambiguous target: {old[:95]!r}, count={body.count(old)}")
    return body.replace(old,new,1)


def matching_block(body:str,phrase:str):
    matches=[m for m in PARA.finditer(body) if phrase in html.unescape(re.sub(r'<[^>]+>', '', m.group(1)))]
    if len(matches)!=1:
        raise RuntimeError(f"Expected one full paragraph with {phrase!r}; found {len(matches)}")
    return matches[0]


def merge(body:str,phrases:list[str])->str:
    """Merge only *contiguous* topic-related Gutenberg paragraph blocks into one block."""
    if len(phrases)<2: raise RuntimeError("Need at least 2 paragraphs")
    chunks=[matching_block(body,q) for q in phrases]
    for a,b in zip(chunks,chunks[1:]):
        if a.end()>b.start() or body[a.end():b.start()].strip():
            raise RuntimeError("Refusing to merge across anything other than blank whitespace")
    contents=[m.group(1).strip() for m in chunks]
    # Existing soft breaks remain; joining topics in the same flow uses soft breaks.
    joined="<br>".join(contents)
    first_block=chunks[0].group(0).replace(chunks[0].group(1),joined,1)
    return body[:chunks[0].start()]+first_block+body[chunks[-1].end():]


def sentence_breaks(inner:str)->str:
    """Add soft breaks after natural prose sentence boundaries without changing markup tags."""
    # Respect existing <br>, including <br /> and line-end.
    # Split by html tags and touch only text tokens.
    tokens=re.split(r'(<[^>]+>)',inner)
    for idx,token in enumerate(tokens):
        if token.startswith("<"): continue
        # Only after a full stop with more prose in the same text token.
        tokens[idx]=re.sub(r'。(?!\s*$)(?=\S)', "。<br>",token)
    out="".join(tokens)
    # Closing inline tags may sit between a sentence full stop and the next text sentence.
    out=re.sub(r'。(</(?:strong|em|a|span)>)(?=[^<\n\r])',r'。\1<br>',out)
    return out


def normalize_plain_paragraphs(body:str)->str:
    # Skip all non-plain paragraphs (e.g. SWELL button blocks, advert captions).
    def fix(m):
        inner=m.group(1)
        revised=sentence_breaks(inner)
        return m.group(0).replace(inner,revised,1) if revised!=inner else m.group(0)
    return PARA.sub(fix,body)


def transform(source:str)->str:
    if MARKER in source:
        if source.count(MARKER)==1 and source.count('[blog_parts id="4505"]')==1 and source.count('[blog_parts id="4521"]')==1:
            return source
        raise RuntimeError("Partial soft-break revision found")
    if hashlib.sha256(source.encode()).hexdigest()!=EXPECTED_SHA:
        raise RuntimeError("Live source SHA drift: revision halted")

    current=source

    # Replace only the introductory six short, disjoint paragraphs (not the owner photo).
    first='<!-- wp:paragraph -->\n<p><strong>中古のレクサスUX、今なら本気で狙い目だと思っています。</strong></p>'
    if current.count(first)!=1 or current.count(INTRO_ANCHOR)!=1:
        raise RuntimeError("Intro or photo anchor moved")
    start=current.index(first)
    end=current.index(INTRO_ANCHOR)
    original_intro=current[start:end]
    if start>=end or original_intro.count("<!-- wp:paragraph")!=6:
        raise RuntimeError("Expected six existing intro paragraphs")
    refreshed=[
        '私はレクサスUX250h F SPORTの特別仕様車「Emotional Explorer」を新車で買いました。<br>オプションや諸費用まで含めて、約616万円。',
        'ところが、あとになって中古UXの価格を見てしまいました。<br><strong>「あれ？ 中古で良かったんじゃないか？」</strong>',
        '後席が狭いのも、荷室が小さいのも、新車と中古で変わりません。<br>前席の居心地、乗り味、見た目のかっこよさだって同じ。<br>私が新車で気に入っていた部分を、今ならもっと手ごろな値段で楽しめるわけです。',
        '<strong>状態も装備も納得できるUXが300万円台までで見つかれば、本気で買い。</strong><br>きっと幸せになれます。',
        '中古車をお得に買うコツは2つ。<br><strong>条件の良い個体を見つけること。<br>今の車を、できるだけ高く売ること。</strong>',
    ]
    current=current[:start]+"\n\n".join(map(p,refreshed))+"\n\n"+current[end:]

    # The article conclusion should keep the same honest "would buy used now" stance.
    old_summary='私はUXを新車で買って良かったと思っています。それでも今もう一度選ぶなら、まず中古のUX250hを探します。<br><strong>300万円台までで状態も装備も納得できる1台があれば、本気で買い！</strong>'
    new_summary='約616万円で新車を買った私でも、今なら中古UX250hを真っ先に探します。<br><strong>300万円台までで状態も装備も納得できる1台なら、本気で買い！</strong>'
    current=replace_one(current,old_summary,new_summary)

    # Meaningful continuation: use <br> within one paragraph, not one block for every sentence.
    groupings=[
      ["中古UXを探すなら、レクサス認定中古車のCPOも候補です。","CPOは一般の中古車より価格が高め"],
      ["レクサス公式では、CPOについて90項目に及ぶ","中古車は1台ずつ状態が違うので"],
      ["反対に、価格を優先したい人や、年式・色・装備を広く探したい人は","CPOだから正解、一般中古だからダメという話ではありません。"],
      ["中古UXを選ぶときは、見た目だけで年式を決めない方がいいです。","外観の基本デザインは大きく変わっていませんが"],
      ["前期型と後期型を見比べても、外観の違いは小さく感じます。","ただし、見た目が似ている＝中身まで同じではありません。"],
      ["価格を優先するなら前期型。","中古車サイトの「前期・後期」という呼び方だけに頼らず"],
      ["私が特に見た方がいいと思うのは","本革や合成皮革は、使い方によって"],
      ["そして「レクサスだから中古でも絶対に壊れない」とは考えない方がいいです。","ここはレクサスでも同じです。"],
      ["私はEmotional Explorerを選びました。","新車では予算差が気になる上級グレードや特別仕様車も"],
      ["同じ「UX250h F SPORT」でも、中身は1台ずつ違います。","安い理由に納得できるなら、お買い得。","中古車はこのくらいの距離感がちょうどいいと思います。"],
    ]
    for group in groupings:
        current=merge(current,group)

    # Reflow paragraph text that has consecutive sentences on the same visual line.
    current=normalize_plain_paragraphs(current)

    if (current.count('[blog_parts id="4505"]')!=1 or current.count('[blog_parts id="4521"]')!=1
        or current.count('ガリバーで希望のUXを探してみる')!=2):
        raise RuntimeError("Existing CTA modified")
    image_ids=lambda body:sorted(re.findall(r'wp-image-(\d+)',body))
    if image_ids(source)!=image_ids(current):
        raise RuntimeError("Owner media IDs drifted")
    # No image blocks, outbound link targets, headings, or styled paragraph attributes may vanish.
    if (source.count("<!-- wp:image") != current.count("<!-- wp:image")
        or source.count("<figure") != current.count("<figure")
        or source.count("<!-- wp:heading") != current.count("<!-- wp:heading")
        or source.count("<!-- wp:paragraph {") != current.count("<!-- wp:paragraph {")):
        raise RuntimeError("Protected block structure drifted")
    if sorted(re.findall(r'href="([^"]+)"', source)) != sorted(re.findall(r'href="([^"]+)"', current)):
        raise RuntimeError("Original internal/external links drifted")
    if source.count('<!-- tq-lexus-related-cards:v1:lexus-ux-used -->')!=1 or current.count('<!-- tq-lexus-related-cards:v1:lexus-ux-used -->')!=1:
        raise RuntimeError("Related article cards moved")
    if "元オーナーです" in current[:current.find(INTRO_ANCHOR)]:
        raise RuntimeError("Old intro credentials remain")
    if '<strong>「あれ？ 中古で良かったんじゃないか？」</strong>' not in current:
        raise RuntimeError("Main personal reaction missing")

    current=MARKER+"\n"+current
    return current


def apply_revision(config_path:Path,cfg:dict,auth:str,api):
    if (cfg.get("post_id"),cfg.get("slug"),cfg.get("title"))!=(POST_ID,SLUG,TITLE):
        raise RuntimeError("Post metadata guard mismatch")
    fetch_post,raw_field,public_counts,post_json,site_url=api
    before=fetch_post(POST_ID,auth)
    for k,v in [("id",POST_ID),("slug",SLUG),("status","publish"),("featured_media",1001),("categories",[10,11]),("author",1)]:
        if before.get(k)!=v: raise RuntimeError(f"WordPress identity drift: {k}")
    if html.unescape(raw_field(before,"title"))!=TITLE: raise RuntimeError("Title drift")
    source=raw_field(before,"content")
    revised=transform(source)
    counts=public_counts(auth)
    twice=fetch_post(POST_ID,auth)
    for k in ["id","slug","status","title","featured_media","categories","author"]:
        if before.get(k)!=twice.get(k): raise RuntimeError(f"Concurrent metadata change: {k}")
    if source!=raw_field(twice,"content"): raise RuntimeError("Concurrent article modification")
    status="ALREADY_PRESENT" if revised==source else "UPDATE"
    if status=="UPDATE":
        updated=post_json(site_url+"/wp-json/wp/v2/posts/"+str(POST_ID),auth,{"content":revised})
        if (updated.get("id"),updated.get("slug"),updated.get("status"),updated.get("featured_media"))!=(POST_ID,SLUG,"publish",1001):
            raise RuntimeError("Update response identity mismatch")
    after=fetch_post(POST_ID,auth)
    for k in ["id","slug","status","title","featured_media","categories","author"]:
        if before.get(k)!=after.get(k): raise RuntimeError(f"Post-update metadata mismatch: {k}")
    if raw_field(after,"content")!=revised: raise RuntimeError("Content not saved as expected")
    if public_counts(auth)!=counts: raise RuntimeError("Published total changed")
    report={"post_id":POST_ID,"slug":SLUG,"status":"publish","title":TITLE,"featured_media":1001,"action":status,"writes":int(status=="UPDATE"),"old_sha":hashlib.sha256(source.encode()).hexdigest(),"new_sha":hashlib.sha256(revised.encode()).hexdigest(),"paragraph_blocks_before":len(PARA.findall(source)),"paragraph_blocks_after":len(PARA.findall(revised)),"soft_breaks_before":source.count("<br"),"soft_breaks_after":revised.count("<br"),"publish_totals":counts}
    out=Path("reports")/"ux-used-voice-breaks-20261113";out.mkdir(parents=True,exist_ok=True)
    (out/"result.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out/"summary.md").write_text("# UX used revised intro and soft/hard breaks\n\n"+json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("UX_USED_BREAKS_RESULT",json.dumps(report,ensure_ascii=False),flush=True)
    return report
