"""LBX cheap light-touch: Nov 2026 official prices, original owner's quote kept historical.

Never rewrite first-person reactions, original affiliate blocks, photos, user links
or article sections. Only exact edits below, then strict content and metadata check.
"""
from __future__ import annotations
import hashlib,html,json,re
from pathlib import Path

POST_ID=3863
SLUG="lexus-lbx-cheap"
TITLE="レクサスLBXを安く買う方法｜欲しいオプションを諦めず負担を減らす5つのコツ"
SOURCE_SHA="c0bdad04c26f8576ea6d197d7b056c627c1370dade7df8d3d949db45267c8447"
IDENTITY={"id":3863,"slug":SLUG,"status":"publish","featured_media":1700,"categories":[10],"author":1}
MARKER="<!-- tsurikue-lbx-cheap-light-prices-20261114 -->"
NEWS="https://global.toyota/jp/newsroom/lexus/44911793.html"

def P(text):return "<p>"+text+"</p>"

CHANGES=[
# Keep personal quote; distinguish September pricing from November new prices.
(P('この5つで<strong><span class="swl-marker mark_orange">25万6,300円</span></strong>。<br>Relaxの車両本体460万円と合わせると、登録諸費用などを除いて<strong>485万6,300円</strong>です。'),
 P('私が当時選んだ5点で<strong><span class="swl-marker mark_orange">25万6,300円</span></strong>。<br>改良前のRelax（車両本体460万円）と合わせると、諸費用を除いて<strong>485万6,300円</strong>でした。')),
(P('LBXは2026年9月時点で、2WDならElegantの420万円から選べます。<br>一方で私が欲しいRelaxは460万円。グレードだけでも40万円差があります。'),
 P('2026年11月改良後の2WDは、Elegantが445万円、Relaxが482万円。<br>グレードだけで<strong>37万円差</strong>です。')),
(P('2026年9月20日にLEXUS公式サイトで確認した、LBXハイブリッド2WDのメーカー希望小売価格は次の通りです。'),
 P('2026年11月3日に発売された一部改良モデル。<br>ハイブリッド2WDの税込メーカー希望小売価格は次の通りです。')),
('<figure class="wp-block-table"><table><thead><tr><th>グレード</th><th>2WD価格</th></tr></thead><tbody><tr><td>Elegant</td><td>4,200,000円</td></tr><tr><td>Active</td><td>4,400,000円</td></tr><tr><td>Cool</td><td>4,600,000円</td></tr><tr><td>Relax</td><td>4,600,000円</td></tr><tr><td>Bespoke Build</td><td>5,500,000円</td></tr></tbody></table></figure>',
 '<figure class="wp-block-table"><table><thead><tr><th>グレード</th><th>2WD価格（税込）</th></tr></thead><tbody><tr><td>Elegant</td><td>4,450,000円</td></tr><tr><td>Active</td><td>4,650,000円</td></tr><tr><td>Cool</td><td>4,820,000円</td></tr><tr><td>Relax</td><td>4,820,000円</td></tr><tr><td>Bespoke Build</td><td>5,670,000円</td></tr></tbody></table></figure>'),
(P('最新価格は<a href="https://lexus.jp/models/lbx/features/price_package/" target="_blank" rel="noopener">LEXUS公式のLBX価格・パッケージ</a>で確認できます。'),
 P('価格は<a href="'+NEWS+'" target="_blank" rel="noopener">LEXUSの2026年10月22日公式発表</a>を参照。<br>私のオプション見積もりは改良前の条件なので、新車の価格表とは分けて見てください。')),
(P('LBXはElegantが420万円、Activeが440万円、RelaxとCoolが460万円です。'),
 P('改良後の2WDはElegantが445万円、Activeが465万円、RelaxとCoolが482万円です。')),
(P('ElegantからRelaxへ上げると40万円差。<br>ここは大きいです。'),
 P('ElegantからRelaxへ上げると37万円差。<br>これでも結構大きい。')),
(P('逆に私みたいに<strong>「Relaxのサドルタンが欲しい」</strong>と決まっているなら、40万円だけを見て下げると後悔するかもしれません。'),
 P('逆に私みたいに<strong>「Relaxのサドルタンが欲しい」</strong>と決まっているなら、37万円の差だけで諦めるのは惜しい。')),
(P('それでも、新車のElegantが420万円、Relaxが460万円なので、条件が合えば中古車で購入額を下げられる可能性はあります。'),
 P('改良後の新車はElegantが445万円、Relaxが482万円。<br>中古なら、欲しい装備が付いた個体の<strong>支払総額</strong>と比べたいところです。')),
(P('500万円前後の車になると、月々の支払い額だけを見ると判断しやすいです。'),
 P('500万円前後の車だと、ローンの見積もりではつい月々の支払額に目が行きます。')),
(P('私がRelaxに付けたいのは次の5つです。'),
 P('改良前の見積もりで、私がRelaxに付けたいと思ったのはこの5つ。<br>価格も当時のものです。')),
(P('LBXは420万円から選べますが、Relaxに欲しい装備を付ければ500万円が見えてきます。'),
 P('11月改良後はElegantが445万円、Relaxが482万円。<br>私が欲しかった装備も考えると、やっぱり500万円級の買い物です。')),
(P('25万円あれば、LBXで私が欲しい25万6,300円分の装備にほぼ届きます。'),
 P('その差が、欲しいオプションを諦めなくて済むほどの金額だったわけです。')),
(P('同じ金額差が出る保証はありません。<br>でも、<strong>今の車の価値を知らないままHUDやAdvanced Parkを削るのは、順番が逆かもしれない。</strong>'),
 P('<strong>今の車の価値を知らないままHUDやAdvanced Parkを削るのは、ちょっと早い。</strong>')),
(P('欲しかったLBXに乗って、駐車するときはAdvanced Park、目線の先にはHUD。<br>「削らなくてよかったな」と思えたら、その25万円はただの金額じゃなくなります。'),
 P('私ならRelaxのサドルタンに、HUDとAdvanced Park。<br>値段だけを見て、最初から諦めるのは惜しいです。')),
]

def digest(s):return hashlib.sha256(s.encode('utf-8')).hexdigest()

def signature(s):
    return {
        "headings":re.findall(r'<!-- wp:heading\b.*?<!-- /wp:heading -->',s,re.S),
        "lists":re.findall(r'<!-- wp:list(?:\s|>).*?<!-- /wp:list -->',s,re.S),
        "images":re.findall(r'<!-- wp:image\b.*?<!-- /wp:image -->',s,re.S),
        "buttons":re.findall(r'<!-- wp:loos/button\b.*?<!-- /wp:loos/button -->',s,re.S),
        "shortcodes":re.findall(r'<!-- wp:shortcode\b.*?<!-- /wp:shortcode -->',s,re.S),
        "paragraphs":s.count('<!-- wp:paragraph'),
        "tables":s.count('<!-- wp:table'),
        "urls_except_official_news":sorted(re.findall(r'href="([^"]+)"',s)),
        "gulliver_counted":s.count('"isCount":true'),
        "gulliver_click_ids":re.findall(r'data-id="(gu3863-\d+)"',s),
        "original_emotional_reactions":[x in s for x in ('シエンタ','サドルタン','30件ほど着信','カーセブンへ427万円','25万6,300円')],
    }

def transform(original):
    if MARKER in original:
        if original.count(MARKER)==1 and all(new in original for _,new in CHANGES):
            return original
        raise RuntimeError('Article has a partial or conflicting edit marker')
    if digest(original)!=SOURCE_SHA:
        raise RuntimeError('LBX original changed since source audit; refuse overwrite')
    updated=original
    for idx,(old,new) in enumerate(CHANGES):
        if old==new or updated.count(old)!=1 or original.count(old)!=1:
            raise RuntimeError(f'Edit {idx+1} expected unique exact original anchor; count {original.count(old)}')
        updated=updated.replace(old,new,1)
    # Marker outside all Gutenberg blocks, but not a new visible paragraph.
    updated=updated.replace('<!-- tsurikue-editorial:v1 slug=lexus-lbx-cheap -->',
       '<!-- tsurikue-editorial:v1 slug=lexus-lbx-cheap -->\n'+MARKER,1)
    reversed_text=updated.replace('\n'+MARKER,'',1)
    for old,new in reversed(CHANGES):
        if reversed_text.count(new)!=1:raise RuntimeError('Replace-back not unique')
        reversed_text=reversed_text.replace(new,old,1)
    if reversed_text!=original:
        raise RuntimeError('Content outside exact intended edits changed')
    a,b=signature(original),signature(updated)
    for field in ('headings','lists','images','buttons','shortcodes','paragraphs','tables','gulliver_counted','gulliver_click_ids','original_emotional_reactions'):
        if a[field]!=b[field]:raise RuntimeError('Protected resources changed: '+field)
    old_urls=a['urls_except_official_news'];new_urls=b['urls_except_official_news']
    original_price_url='https://lexus.jp/models/lbx/features/price_package/'
    if old_urls.count(original_price_url)!=1 or new_urls!=sorted([u for u in old_urls if u!=original_price_url]+[NEWS]):
        raise RuntimeError('Unexpected link change')
    if len(CHANGES)>17:raise RuntimeError('Too many changes in light edit')
    return updated

def apply(config_path:Path,cfg:dict,auth:str,api):
    if (cfg.get('operation'),cfg.get('post_id'),cfg.get('slug'),cfg.get('expected_sha256'))!=(
      'revise_lbx_cheap_light_20261114',POST_ID,SLUG,SOURCE_SHA):
        raise RuntimeError('Wrong edit target')
    fetch_post,raw_field,public_counts,post_json,site_url=api
    before=fetch_post(POST_ID,auth)
    keys={key:before.get(key) for key in IDENTITY}
    if keys!=IDENTITY:raise RuntimeError('Published LBX cheap identity changed')
    if html.unescape(raw_field(before,'title'))!=TITLE:raise RuntimeError('Unexpected LBX title')
    raw=raw_field(before,'content')
    updated=transform(raw)
    counts=public_counts(auth)
    latest=fetch_post(POST_ID,auth)
    if any(latest.get(k)!=before.get(k) for k in IDENTITY) or raw_field(latest,'content')!=raw or raw_field(latest,'title')!=raw_field(before,'title'):
        raise RuntimeError('Concurrent user WordPress changes found')
    action='ALREADY_PRESENT' if raw==updated else 'UPDATE'
    if action=='UPDATE':
        saved=post_json(site_url+f'/wp-json/wp/v2/posts/{POST_ID}',auth,{'content':updated})
        if any(saved.get(k)!=v for k,v in IDENTITY.items()):raise RuntimeError('Save changed article metadata')
    verified=fetch_post(POST_ID,auth)
    if raw_field(verified,'content')!=updated or html.unescape(raw_field(verified,'title'))!=TITLE:
        raise RuntimeError('Live WordPress content/title mismatch')
    if any(verified.get(k)!=v for k,v in IDENTITY.items()):
        raise RuntimeError('Published post metadata changed')
    if counts!=public_counts(auth):raise RuntimeError('Published page/post count changed')
    report={
        "post_id":POST_ID,"slug":SLUG,"status":"publish","action":action,"write_count":int(action=='UPDATE'),
        "old_sha256":digest(raw),"new_sha256":digest(updated),
        "fixed_price_table":"2026-11-03 LBX refreshed model",
        "original_2026_09_option_quote_retained":True,
        "paraphrased_paragraphs":len(CHANGES)-1,"price_table_replaced":True,
        "all_unlisted_original_content_unchanged":True,
        "gulliver_buttons":signature(updated)['gulliver_click_ids'],
        "CTN_shortcode":updated.count('[blog_parts id="4521"]'),
        "published_counts":counts
    }
    dest=Path('reports/lbx-cheap-light-20261114');dest.mkdir(parents=True,exist_ok=True)
    (dest/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('LBX_CHEAP_LIGHT_RESULT',json.dumps(report,ensure_ascii=False),flush=True)
    return report
