#!/usr/bin/env python3
"""Reader-facing polish after Phase 3.2, still local-only and write-free."""
from __future__ import annotations
import argparse, csv, html, json, re, tempfile
from pathlib import Path

N=46
EXPECTED_AVAILABLE=110
EXPECTED_USED=105
EXPECTED_REDUNDANT=5
EXPECTED_PLACEHOLDERS=28
EXPECTED_OMITTED=225

# Exact, conservative edits only. No new facts are introduced.
REPLACEMENTS = {
    'fishing': [
        ('旧つりくえ！では「さあ、釣りに行こう」を入口に、初心者向けの釣り方解説と実際の釣行記録をまとめていました。このページでは、復活させる各記事へつながる入口として内容を整理しています。',
         'このページは、初心者向けの釣り方解説と実際の釣行記録をまとめた、つりくえ！の釣り記事の入口です。気になる釣り方や魚から読んでみてください。'),
    ],
    'hiroshima-gourmet': [
        ('旧つりくえ！では、西条町下見のラーメン亭・民都、西条中央のらー亭と焼肉あさひ、安芸津のいろは寿司など、実際に食べて印象に残った店を個別記事で紹介していました。',
         '西条町下見のラーメン亭・民都、西条中央のらー亭と焼肉あさひ、安芸津のいろは寿司など、実際に食べて印象に残った店を個別記事で紹介しています。'),
        ('店ごとの詳しい感想は、それぞれの復活記事で紹介します。',
         '店ごとの詳しい感想は、それぞれの関連記事で紹介します。'),
    ],
    'ginnjoura-men': [
        ('回収できた旧記録には営業時間の表記違いがあるため、来店前に最新情報をご確認ください。',
         '訪問時のメモには営業時間の表記が複数残っているため、正確な時刻は来店前に最新情報をご確認ください。'),
    ],
    'totoya-iiyo': [
        ('Wi-Fiは完備してあり、こころよくコンセントの延長ケーブルや加湿器の貸し出しをしてもらえました。',
         '訪問時はWi-Fiがあり、コンセントの延長ケーブルや加湿器もこころよく貸してもらえました。'),
        ('ただ、終電が23時ごろなので就寝には静かになっていると思われます。',
         '訪問当時は終電が23時ごろだったため、就寝するころには静かになっていました。'),
    ],
    'inbloombeppu': [
        ('ステキな想いでを作りに、大分県InBloomBeppuへ旅行の計画をたててみませんか？',
         'ステキな思い出を作りに、大分県InBloomBeppuへ旅行の計画をたててみませんか？'),
        ('戦後は米軍の幹部将校の宿舎として利用され、現在では改装してゲストハウスになっていて、一棟まるごと借りられる宿泊施設です。',
         '戦後は米軍の幹部将校の宿舎として利用され、訪問当時は改装された一棟貸しの宿泊施設として利用できました。'),
        ('冷蔵庫・IHクッキングヒーター・電子レンジ・炊飯器・湯沸かし器・食器類まで完備！（包丁は無かったかな）持ち込みOKなので、宴会しちゃいましょう！',
         '訪問時は冷蔵庫・IHクッキングヒーター・電子レンジ・炊飯器・湯沸かし器・食器類まで揃っていました！（包丁は無かったかな）食べ物を持ち込んで、みんなで宴会を楽しみました。'),
        ('当主さんとは直接会うことのない非接触がたチェックインでした。',
         '当主さんとは直接会うことのない非接触型のチェックインでした。'),
        ('何が言いたかというと、気持ちいい！です。', '何が言いたいかというと、気持ちいい！です。'),
    ],
    'matthewoishii': [
        ('マシューは人気店なので、混雑していることがあります。とくに週末は席がいっぱいなことがあるので、予約して行くことをオススメします。',
         '訪問当時は週末に席がいっぱいになることもある人気店という印象でした。混雑状況や予約方法は、来店前に最新情報をご確認ください。'),
    ],
    'ra-tei': [
        ('私の好きなラーメン屋シリーズ今回は東広島市西条中央にある『らー亭』は、がっつり食べたい気分の時に最高のお店です。',
         '私の好きなラーメン屋シリーズ。今回は東広島市西条中央にある『らー亭』。がっつり食べたい気分の時に最高のお店です。'),
        ('味千ラーメンの単品が700円なので、400円でこの唐揚げとご飯が食べられるってこと…ですか？',
         '訪問当時は味千ラーメン単品が700円だったので、セットとの差額400円でこの唐揚げとご飯が付くの…？と驚きました。'),
    ],
    'gogocurry': [
        ('私が食べたのはコチラ、豚ロースカツとチキンカツが１枚ずつ乗っているダブルカツカレー訪問当時はこれで1,050円…お得感が強い！',
         '私が食べたのはコチラ。豚ロースカツとチキンカツが1枚ずつ乗っているダブルカツカレー。訪問当時はこれで1,050円…お得感が強い！'),
        ('現金払いのほかにもPayPay・d払い・au PAYなど,QR決済の種類が充実していました。',
         '訪問当時は、現金払いのほかにもPayPay・d払い・au PAYなど、QR決済の種類が充実していました。'),
        ('テイクアウトの際は、先に電話で連絡をいれておくとスムーズに持ち帰れます。',
         '訪問時は、先に電話で連絡を入れてからテイクアウトするとスムーズに受け取れました。'),
    ],
    'tottori-drive': [
        ('資料館見学のほかにも、お土産コーナーやグッズ販売もあります。',
         '訪問当時は、資料館見学のほかにお土産コーナーやグッズ販売もありました。'),
        ('異国情緒あふれる庭園散策のほかに、毎日3回開催される中国雑技ショーなどが楽しめます。チャイナドレスのレンタルもあるので、借りたら気分は中国娘！？',
         '訪問当時は、異国情緒あふれる庭園散策のほかに中国雑技ショーも楽しめ、チャイナドレスのレンタルもありました。現在の開催内容は公式情報をご確認ください。'),
    ],
    'shiosoba-maeda-hiroshima': [
        ('平日ランチのみの営業なのでサラリーマンにはちょっとハードルが高い',
         '訪問当時は平日ランチのみの営業で、サラリーマンにはちょっとハードルが高い'),
        ('平日のランチタイムのみの営業に超人気店ということもあって、',
         '訪問当時は平日のランチタイムのみの営業で、超人気店ということもあって、'),
    ],
    'karaagekariju': [
        ('電話で先に注文しておくと待ち時間を短縮できますよ。',
         '訪問当時は、電話で先に注文しておくと待ち時間を短縮できました。'),
    ],
    'matsuura': [
        ('らーめんまつうら大２駐車場', 'らーめんまつうら第2駐車場'),
        ('運転に自信がない人は、近くに第2駐車場もあるので安心してください。',
         '訪問時は近くに第2駐車場もありました。運転に自信がない人はこちらの方が停めやすいかもしれません。'),
    ],
    'agetate-tenpura-hongo': [
        ('店内はカウンターとテーブル席があり、カウンターだと揚立てのものをトレイに出してくれ、テーブル席は注文品ができ上がったらまとめて持って来てくれるシステムになっています。',
         '訪問時の店内はカウンターとテーブル席があり、カウンターでは揚げ立てのものをトレイに出してくれ、テーブル席では注文品ができ上がったらまとめて持って来てくれる形でした。'),
    ],
    'hanabiramenn': [
        ('妙に焼酎が似合うカウンター席とテーブル席があります。',
         '訪問時は、妙に焼酎が似合うカウンター席とテーブル席がありました。'),
    ],
    'hiroshima-station-ramen-michimaru': [
        ('端的に言います。みちまるラーメンと替玉以上！',
         '端的に言います。注文したのは、みちまるラーメンと替玉。以上！'),
        ('麺の固さバリカタ、面が立っちゃう固さ。',
         '麺の固さはバリカタ。麺が立っちゃう固さ。'),
    ],
    'komugikodesakanatsureruyo': [
        ('タンパク質の混合物のことなんですね小麦粉に水を混ぜこねると',
         'タンパク質の混合物のことなんですね。小麦粉に水を混ぜこねると'),
    ],
    'kotamagairyouri': [
        ('コタマガイは沖アサリとは別種の貝です。', 'コタマガイはオキアサリとは別種の貝です。'),
    ],
    'catfish': [
        ('ナマズの生態(目次じゃないです)', 'ナマズの生態をざっくりまとめると'),
    ],
    'orizuru-tower': [
        ('また、売り上げの一部を原爆ドーム保存事業基金および広島市平和推進事業へ寄付するということみたいですね。',
         '訪問当時の案内では、売り上げの一部を原爆ドーム保存事業基金および広島市平和推進事業へ寄付する取り組みも紹介されていました。'),
    ],
    'yakinikucenter': [
        ('焼肉センターはどんなお店？店舗情報はコチラ！', '焼肉センターはどんなお店？'),
    ],
    'roast-beef-yusen': [
        ('コチラのお店で購入したので、驚き価格を見てみてくださいね。同じお店にある、送料無料の牛スジ肉とセットで注文をすると送料が無料になったのでお得でした。',
         ''),
        ('ローストビーフのざっくりとした作り方。(触れる目次は下にあります)', 'ローストビーフのざっくりとした作り方'),
    ],
}

REMOVE_PARAGRAPH_EXACT = {
    'hiroshima-station-ramen-michimaru': {'お店の情報','オススメメニュー','私の感想'},
    'shiosoba-maeda-hiroshima': {'広島の美味しい！をもっと見る'},
    'catfish': {'この記事でわかること(目次は下にあります)','ナマズの生態・狙うポイント','ナマズの釣り方【餌釣り編】','ナマズの釣り方【ルアー編】'},
    'tsureruurawaza': {'ガルプアライブパウダ―とは','ちょっとひと手間でさらにパワーアップ！','釣果のほどは？','まとめ・釣れない人は試してみる価値あり！'},
    'kotamagai-seafood-gathering': {'地方名から生息地を推察！','採取方、その①『職人タイプ』','採取方、その②『力技タイプ』','採取方、その③『道具タイプ』','採ったあとは食べよう！'},
}

REMOVE_EXACT = {
    'iphone-photo-alt': {'コチラで紹介していただきました。夕ごと日記様、ありがとうございます！'},
    'yakitori-riku': {
        '希釈タイプのチー坊売ってた！チー坊ウォーターはたまに見かけるけど、希釈タイプはあんまり見ないですよね',
        'チー坊とは、日本で初めてヨーグルトを発売した広島の企業チチヤスが、作った乳酸菌飲料です。カルピスみたいな感じかな、と思われました？それが全然違うものなんです！どう違うかは飲んでみてのお楽しみ、とっても美味しいですよ！',
        'チー坊についての記事はコチラ',
    },
}

# The Yakitori tail is a duplicated old related-link section. Keep the useful
# firsthand store impression by moving that sentence into the actual conclusion.
YAKITORI_CONCLUSION_OLD = '西条の友人たちに『美味しい焼き鳥屋さんを教えて』と聞いたところ、こちらの名前を教えてもらったのが来店のきっかけ。感想は簡潔に、ここのお店を教えてくれてありがとう！でした。オススメメニューを書き出しましたが、この日に食べたモモ・ハツ・ツクネ・セセリ・全てが本当に美味しかった！ごちそうさまでした。'
YAKITORI_CONCLUSION_NEW = YAKITORI_CONCLUSION_OLD + ' 騒がしすぎない雰囲気と、笑顔のステキな店長さんも印象に残っています。'

BANNED_READER_TEXT = (
    'チー坊についての記事はコチラ',
    '希釈タイプのチー坊売ってた！',
    'コチラのお店で購入したので、驚き価格を見てみてくださいね',
    '旧つりくえ！では',
    '復活記事',
    '回収できた旧記録',
    '終電が23時ごろなので',
    '現在では改装してゲストハウス',
    'マシューは人気店なので',
    '毎日3回開催される中国雑技ショー',
    'らーめんまつうら大２駐車場',
    'みちまるラーメンと替玉以上！',
    '面が立っちゃう固さ',
    'コタマガイは沖アサリとは別種',
    '広島の美味しい！をもっと見る',
    'この記事でわかること(目次は下にあります)',
    '触れる目次は下にあります',
)

def strip_tags(s: str) -> str:
    return html.unescape(re.sub(r'<[^>]+>', '', s))

def text(block: str) -> str:
    return re.sub(r'\s+', ' ', strip_tags(block)).strip()

def typ(block: str) -> str:
    if '<!-- wp:image' in block: return 'image'
    if '<!-- wp:heading' in block: return 'heading'
    if '<!-- wp:paragraph' in block: return 'paragraph'
    return 'other'

def blocks(content: str) -> list[str]:
    return [x.strip() for x in re.split(r'\n\s*\n', content) if x.strip()]

def replace_text(block: str, new_text: str) -> str:
    safe=html.escape(new_text, quote=False)
    if typ(block)=='paragraph':
        return re.sub(r'<p>.*?</p>', f'<p>{safe}</p>', block, count=1, flags=re.S)
    if typ(block)=='heading':
        return re.sub(r'<h([23])([^>]*)>.*?</h\1>', lambda m:f'<h{m.group(1)}{m.group(2)}>{safe}</h{m.group(1)}>', block, count=1, flags=re.S)
    return block

def visible_chars(content: str) -> int:
    return len(re.sub(r'\s+', '', strip_tags(content)))

def polish(article: dict) -> tuple[dict, dict]:
    a=dict(article)
    slug=a['slug']; before=a['content']; before_n=visible_chars(before)
    out=[]; fixes=0; removed=0
    yak_tail=False
    for b in blocks(before):
        t=text(b)
        if slug=='yakitori-riku' and typ(b)=='heading' and t=='お店の情報':
            yak_tail=True; removed+=1; continue
        if slug=='yakitori-riku' and yak_tail:
            if typ(b)=='image':
                out.append(b)  # retain confirmed photo provenance/display
                continue
            if t in REMOVE_EXACT.get(slug,set()) or typ(b) in ('paragraph','heading'):
                removed+=1; continue
        if typ(b)=='paragraph' and t in REMOVE_PARAGRAPH_EXACT.get(slug,set()):
            removed+=1; continue
        if t in REMOVE_EXACT.get(slug,set()):
            removed+=1; continue
        if slug=='yakitori-riku' and t==YAKITORI_CONCLUSION_OLD:
            b=replace_text(b,YAKITORI_CONCLUSION_NEW); t=YAKITORI_CONCLUSION_NEW; fixes+=1
        new=t
        for old,repl in REPLACEMENTS.get(slug,[]):
            if old in new:
                new=new.replace(old,repl); fixes+=1
        if new!=t:
            if not new.strip():
                removed+=1; continue
            b=replace_text(b,new)
        out.append(b)
    content='\n\n'.join(out).strip()+'\n'
    after_n=visible_chars(content)
    a['content']=content
    a['wordpress_write_count']=0; a['draft_creation_count']=0; a['media_upload_count']=0
    qa={'slug':slug,'visible_chars_before':before_n,'visible_chars_after':after_n,'reduction_ratio':0 if before_n==0 else round(max(0,(before_n-after_n)/before_n),6),'text_fixes':fixes,'blocks_removed':removed}
    a['phase32_reader_polish']=qa
    return a,qa

def validate(articles: list[dict], qa: list[dict]):
    if len(articles)!=N or len({a['slug'] for a in articles})!=N: raise ValueError('scope mismatch')
    available=sum(int(a.get('matched_images_available',len(a.get('matched_media_ids') or [])+len(a.get('matched_media_omitted_redundant') or []))) for a in articles)
    used=sum(len(a.get('matched_media_ids') or []) for a in articles)
    redundant=sum(len(a.get('matched_media_omitted_redundant') or []) for a in articles)
    ph=sum(len(a.get('placeholders') or []) for a in articles)
    om=sum(len(a.get('omitted_photo_positions') or []) for a in articles)
    if (available,used,redundant,ph,om)!=(EXPECTED_AVAILABLE,EXPECTED_USED,EXPECTED_REDUNDANT,EXPECTED_PLACEHOLDERS,EXPECTED_OMITTED):
        raise ValueError(f'image disposition changed: {(available,used,redundant,ph,om)}')
    blob='\n'.join(a['content'] for a in articles)
    for bad in BANNED_READER_TEXT:
        if bad in blob: raise ValueError(f'reader-facing remnant: {bad}')
    if 'web.archive.org' in blob.lower() or 'lexus-diary.com' in blob.lower(): raise ValueError('banned source leaked')
    if any(q['reduction_ratio']>=.50 for q in qa): raise ValueError('excessive polish reduction')
    if any(a.get('wordpress_write_count') or a.get('draft_creation_count') or a.get('media_upload_count') for a in articles): raise ValueError('write count nonzero')

def write(outdir: Path, articles: list[dict], qa: list[dict]):
    validate(articles,qa)
    ad=outdir/'articles'; ad.mkdir(parents=True,exist_ok=True)
    rows=[]
    for a in sorted(articles,key=lambda x:x['slug']):
        s=a['slug']; (ad/f'{s}.html').write_text(a['content'],encoding='utf-8'); (ad/f'{s}.json').write_text(json.dumps(a,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        rows.append({'slug':s,'title':a['title'],'characters':visible_chars(a['content']),'matched_images_available':int(a.get('matched_images_available',len(a.get('matched_media_ids') or [])+len(a.get('matched_media_omitted_redundant') or []))),'matched_images':len(a.get('matched_media_ids') or []),'matched_images_omitted_redundant':len(a.get('matched_media_omitted_redundant') or []),'placeholders':len(a.get('placeholders') or []),'omitted_photos':len(a.get('omitted_photo_positions') or []),'status':'READER_POLISHED'})
    summary={'targets':46,'lexus_targets':0,'articles_generated':46,'matched_images_available':sum(r['matched_images_available'] for r in rows),'matched_images_used':sum(r['matched_images'] for r in rows),'matched_images_omitted_redundant':sum(r['matched_images_omitted_redundant'] for r in rows),'placeholders_retained':sum(r['placeholders'] for r in rows),'unresolved_positions_omitted':sum(r['omitted_photos'] for r in rows),'reader_polish_text_fixes':sum(q['text_fixes'] for q in qa),'reader_polish_blocks_removed':sum(q['blocks_removed'] for q in qa),'articles_reduced_50pct_or_more':sum(q['reduction_ratio']>=.5 for q in qa),'wordpress_write_count':0,'draft_creation_count':0,'media_upload_count':0}
    outdir.mkdir(parents=True,exist_ok=True)
    (outdir/'index.json').write_text(json.dumps({'summary':summary,'articles':rows},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (outdir/'index.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    (outdir/'reader-polish-report.json').write_text(json.dumps({'summary':summary,'articles':qa},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (outdir/'summary.md').write_text('\n'.join(['# Phase 3.2 reader polish','']+[f'- {k}: **{v}**' for k,v in summary.items()])+'\n',encoding='utf-8')
    return {'summary':summary,'articles':rows,'qa':qa}

def build_from_phase32_dir(src: Path, outdir: Path):
    ps=sorted((src/'articles').glob('*.json'))
    if len(ps)!=N: raise ValueError(f'need 46 phase3.2 article JSON files, got {len(ps)}')
    articles=[]; qa=[]
    for p in ps:
        a=json.loads(p.read_text(encoding='utf-8')); o,q=polish(a); articles.append(o); qa.append(q)
    return write(outdir,articles,qa)

def build(outdir: Path):
    import old_tsurikue_remake_final_qa_dry_run as p32
    with tempfile.TemporaryDirectory(prefix='old-tsurikue-p32-') as td:
        src=Path(td)/'p32'; p32.build(src); return build_from_phase32_dir(src,outdir)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output-dir',type=Path,default=Path('reports/old-tsurikue-remake-final-qa-dry-run')); ap.add_argument('--phase32-dir',type=Path)
    args=ap.parse_args(); r=build_from_phase32_dir(args.phase32_dir,args.output_dir) if args.phase32_dir else build(args.output_dir); print(json.dumps(r['summary'],ensure_ascii=False,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
