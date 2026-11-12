"""Guarded targeted rewrite of the published Lexus UX used-car article.

Only post 2948. Preserve all media, source citations, unrelated articles,
existing 4505 price-checker and 4521 CTN common shortcode.
Never publish without matching exact previously audited content SHA.
"""
from __future__ import annotations
import hashlib
import html
import json
from pathlib import Path

EXPECTED_SHA = "201f03006afa8c31e9a7481f769f00ebee1e4eaef7b66e28d771412d018470b3"
MARKER = "<!-- tsurikue-ux-used-rewrite:20261113 -->"
TITLE = "レクサスUXの中古は狙い目？新車と比べて中古をおすすめしたい理由"
SLUG = "lexus-ux-used"
POST_ID = 2948


def paragraph(content: str) -> str:
    return "<!-- wp:paragraph -->\n<p>" + content + "</p>\n<!-- /wp:paragraph -->"


def heading(content: str, level: int = 2) -> str:
    opts = ' {"level":3}' if level == 3 else ""
    return f'<!-- wp:heading{opts} -->\n<h{level} class="wp-block-heading">{content}</h{level}>\n<!-- /wp:heading -->'


def replace_once(body: str, original: str, replacement: str) -> str:
    count = body.count(original)
    if count != 1:
        raise RuntimeError(f"Expected exact one occurrence, found {count}: {original[:85]}")
    return body.replace(original, replacement, 1)


def transform(current: str, funnel: str) -> str:
    if MARKER in current:
        if (
            current.count(MARKER) == 1
            and current.count('[blog_parts id="4505"]') == 1
            and current.count('[blog_parts id="4521"]') == 1
            and current.count("ガリバーで希望のUXを探してみる") == 2
        ):
            return current
        raise RuntimeError("Partial rewrite marker found; refusing repair")
    sha = hashlib.sha256(current.encode()).hexdigest()
    if sha != EXPECTED_SHA:
        raise RuntimeError(f"Source content changed after audited snapshot: {sha}")

    # Only the six leading intro paragraphs; preserve markers and original UX photo.
    first = '<!-- wp:paragraph -->\n<p><strong>UX250h F SPORTが車両本体199.6万円。'
    image_anchor = '<!-- wp:image {"id":2587,"sizeSlug":"large","linkDestination":"none"} -->'
    if current.count(first) != 1 or current.count(image_anchor) != 1:
        raise RuntimeError("Intro/photo anchors drifted")
    start, end = current.index(first), current.index(image_anchor)
    if start >= end or current[start:end].count('<!-- wp:paragraph') != 6:
        raise RuntimeError("Intro structure drifted")

    intro = [
        '<strong>中古のレクサスUX、今なら本気で狙い目だと思っています。</strong>',
        '私はUX250h F SPORTの特別仕様車「Emotional Explorer」を新車で購入し、諸費用やオプションを含め約616万円を支払いました。1年以上・1万km以上乗った元オーナーです。',
        '後席は狭いし、荷室だって広くありません。でも、前席の居心地や乗り味、扱いやすいサイズ、見た目のかっこよさ。私が気に入っていたところは、中古になっても変わらない。',
        '<strong>支払総額300万円台までで、欲しい装備がそろった状態のいいUXを見つけられたら、私は買いだと思います。</strong>条件が合えば、きっと幸せになれるはず。',
        '中古車をお得に買うコツは2つ。<br><strong>① 条件の良い個体を見つける。<br>② 今乗っている車を、できるだけ高く売る。</strong>',
        'どのUXを狙うか。そして乗り換えのお金をどう作るか。私の経験も交えて話します。',
    ]
    current = current[:start] + "\n\n".join(paragraph(x) for x in intro) + "\n\n" + current[end:]
    current = MARKER + "\n" + current

    current = replace_once(
        current,
        '結論｜中古UXは今「最強個体を探す」のが面白い',
        '結論｜条件の良い中古UXが300万円台までなら本気で買い！',
    )
    current = replace_once(
        current,
        '私は616万円でUXを買いました。<br>それを知っているからこそ、支払総額200万円台のF SPORTを見ると「いや、これ満足度高いだろ」と思います。',
        '私は約616万円でUXを購入しました。<br>だからこそ、200万〜300万円台で状態や装備のいいF SPORTを見つけると、思わず「これ、いいじゃん」となります。',
    )
    current = replace_once(
        current, '中古UXの「最強」は3つある',
        '中古UXは「何を重視するか」で選ぶ',
    )
    current = replace_once(
        current, '私なら中古UXを「一番安い1台」では選びません。<br>何を優先するかで、最強は変わります。',
        '最安値だけで決めるのはもったいない。<br>価格・新しさ・保証。どこを重視するかで、狙うUXは変わります。',
    )
    for old, new in [
        ("<strong>コスパ最強</strong>", "<strong>購入価格重視</strong>"),
        ("<strong>完成度最強</strong>", "<strong>改良後の装備重視</strong>"),
        ("<strong>安心最強</strong>", "<strong>保証・整備重視</strong>"),
    ]:
        current = replace_once(current, old, new)

    # Keep CTN blog part 4521 exactly once, and expand only its adjacent narrative.
    old_ctn_start = '<!-- wp:paragraph -->\n<p>そして乗り換えなら、買う車だけでなく'
    ctn_button = '<!-- wp:shortcode -->\n[blog_parts id="4521"]\n<!-- /wp:shortcode -->'
    if current.count(old_ctn_start) != 1 or current.count(ctn_button) != 1:
        raise RuntimeError("CTN anchors drifted")
    ctn_s = current.index(old_ctn_start)
    ctn_e = current.index(ctn_button)
    if ctn_e <= ctn_s or current[ctn_s:ctn_e].count("tsurikue-ctn-used-funnel:20260917-treasure") != 1:
        raise RuntimeError("CTN placement drifted")
    new_ctn = [
        '<!-- tsurikue-ctn-used-funnel:20260917-treasure -->',
        heading('今の車を高く売る｜シエンタの査定は25万円も違った'),
        paragraph('中古UXをお得に買うなら、今の車の売り方も大事です。<br><strong>ディーラーの下取りだけで決めると、損をすることがあります。</strong>'),
        paragraph('私がシエンタからUXへ乗り換えたとき、ディーラーの下取り査定は50万円。ところが、従来型の一括査定に出してみると75万円で売れました。<br><strong>まさかの25万円差！</strong>'),
        paragraph('「これ、三眼LEDとムーンルーフが実質無料で買えたようなものじゃん！」と大喜びしました。買い方は同じでも、売り方でこれだけ変わるんです。'),
        paragraph('ただ、その一括査定で参ったのが電話ラッシュ。<br>何度も電話がかかってくる、あの「無限電話」です。'),
        paragraph('そこで、UXを手放すときに選んだのがCTN。連絡先が最大3社に絞られるので、たくさんの会社と一度にやりとりする負担がありません。実際、私に連絡してきたのはカーセブンとネクステージの2社。最終的に、カーセブンへ427万円で売却しました。'),
        paragraph('1社だけに任せる方法もあります。でも、私は複数社と話せる方が好き。<strong>交渉の余地が残るからです。</strong>'),
        heading('私ならこう交渉する', 3),
        '<!-- wp:list -->\n<ul class="wp-block-list"><!-- wp:list-item -->\n<li>まず電話で「ぶっちゃけ、いくらぐらいになりそうですか？」と聞く。このとき、金額だけでなく、対応に熱意を感じる会社も覚えておく。</li>\n<!-- /wp:list-item -->\n\n<!-- wp:list-item -->\n<li>各社の感触が大きく変わらないなら、一番熱意を感じた会社へこう伝える。<br>「大体どこも同じ金額ですよね。正直、手間と時間が惜しいので、現地査定は一社にしたい。他社に負けない金額が出せそうなら、他社の現地査定を断ろうと思う」</li>\n<!-- /wp:list-item --></ul>\n<!-- /wp:list -->',
        paragraph('もちろん、この話で金額が上がる保証はありません。提示額に納得できなければ、ほかの会社にも現車を見てもらえばOK。<br><strong>大事なのは、下取りの一発回答で決めないこと。</strong>'),
    ]
    current = current[:ctn_s] + "\n\n".join(new_ctn) + "\n\n" + current[ctn_e:]

    # Replace the old text-only last Gulliver CTA; keep related-card section intact.
    summary_start = '<!-- wp:heading -->\n<h2 class="wp-block-heading">まとめ｜200万円台のUXは「安いレクサス」じゃなく宝探し</h2>\n<!-- /wp:heading -->'
    related_marker = '<!-- tq-lexus-related-cards:v1:lexus-ux-used -->'
    if current.count(summary_start) != 1 or current.count(related_marker) != 1:
        raise RuntimeError("Summary/related anchors drifted")
    ss, ee = current.index(summary_start), current.index(related_marker)
    original_footer = current[ss:ee]
    if (
        original_footer.count('ガリバーで中古のレクサスUXを探してみる') != 1
        or original_footer.count('tsq-gulliver-micro-20261014 top') != 1
        or original_footer.count('tsq-gulliver-micro-20261014 bottom') != 1
    ):
        raise RuntimeError("Legacy footer CTA drifted")

    footer = [
        heading('まとめ｜良い中古UXを見つけて、今の車は高く売る'),
        paragraph('私はUXを新車で買って良かったと思っています。それでも今もう一度選ぶなら、まず中古のUX250hを探します。<br><strong>300万円台までで状態も装備も納得できる1台があれば、本気で買い！</strong>'),
        paragraph('後席の狭さや荷室の小ささは、中古になっても変わりません。そこが許せて、前席の心地よさや見た目に惹かれるなら、きっと気に入ると思います。'),
        paragraph('<strong>条件のいいUXを探す。そして今の車をできるだけ高く売る。</strong><br>この2つを押さえれば、同じ予算でも選べる中古UXが変わってきます。'),
        paragraph('中古車は1台ずつ条件が違うもの。お気に入りを見つけるなら、公開中の在庫だけで決めず、非公開車両も含めて探してみよう。'),
        funnel.strip(),
    ]
    current = current[:ss] + "\n\n".join(footer) + "\n\n" + current[ee:]

    # Guard the original photo map and related links; do not create/destroy media.
    if (
        current.count('[blog_parts id="4505"]') != 1
        or current.count('[blog_parts id="4521"]') != 1
        or current.count('ガリバーで希望のUXを探してみる') != 2
        or 'ガリバーで中古のレクサスUXを探してみる' in current
        or current.count('<!-- tq-lexus-related-cards:v1:lexus-ux-used -->') != 1
        or current.count('<!-- tq-lexus-related-cards:v1:end -->') != 1
    ):
        raise RuntimeError("CTA/related blocks failed invariants")
    return current


def apply_rewrite(config_path: Path, cfg: dict, auth: str, api):
    if (cfg.get("post_id"), cfg.get("slug"), cfg.get("title")) != (POST_ID, SLUG, TITLE):
        raise RuntimeError("Requested post identity mismatch")
    funnel_path = config_path.parent / cfg["funnel_file"]
    funnel = funnel_path.read_text(encoding="utf-8").strip()
    if hashlib.sha256(funnel.encode()).hexdigest() != cfg["funnel_sha256"]:
        raise RuntimeError("Current 4507 copy changed")
    fetch_post, raw_field, public_counts, post_json, site_url = api
    before = fetch_post(POST_ID, auth)
    for key, expected in (("id", POST_ID), ("slug", SLUG), ("status", "publish"), ("featured_media", 1001)):
        if before.get(key) != expected: raise RuntimeError(f"Identity/status/media drift: {key}")
    if html.unescape(raw_field(before, "title")) != TITLE:
        raise RuntimeError("Title drift")
    original = raw_field(before, "content")
    new_body = transform(original, funnel)
    if new_body == original:
        action = "ALREADY_PRESENT"
    else:
        action = "UPDATE"
    counts_before = public_counts(auth)
    second = fetch_post(POST_ID, auth)
    for k in ("id", "slug", "status", "title", "featured_media", "author", "categories"):
        if second.get(k) != before.get(k):
            raise RuntimeError(f"Concurrent metadata drift: {k}")
    if raw_field(second, "content") != original:
        raise RuntimeError("Concurrent content drift")
    if action == "UPDATE":
        response = post_json(f"{site_url}/wp-json/wp/v2/posts/{POST_ID}", auth, {"content": new_body})
        if (response.get("id"), response.get("slug"), response.get("status"), response.get("featured_media")) != (POST_ID, SLUG, "publish", 1001):
            raise RuntimeError("WP update response mismatch")
    after = fetch_post(POST_ID, auth)
    if any(after.get(k) != before.get(k) for k in ("id", "slug", "status", "title", "featured_media", "author", "categories")):
        raise RuntimeError("Non-content metadata changed")
    if raw_field(after, "content") != new_body:
        raise RuntimeError("Saved body verification failed")
    if public_counts(auth) != counts_before:
        raise RuntimeError("Published counts changed")
    report = {"action": action, "post_id": POST_ID, "slug": SLUG, "title": TITLE, "status":"publish", "featured_media":1001, "content_before_sha256":hashlib.sha256(original.encode()).hexdigest(),"content_after_sha256":hashlib.sha256(new_body.encode()).hexdigest(), "wp_write_count":int(action == "UPDATE"),"published_counts":counts_before}
    out=Path("reports")/"lexus-ux-used-rewrite-20261113";out.mkdir(parents=True,exist_ok=True)
    (out/"result.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out/"summary.md").write_text("# Lexus UX used rewrite 2026-11-13\n\n"+json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("UX_USED_REWRITE_RESULT",json.dumps(report,ensure_ascii=False),flush=True)
    return report
