"""One-post verified UX resale edit: transparent ratio, grade/year, dated record, real CTN story.

All edits guarded by exact WordPress content SHA and Gutenberg block anchors. No
fictional negotiation, no unsupported current market quotes, no changes to CTN.
"""
from __future__ import annotations
from pathlib import Path
import hashlib, html, json, re

POST_ID = 2222
SLUG = "ux-resale"
OLD_TITLE = "レクサスUXのリセールは？616万円で購入し427万円で売却した記録"
NEW_TITLE = "レクサスUXのリセールは？616万円→427万円、残価率69.3％の売却記録"
EXPECTED_CONTENT_SHA = "f90f4f14e2c5761f4ed4cb43121799b156a994468277f5ef4f8f958817300a10"
MARKER = "<!-- tsurikue-ux-resale-verified-story:20261113 -->"
P_BLOCK = re.compile(r'<!-- wp:paragraph(?: [^\n]*?)? -->\s*<p[^>]*>(.*?)</p>\s*<!-- /wp:paragraph -->',re.S)
H_BLOCK = re.compile(r'<!-- wp:heading(?: [^\n]*?)? -->\s*<h[234][^>]*>(.*?)</h[234]>\s*<!-- /wp:heading -->',re.S)

def sha(value:str)->str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()

def visible(text:str)->str:
    return html.unescape(re.sub(r'<[^>]+>','',text)).replace('\n',' ').strip()

def p(text:str)->str:
    return "<!-- wp:paragraph -->\n<p>"+text+"</p>\n<!-- /wp:paragraph -->"

def h2(text:str)->str:
    return '<!-- wp:heading -->\n<h2 class="wp-block-heading">'+text+'</h2>\n<!-- /wp:heading -->'

def replace_paragraph(body:str,search:str,new_text:str)->str:
    matches=[m for m in P_BLOCK.finditer(body) if search in visible(m.group(1))]
    if len(matches)!=1: raise RuntimeError(f"Paragraph anchor must be unique: {search!r}, found {len(matches)}")
    m=matches[0]
    return body[:m.start()]+p(new_text)+body[m.end():]

def rename_heading(body:str,old:str,new:str)->str:
    matches=[m for m in H_BLOCK.finditer(body) if visible(m.group(1))==old]
    if len(matches)!=1:raise RuntimeError(f"Heading anchor not unique: {old!r}, count={len(matches)}")
    m=matches[0]; block=m.group(0).replace(old,new,1)
    return body[:m.start()]+block+body[m.end():]

def insert_before_heading(body:str,heading:str,addition:str)->str:
    matches=[m for m in H_BLOCK.finditer(body) if visible(m.group(1))==heading]
    if len(matches)!=1:raise RuntimeError(f"Target heading not unique: {heading!r}")
    return body[:matches[0].start()]+addition+"\n\n"+body[matches[0].start():]

def protected_signature(body:str)->dict:
    return {
       'images':sorted(re.findall(r'wp-image-\d+',body)),
       'image_blocks':len(re.findall(r'<!-- wp:image\b',body)),
       'embeds':len(re.findall(r'<!-- wp:embed\b',body)),
       'table':len(re.findall(r'<!-- wp:table\b',body)),
       'table_body':[m.group(0) for m in re.finditer(r'<!-- wp:table\b.*?<!-- /wp:table -->',body,re.S)],
       'list':len(re.findall(r'<!-- wp:list\b',body)),
       'shortcode':re.findall(r'\[blog_parts id="\d+"\]',body),
       'affiliate_urls':sorted(re.findall(r'https?://(?:px\.a8\.net|www15\.a8\.net)[^"\s<]+',body)),
       'external_urls': sorted(re.findall(r'href="(https?://[^"]+)"',body)),
       'related_cards':len(re.findall(r'<!-- tq-lexus-related-cards',body)),
    }

def transform(source:str)->str:
    if MARKER in source:
        if source.count(MARKER)==1 and source.count('69.3％')>=2 and source.count('[blog_parts id="4521"]')==1:
            return source
        raise RuntimeError('Partial UX resale marker found')
    if sha(source)!=EXPECTED_CONTENT_SHA:
        raise RuntimeError("Live UX resale content SHA drift; cancel rather than overwrite")
    if source.count('[blog_parts id="4521"]')!=1: raise RuntimeError('CTN shortcode unexpectedly changed')
    if source.count('レクサスUXのリセールで私が学んだこと')!=1:
        raise RuntimeError("Protected structure changed")
    current=source

    # Lead with the actual outcome and explain why two early quotes differ.
    current=replace_paragraph(current,
       '私のUXは、納車から約3か月ごろのほぼ同じ時期に',
       '約616万円で新車購入したレクサスUX250h F SPORTを、2025年2月に427万円で売却しました。<br>購入総額に対する売却額の割合は、約69.3％です。')
    current=replace_paragraph(current,
       '私が実際にUXを手放したのは約2年後',
       'ただ、最初から427万円という金額が見えていたわけではありません。<br>納車から数か月の頃、ディーラーの査定は350万円。一方、ほぼ同じ時期の別の一括査定では500万円前後。<br>同じ車で、約150万円の差が出たんです。')
    current=replace_paragraph(current,
       'この記事では、好奇心で査定した350万円から',
       '売るつもりがなかった頃の好奇心査定から、生活のために手放すまで。<br>私のUXに実際についた金額を、順番に残します。')

    current=rename_heading(current,
       '結論｜UXのリセールは悪いとは思わなかった。ただし査定先で150万円差が出た',
       '結論｜UXのリセールは購入総額比69.3％。査定先では150万円差')
    current=replace_paragraph(current,
       'まず、私のUXに実際についた金額を時系列で並べます',
       '私が乗っていたのは、<strong>2023年式のUX250h F SPORT 特別仕様車「Emotional Explorer」</strong>。<br>2023年6月に初度登録、7月に納車され、2025年2月に売却しました。<br>まずは実際の査定額を時系列でどうぞ。')
    current=replace_paragraph(current,
       '350万円、500万円前後、430万円、435万円は査定時の提示額',
       '350万円・500万円前後・430万円・435万円は、いずれも査定時の<strong>提示額</strong>。<br>2025年2月にカーセブンへ<strong>実際に売却した価格</strong>は427万円です。')
    current=replace_paragraph(current,
       'なお、購入額616万円の見積もり内訳には',
       '<strong>購入総額比の残価率：約69.3％</strong>（427万円 ÷ 616万円 × 100）。<br>この616万円にはオプションや諸費用も含まれます。車両本体価格だけを分母にした残価率とは別の数字なので、そこは分けて見てください。<br>新車購入時の内訳は<a href="https://tsurikue.com/ux-mitsumori/">616万円の見積もり記事</a>に載せています。')

    # Preserve the actual two-company physical appraisal sequence; no imagined bids or dialogue.
    current=rename_heading(current,
       '売ると決めてCTNを使った｜連絡が来たのは2社だった',
       'CTN経由で2社に実車査定。最後はカーセブンへ')
    current=replace_paragraph(current,
       '2社とも電話だけで金額を決めたわけではありません',
       'カーセブンとネクステージには、どちらにも実際のUXを見てもらいました。<br>電話だけの概算で終わらず、2社に現車を確認してもらったうえで比較できたのが良かったです。')
    current=replace_paragraph(current,
       '最終的にUXを買い取ったのは、カーセブンです',
       '最終的に選んだのは、カーセブン。<br>2025年2月、427万円で売却しました。<br>最初にディーラーで350万円と言われたときには、ここまでの金額で売れるとは思っていませんでした。')

    # Clarify that the historic 435 quote is not an undocumented same-day competing offer.
    current=replace_paragraph(current,
       '半年近く前にネクステージから提示された実車査定は435万円',
       '約半年前にネクステージから提示された実車査定額は435万円で、実際の売却額との差は8万円。<br>ただし435万円は<strong>売却の約半年前の査定</strong>です。2025年2月にカーセブンと競り合って出た最終提示額ではありません。')
    # Add time-bound context without manufacturing a current appraisal or price forecast.
    current=insert_before_heading(current,
       'レクサスUXのリセールで私が学んだこと',
       h2('2026年11月現在も427万円で売れる？')+'\n\n'+
       p('ここまでの427万円は、<strong>2025年2月に私が売却した実績</strong>です。<br>2026年11月現在の査定額を示すものではありません。年式・走行距離・車両状態や中古車の需要が違えば、金額も変わります。')+'\n\n'+
       p('LEXUS公式は、UXの<strong>2027年2月生産終了予定</strong>を案内しています。<br>ただ、生産終了の予定だけで中古車価格が上がるとも下がるとも言い切れません。今のUXの値段は、実際の査定を比較して確かめるのが近道です。<br><a href="https://lexus.jp/models/ux/" target="_blank" rel="noopener noreferrer">出典：LEXUS公式「UX」</a>'))
    current=rename_heading(current,
       'まとめ｜616万円で買ったUXは427万円で売れた',
       'まとめ｜UX250h F SPORTは購入総額比69.3％で売れた')
    current=replace_paragraph(current,
       '私のUXの記録をまとめると、納車約3か月の好奇心査定で',
       '<strong>2023年式UX250h F SPORT Emotional Explorerを約616万円で購入し、2025年2月に427万円で売却。</strong><br>購入総額比は約69.3％。ただし途中の査定は、ディーラー350万円と別の一括査定500万円前後で約150万円も違いました。')

    # Keep the real lived story, amount table, imagery, CTA, other links unchanged.
    if protected_signature(source)['images']!=protected_signature(current)['images']:
        raise RuntimeError('Original image IDs changed')
    before,after=protected_signature(source),protected_signature(current)
    for key in ['image_blocks','embeds','table','table_body','list','shortcode','affiliate_urls','related_cards']:
        if before[key]!=after[key]:
            raise RuntimeError(f"Protected resource drifted: {key}")
    old_links=before['external_urls'];new_links=after['external_urls']
    if sorted(set(new_links)-set(old_links))!=['https://lexus.jp/models/ux/']:
        raise RuntimeError('Unexpected outgoing URL introduced')
    if not set(old_links).issubset(set(new_links)):
        raise RuntimeError(f'Existing outbound link removed: {sorted(set(old_links)-set(new_links))}')
    if current.count('Emotional Explorer')<1 or current.count('69.3％')<3:
        raise RuntimeError('Main search intent answer missing')
    if current.count('wp-image-')!=source.count('wp-image-'):
        raise RuntimeError('Owner media mutated')
    if source.count('<!-- wp:heading')+1!=current.count('<!-- wp:heading'):
        raise RuntimeError('Unexpected heading count')
    if '私ならこう交渉する' in current:
        raise RuntimeError('Avoid blending an imagined negotiation into real story')
    return MARKER+'\n'+current


def apply_revision(config_path:Path,config:dict,auth:str,api):
    if (config.get('operation'),config.get('post_id'),config.get('slug'),config.get('expected_sha256')) != (
        'rewrite_published_ux_resale_20261113',POST_ID,SLUG,EXPECTED_CONTENT_SHA):
        raise RuntimeError('Wrong configuration for UX resale edit')
    fetch_post,raw_field,public_counts,post_json,site_url=api
    before=fetch_post(POST_ID,auth)
    for key,val in [('id',POST_ID),('slug',SLUG),('status','publish'),('featured_media',2223),('author',1),('categories',[10,11])]:
        if before.get(key)!=val:raise RuntimeError(f"Protected metadata mismatched: {key}")
    if html.unescape(raw_field(before,'title')) not in [OLD_TITLE,NEW_TITLE]:
        raise RuntimeError('Original title changed')
    original=raw_field(before,'content')
    updated=transform(original)
    counts_before=public_counts(auth)
    fresh=fetch_post(POST_ID,auth)
    for key in ['id','slug','status','title','featured_media','categories','author']:
        if fresh.get(key)!=before.get(key):raise RuntimeError(f"Post metadata edited concurrently: {key}")
    if raw_field(fresh,'content')!=original:raise RuntimeError('Someone edited UX resale content concurrently')
    action='ALREADY_PRESENT' if updated==original else 'UPDATE'
    if action=='UPDATE':
        response=post_json(site_url+'/wp-json/wp/v2/posts/'+str(POST_ID),auth,{'content':updated,'title':NEW_TITLE})
        if (response.get('id'),response.get('slug'),response.get('status'),response.get('featured_media')) != (POST_ID,SLUG,'publish',2223):
            raise RuntimeError('WordPress update returned unexpected metadata')
    after=fetch_post(POST_ID,auth)
    for key in ['id','slug','status','featured_media','categories','author']:
        if after.get(key)!=before.get(key):raise RuntimeError(f"Unexpected post-change metadata: {key}")
    if html.unescape(raw_field(after,'title'))!=NEW_TITLE or raw_field(after,'content')!=updated:
        raise RuntimeError('WordPress title or article body not saved as expected')
    counts_after=public_counts(auth)
    if counts_after!=counts_before:raise RuntimeError('Public post count changed unexpectedly')
    result={'post_id':POST_ID,'slug':SLUG,'status':'publish','title':NEW_TITLE,'featured_media':2223,
            'action':action,'writes':1 if action=='UPDATE' else 0,'sha_before':sha(original),
            'sha_after':sha(updated),'resale_2025_feb':4270000,'purchase_approx':6160000,
            'ratio_percent':round(427/616*100,1),'image_blocks':updated.count('<!-- wp:image'),
            'cta_preserved':'[blog_parts id="4521"]' in updated,'published_before':counts_before,'published_after':counts_after}
    out=Path('reports/ux-resale-verified-story-20261113');out.mkdir(parents=True,exist_ok=True)
    (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'summary.md').write_text('# UX resale guarded rewrite\n\n'+json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('UX_RESALE_REWRITE_RESULT',json.dumps(result,ensure_ascii=False),flush=True)
    return result
