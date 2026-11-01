#!/usr/bin/env python3
"""Two factual corrections to an unpublished exhibit report. No other WordPress mutation."""
import base64,hashlib,html,json,os,re,sys,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path

ROOT=Path("editorial/tom-and-jerry-hiroshima-2026/revisions")
OLD=ROOT/"followalong-seo-20261101.html"
NEW=ROOT/"storyboard-quacker-corrected-20261101.html"
SITE="https://tsurikue.com"
PID=4282
SLUG="tom-and-jerry-exhibition-hiroshima-2026"
TITLE="【広島】そごうのトムとジェリー展に行ってきた！見どころと限定グッズを現地レポ"
BASE_SHA="732182a653985e985fd271dbe52526cd05d16717992b792449fe3c7363c0ac0d"
PAIRS=[
(
"<p>アニメの絵コンテまで展示されていました。あのドタバタ劇も、こうして一つずつ作られていたんですね。</p>",
"<p>展示されていたのは、アニメ<strong>『トムとジェリーごっこ』</strong>の絵コンテ。<br>いつものドタバタ劇も、こうして一つずつ作られていたんですね。</p>"
),
(
'<h3 class="wp-block-heading">アヒルちゃんの丸焼きレシピって！</h3>',
'<h3 class="wp-block-heading">えっ、クァッカーの丸焼きレシピ！？</h3>'
),
(
"<p>料理本を開いたような展示には、アヒルちゃんの丸焼きレシピ。<br>しかも、ネズミが邪魔するかもしれないという注意書きつき。</p>",
"<p>料理本を開いたような展示には、まさかの<strong>クァッカーの丸焼きレシピ</strong>。<br>トムをお母さんだと思っているあの子が、丸焼きに！？<br>しかも、ネズミが邪魔するかもしれないという注意書きつき。</p>"
)]
IMAGE=re.compile(r"<!-- wp:image\b.*?<!-- /wp:image -->",re.S)
def digest(x):return hashlib.sha256(x.encode("utf-8")).hexdigest()
def auth():
    u=os.getenv("TSURIKUE_WP_USER");p=os.getenv("TSURIKUE_WP_APP_PASSWORD")
    if not u or not p:raise RuntimeError("STOP: missing WordPress secrets")
    return "Basic "+base64.b64encode((u+":"+p).encode()).decode()
def api(path,token,payload=None):
    headers={"Authorization":token,"Accept":"application/json","User-Agent":"tsurikue-tom-jerry-factual-corrections/1.0"}
    method="POST" if payload is not None else "GET"
    if payload is not None:headers["Content-Type"]="application/json; charset=utf-8"
    req=urllib.request.Request(SITE+path,method=method,headers=headers,
        data=json.dumps(payload,ensure_ascii=False).encode() if payload is not None else None)
    for attempt in range(3 if method=="GET" else 1):
        try:
            with urllib.request.urlopen(req,timeout=60) as r:return json.loads(r.read().decode())
        except (urllib.error.URLError,TimeoutError) as e:
            if method=="POST" or attempt==2:raise
            print("RETRY_GET",attempt+1,type(e).__name__,flush=True);time.sleep(2*(attempt+1))
def live(token):
    query=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,categories,featured_media,author,content"})
    return api("/wp-json/wp/v2/posts/"+str(PID)+"?"+query,token)
def raw(row):return (row.get("content") or {}).get("raw") or ""
def validate(row,sha):
    if (row.get("id"),row.get("slug"),row.get("status"))!=(PID,SLUG,"draft"):
        raise RuntimeError("STOP: target is not expected unpublished article")
    title=html.unescape((row.get("title") or {}).get("raw") or "")
    if title!=TITLE or row.get("categories")!=[7] or int(row.get("featured_media") or 0)!=4301:
        raise RuntimeError("STOP: article metadata drifted")
    if digest(raw(row))!=sha:
        raise RuntimeError("STOP: WordPress article body changed since last confirmed audit")
    if len(IMAGE.findall(raw(row)))!=15:
        raise RuntimeError("STOP: expected 15 existing photos")
def replace_exact(s):
    for old,new in PAIRS:
        if s.count(old)!=1:raise RuntimeError("STOP: expected correction text missing or duplicated")
        s=s.replace(old,new,1)
    return s
def prepare(original):
    old=OLD.read_text("utf-8")
    new=NEW.read_text("utf-8")
    if replace_exact(old)!=new:raise RuntimeError("STOP: proposed revision includes unapproved extra changes")
    result=replace_exact(original)
    if IMAGE.findall(result)!=IMAGE.findall(original):
        raise RuntimeError("STOP: existing photo blocks changed")
    if result.count("<!-- wp:paragraph -->")!=45 or result.count("<br>")!=45:
        raise RuntimeError("STOP: scene-level line break structure unexpectedly changed")
    if result.count("<!-- wp:image ")!=15 or result.count("<!-- /wp:image -->")!=15:
        raise RuntimeError("STOP: existing image count unexpectedly changed")
    if result.count("<!-- wp:table -->")!=1:
        raise RuntimeError("STOP: article fee table missing")
    old_table=re.search(r"<!-- wp:table -->.*?<!-- /wp:table -->",original,re.S)
    new_table=re.search(r"<!-- wp:table -->.*?<!-- /wp:table -->",result,re.S)
    if not old_table or not new_table or old_table.group()!=new_table.group():
        raise RuntimeError("STOP: official pricing table changed")
    if not result.startswith("<!-- tsurikue-salvage:v1 -->\n<!-- tsurikue-editorial:tom-and-jerry-hiroshima-2026:v1 -->\n"):
        raise RuntimeError("STOP: editorial identity missing")
    return result
def main(mode):
    if mode not in ("check","apply"):raise RuntimeError("Usage: check/apply")
    token=auth()
    before=live(token);validate(before,BASE_SHA)
    updated=prepare(raw(before))
    report={"post_id":PID,"status":"draft","featured_media":4301,
            "existing_photos_unchanged":15,"soft_line_breaks":45,
            "changes":["storyboard episode title","Quacker roast heading","Quacker roast description"],
            "before_sha256":BASE_SHA,"target_sha256":digest(updated),
            "expected_wordpress_uploads":0}
    out=Path("reports/tom-jerry-factual-corrections");out.mkdir(parents=True,exist_ok=True)
    (out/"preflight.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("CORRECTION_READ_ONLY_PREFLIGHT_OK",json.dumps(report,ensure_ascii=False),flush=True)
    if mode=="check":return
    current=live(token);validate(current,BASE_SHA)
    if any(current.get(field)!=before.get(field) for field in ("id","slug","status","title","featured_media","categories","author","content")):
        raise RuntimeError("STOP: concurrent edit")
    try:
        result=api("/wp-json/wp/v2/posts/"+str(PID),token,{"content":updated})
        if result.get("id")!=PID or result.get("status")!="draft":
            raise RuntimeError("STOP: unexpected WP write response")
    except (urllib.error.URLError,TimeoutError) as e:
        print("UNCERTAIN_POST_DO_NOT_RETRY",type(e).__name__,flush=True)
    saved=live(token)
    for field in ("id","slug","status","title","featured_media","categories","author"):
        if saved.get(field)!=before.get(field):
            raise RuntimeError("STOP: protected WordPress field changed: "+field)
    if raw(saved)!=updated or IMAGE.findall(raw(saved))!=IMAGE.findall(raw(before)):
        raise RuntimeError("STOP: stored text or image blocks differ")
    report["result"]="UPDATED_AND_VERIFIED";report["after_sha256"]=digest(raw(saved))
    (out/"result.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("CORRECTION_DRAFT_UPDATED_VERIFIED",json.dumps(report,ensure_ascii=False),flush=True)
if __name__=="__main__":main(sys.argv[1] if len(sys.argv)>1 else "check")
