#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,html,json,re,tempfile
from collections import Counter
from pathlib import Path
from typing import Any

N=46; MATCH=110; UNRES=253; WARN=.25; FAIL=.50
BANNED=('web.archive.org','lexus-diary.com','<script','<style')
REASONS=('orphan_heading','affiliate','stale_fix','truncated','duplicate','placeholder_omitted','other')

def strip_tags(s): return html.unescape(re.sub(r'<[^>]+>','',s))
def vis(s): return re.sub(r'\s+','',strip_tags(s))
def chars(s): return len(vis(s))
def blocks(s): return [x.strip() for x in re.split(r'\n\s*\n',s) if x.strip()]
def typ(b):
    if '<!-- wp:image' in b:return 'image'
    if '<!-- wp:heading' in b:return 'heading'
    if '<!-- wp:paragraph' in b:return 'paragraph'
    return 'other'
def txt(b): return re.sub(r'\s+',' ',strip_tags(b)).strip()
def level(b):
    m=re.search(r'<h([23])\b',b); return int(m.group(1)) if m else 2
def repl_block(b,t):
    safe=html.escape(t,quote=False)
    if typ(b)=='paragraph': return re.sub(r'<p>.*?</p>',f'<p>{safe}</p>',b,count=1,flags=re.S)
    if typ(b)=='heading': return re.sub(r'<h([23])([^>]*)>.*?</h\1>',lambda m:f'<h{m.group(1)}{m.group(2)}>{safe}</h{m.group(1)}>',b,count=1,flags=re.S)
    return b
def wp_p(t): return f'<!-- wp:paragraph -->\n<p>{html.escape(t,quote=False)}</p>\n<!-- /wp:paragraph -->'
def wp_h(t,l=2): return f'<!-- wp:heading {{"level":{l}}} -->\n<h{l} class="wp-block-heading">{html.escape(t,quote=False)}</h{l}>\n<!-- /wp:heading -->'

def looks_address(s):
    s=s.strip()
    if not s or len(s)>100 or any(c in s for c in '。！？、'): return False
    if re.match(r'^〒?\d{3}-?\d{4}',s): return True
    if not re.match(r'^(?:北海道|東京都|京都府|大阪府|.{2,3}県)',s): return False
    return bool(re.search(r'(?:市|区|郡|町|村|丁目|番地?|\d)',s))

def natural(slug,s):
    old=s
    p='訪問当時の所在地：'
    if s.startswith(p) and not looks_address(s[len(p):]): s=s[len(p):].strip()
    p='訪問当時の料金に関する記録：'
    if s.startswith(p):
        r=s[len(p):].strip().lstrip('※')
        if slug=='orizuru-tower':
            r=r.replace('入場料2200円','入場料2,200円',1)
            s='訪問当時は'+r if r.startswith('入場料') else '訪問当時、'+r
        elif slug=='inbloombeppu' and '宿泊料金' in r:
            s=r.replace('1棟貸しの宿泊料金は40000円','訪問当時の1棟貸し宿泊料金は40,000円',1)
        else:s='訪問当時、'+r
    s=s.replace('訪問当時の営業時間：営業時間：','訪問当時の営業時間：')
    if slug=='yakinikuasahi' and s.startswith('訪問当時の定休日：火曜日営業時間：'):
        s=f"訪問当時の案内では、定休日は火曜日、営業時間は{s.split('営業時間：',1)[1]}でした。"
    for target in ('yakinikuasahi','iroha-sushi-akitsu-menu'):
        if slug==target and s.startswith('訪問当時の住所：') and '電話番号：' in s:
            a,pn=s[len('訪問当時の住所：'):].split('電話番号：',1); s=f'訪問当時の住所は{a.strip()}、電話番号は{pn.strip()}でした。'
    if slug=='iroha-sushi-akitsu-menu' and s.startswith('訪問当時の営業時間：11時から21時30分ごろ定休日：水曜日'):
        s='訪問当時の案内では、営業時間は11時〜21時30分ごろ、定休日は水曜日でした。'
    return s,s!=old

REPL={
'catfish':(('送料を含めても３０００円程度とお手頃価格！','購入当時は送料を含めても3,000円程度と、お手頃価格でした！'),),
'gekiyasu-metal-vibration':(('ゲキブルブレードは、なんと174円～という破格さ！','ゲキブルブレードは購入当時174円～という破格さ！'),('どうです？これ、200円しないんですよ…？','購入当時は200円しない価格だったんですよ…？'),('まとめて送ってもらえるので送料220円ですみますよ。','購入当時は、まとめて送ってもらうと送料220円で済みました。'),('楽天の場合は送料無料ラインまで買わなくても、複数買いをすれば送料が分散されていい感じ！','購入当時は、楽天で複数買いすると送料を分散できる感覚でした。')),
'gogocurry':(('これで１０００円程度なのですから驚きました。','訪問当時はこれで1,000円程度だったので驚きました。'),('これで１０５０円…お得感が強い！','訪問当時はこれで1,050円…お得感が強い！'),('ペイペイなど、電子決済の種類が豊富！','訪問当時は、複数の電子決済に対応していました。'),('個人的には楽天ペイが使えないのが悲しいところだったので、いつか実装されてほしい！','訪問当時は楽天ペイに対応していなかったのが、個人的には少し残念でした。')),
'iroha-sushi-akitsu-menu':(('海鮮丼これで600円だからね！','訪問当時は海鮮丼が600円だったからね！'),('これで420円…ちょっと安すぎるよ！','訪問当時はこれで420円…ちょっと安すぎるよ！'),('お寿司もね、お手頃価格で美味しく食べられるの','お寿司も、お手頃価格で美味しく食べられました。')),
'matubagani':(('２杯5000円が目に留まり購入。','購入当時、2杯5,000円が目に留まり購入。'),),
'ra-tei':(('味千ラーメン唐揚げ定食【普通盛】1100円！','訪問当時、味千ラーメン唐揚げ定食【普通盛】は1,100円でした！'),('支払い方法は現金のみです。','訪問当時の支払い方法は現金のみでした。'),('東広島市 西条中央 1丁目18－28 中森マンション','訪問当時の所在地は、東広島市西条中央1丁目18－28 中森マンションでした。'),('駐車場もあって車で行きやすいですよ。','訪問時は駐車場もあり、車で立ち寄りやすい印象でした。')),
'sayori':(('2000円とちょっとで釣り道具一式が揃いました。','購入当時は2,000円とちょっとで釣り道具一式が揃いました。'),),
'totoya-iiyo':(('境港の市場で3万円ぐらいするカニより大きくて驚きました。','訪問当時に境港の市場で3万円ぐらいしていたカニより大きくて驚きました。'),),
'orizuru-tower':(('行く前までは正直なところ、高さ50メートルで2,200円ってやりすぎじゃない？と思っていました。','行く前までは正直なところ、高さ50メートルで当時の入場料2,200円ってやりすぎじゃない？と思っていました。'),('100円で折り紙が購入できるので、是非やってみてください。','訪問当時は100円で折り紙を購入できました。折り鶴づくりも、印象に残った体験のひとつです。')),
'sayori-tsurikata':(('早速サヨリを釣ろう！サヨリ釣行編へ','実際にこの仕掛けでサヨリを釣った様子は、サヨリ釣行記事で紹介します。'),('延べ竿仕掛けの詳しい作り方はこちら','延べ竿仕掛けそのものの作り方は、延べ竿仕掛けの記事で詳しくまとめています。')),
'inbloombeppu':(('アナゴこれ反則だろ…300円で1本アナゴ、しかも旨い。','アナゴこれ反則だろ…訪問当時は300円で1本アナゴ、しかも旨い。'),('古民家1棟貸しの料金が1泊4万円ほどで、7名まで利用できることを考えると','訪問当時、古民家1棟貸しは1泊4万円ほどで、7名まで利用できるとのことだったので'),('楽天トラベルやじゃらんでも掲載されているのですが','訪問当時は楽天トラベルやじゃらんにも掲載されていましたが'),('ドラッグストア コスモスさんの駐車場は、観光には使えない設定になっているので要注意！','訪問当時、ドラッグストア コスモスさんの駐車場は観光利用できない設定でした。')),
'ginnjoura-men':(('駐車場があるので車で行きやすいのも良いですね','訪問時は駐車場があり、車で立ち寄りやすいのも良いと感じました。'),),
'agetate-tenpura-hongo':(('広い駐車場があり、家族連れはもちろん、トラックドライバーさん達も入りやすい作りになっています。','訪問時は広い駐車場があり、家族連れはもちろん、トラックドライバーさん達も入りやすい作りだと感じました。'),),
}

def apply_repl(slug,s):
    n=0
    for a,b in REPL.get(slug,()):
        if a in s:s=s.replace(a,b);n+=1
    return s,n

def omit_placeholder(a,needle):
    old=list(a.get('placeholders') or []); rem=[x for x in old if needle in x]
    if not rem:return 0
    a['placeholders']=[x for x in old if x not in rem]; om=list(a.get('omitted_photo_positions') or [])
    for x in rem:
        m=re.match(r'【写真差し込み：旧画像(\d+) / (.*?) / (.*?)】$',x)
        if m:om.append({'image_order':int(m.group(1)),'legacy_filename':m.group(2),'nearest_heading':m.group(3),'reason':'関連記事由来で当該記事の理解に不要なため省略'})
    a['omitted_photo_positions']=om; return len(rem)

def remove_orphan(bs):
    out=[];removed=0;i=0
    while i<len(bs):
        b=bs[i]
        if typ(b)!='heading':out.append(b);i+=1;continue
        j=i+1; has=False
        while j<len(bs) and typ(bs[j])!='heading':
            if typ(bs[j]) in ('paragraph','image') and txt(bs[j]):has=True;break
            j+=1
        if not has:
            removed+=1;i+=1;continue
        out.append(b);i+=1
    return out,removed

def dedupe_images(bs,a):
    seen=set();out=[];removed=[]
    for b in bs:
        if typ(b)=='image':
            m=re.search(r'wp-image-(\d+)',b)
            if m:
                mid=int(m.group(1))
                if mid in seen: removed.append(mid);continue
                seen.add(mid)
        out.append(b)
    if removed:
        ids=list(a.get('matched_media_ids') or []); urls=list(a.get('matched_media_source_urls') or [])
        kept_i=[];kept_u=[];used=set();om=[]
        for mid,url in zip(ids,urls):
            if mid in used:om.append({'media_id':mid,'source_url':url,'reason':'同一記事内で同じ確定写真が重複するため省略'});continue
            used.add(mid);kept_i.append(mid);kept_u.append(url)
        a['matched_media_ids']=kept_i;a['matched_media_source_urls']=kept_u;a['matched_media_omitted_redundant']=om
    else:a['matched_media_omitted_redundant']=[]
    return out,len(removed)

def rebuild_hiroshima(bs):
    prefix=[b for b in bs if typ(b)=='paragraph' and txt(b).startswith(('この記事は、','営業時間・料金・商品仕様'))]
    ph=[b for b in bs if typ(b)=='paragraph' and '【写真差し込み' in txt(b)]
    return prefix+[wp_h('東広島で実際に食べてよかった店'),wp_p('旧つりくえ！では、西条町下見のラーメン亭・民都、西条中央のらー亭と焼肉あさひ、安芸津のいろは寿司など、実際に食べて印象に残った店を個別記事で紹介していました。'),wp_h('広島市内・安佐北区で印象に残った店'),wp_p('広島駅近くの博多ラーメン みちまる、安佐北区のマシューも、また食べに行きたいと思った店です。店ごとの詳しい感想は、それぞれの復活記事で紹介します。'),wp_h('旅先で印象に残ったグルメ'),wp_p('広島以外では、境港で食べた松葉ガニや、浜村温泉・魚と屋の食事も強く印象に残っています。広島の店を中心に、実際に食べた記録を少しずつ掘り起こしていきます。')]+ph

def rebuild_sanin(bs):
    kept=[]
    for b in bs:
        if typ(b)=='heading' and txt(b)=='松江城':break
        kept.append(b)
    return kept+[wp_h('島根県で印象に残っている場所'),wp_p('出雲大社や宍道湖に加えて、松江城など、歴史や景色を楽しめる場所を巡りました。山陰旅行では、目的地を一つだけに絞らず周辺も一緒に回るのが楽しかったです。'),wp_h('鳥取県西部で立ち寄りたい場所'),wp_p('鳥取県西部では、境港、皆生温泉、大山、青山剛昌ふるさと館などを旧記事で紹介していました。海鮮・温泉・景色を組み合わせやすく、ドライブで回るのが楽しいエリアです。'),wp_h('鳥取県東部で立ち寄りたい場所'),wp_p('鳥取県東部では、中国庭園 燕趙園、砂の美術館、鳥取砂丘などを巡りました。個別の体験は鳥取ドライブ記事側にまとめ直しています。'),wp_h('まとめ'),wp_p('山陰は、グルメ・観光・景色を一度の旅行で楽しめるのが魅力でした。日帰りでも遊べますが、行きたい場所が増えやすいので、時間に余裕を持ったドライブ旅行がよく合います。')]

def compact_kotamagai(bs):
    second=None
    for i,b in enumerate(bs):
        if typ(b)=='paragraph' and txt(b).startswith('オキアサリはコタマガイとは別種の貝です'):
            second=i;break
    if second is None:return bs
    return bs[:second]+[wp_h('オキアサリも同じ方法で食べてみた'),wp_p('オキアサリはコタマガイとは別種ですが、見た目はよく似ています。当時はオキアサリも殻を洗い、コタマガイと同じようにバター焼きにしました。'),wp_p('食べてみると、こちらも濃厚な貝の旨味とバターの相性が良くて満足。以前アオリイカと一緒にイカスミパスタへ使った時も美味しかったので、オキアサリもまた採りに行きたいと思った貝でした。')]

def collapse_ginn(bs):
    out=[];inserted=False
    for b in bs:
        t=txt(b)
        if typ(b)=='paragraph' and (re.search(r'\d{1,2}[:：]\d{2}',t) or ('営業時間' in t and '定休日' in t)):
            if not inserted:out.append(wp_p('訪問当時は昼・夜の二部制で、水曜日が定休日という案内でした。回収できた旧記録には営業時間の表記違いがあるため、来店前に最新情報をご確認ください。'));inserted=True
            continue
        out.append(b)
    return out

def finalize(a):
    a=dict(a);before=a['content']; before_n=chars(before); cnt=Counter(); fixes=0
    bs=[]
    for b in blocks(before):
        t=txt(b)
        if typ(b)=='paragraph':
            nt,ch=natural(a['slug'],t); fixes+=int(ch); t=nt
            t,n=apply_repl(a['slug'],t);fixes+=n
            if a['slug']=='inbloombeppu' and (t.endswith('1棟貸しプランを') or t in ('0977222449','PGFTCS') or '招待コード' in t or 'HafH' in t or '紹介キャンペーン' in t or '100コイン' in t):cnt['truncated' if t.endswith('1棟貸しプランを') else 'affiliate']+=1;continue
            if a['slug']=='yakitori-riku' and any(k in t for k in ('チチヤス チー坊','通販でチー坊','管理釣り場の魚は美味しい','ソウルドリンク チー坊')):cnt['affiliate']+=1;continue
            if a['slug']=='gulpalivepowder' and any(k in t for k in ('魚のヤル気スイッチ','Berkley Gulp','ポイント10倍','楽天市場')):cnt['affiliate']+=1;continue
            if a['slug']=='inbloombeppu' and '0977222449' in t:
                t=t.replace('わからないことが有れば0977222449に電話をするようです。','わからないことがあれば、案内されていた連絡先へ確認できる形でした。')
                b=repl_block(b,t);fixes+=1
            else:
                b=repl_block(b,t)
        bs.append(b)
    slug=a['slug']
    if slug=='hiroshima-gourmet':bs=rebuild_hiroshima(bs)
    if slug=='sanin-sightseeing':bs=rebuild_sanin(bs)
    if slug=='kotamagairyouri':bs=compact_kotamagai(bs);cnt['duplicate']+=1
    if slug=='ginnjoura-men':bs=collapse_ginn(bs)
    drop={
      'yamaguchi-drive':('各観光地の個別記事はコチラ！',),
      'ramenkou':('店舗情報',),'matsuura':('【らーめんまつうら】店舗情報',),
      'hiroshima-station-ramen-michimaru':('メニュー','お店の情報'),
      'yakitori-riku':('関連記事','通販で買えるチー坊'),
      'inbloombeppu':('お得に泊まれるかも？オススメの宿泊予約サービス',),
    }
    if slug in drop:
        nb=[]
        for b in bs:
            if typ(b)=='heading' and any(k in txt(b) for k in drop[slug]):cnt['orphan_heading']+=1;continue
            nb.append(b)
        bs=nb
    bs=[b for b in bs if not (typ(b)=='heading' and txt(b)=='記事内で使う写真・確認用')]
    bs,n=remove_orphan(bs);cnt['orphan_heading']+=n
    if slug=='yakitori-riku':cnt['placeholder_omitted']+=omit_placeholder(a,'管理釣り場の魚は美味しい')
    bs,n=dedupe_images(bs,a);cnt['duplicate']+=n
    content='\n\n'.join(bs).strip()+'\n';after_n=chars(content);red=max(0,(before_n-after_n)/before_n) if before_n else 0
    a['content']=content;a['wordpress_write_count']=a['draft_creation_count']=a['media_upload_count']=0
    q={'slug':slug,'visible_chars_before':before_n,'visible_chars_after':after_n,'reduction_ratio':round(red,6),'changes_by_reason':{r:int(cnt[r]) for r in REASONS},'text_fixes':fixes,'under_800_before':before_n<800,'under_800_after':after_n<800,'became_under_800':before_n>=800 and after_n<800,'requires_review_25pct':red>=WARN,'fails_50pct':red>=FAIL}
    a['phase32_qa']=q;return a,q

def content_has_terminal_orphan_heading(c):
    bs=blocks(c);return bool(bs and typ(bs[-1])=='heading')
def terminal_heading(c): return content_has_terminal_orphan_heading(c)
def validate(arts,qs):
    if len(arts)!=N or len({a['slug'] for a in arts})!=N:raise ValueError('scope')
    av=sum(int(a.get('matched_images_available',len(a.get('matched_media_ids') or [])+len(a.get('matched_media_omitted_redundant') or []))) for a in arts)
    used=sum(len(a.get('matched_media_ids') or []) for a in arts);mo=sum(len(a.get('matched_media_omitted_redundant') or []) for a in arts)
    if av!=MATCH or used+mo!=MATCH:raise ValueError(f'matched disposition {av=} {used=} {mo=}')
    ph=sum(len(a.get('placeholders') or []) for a in arts);om=sum(len(a.get('omitted_photo_positions') or []) for a in arts)
    if ph+om!=UNRES:raise ValueError(f'unresolved {ph}+{om}')
    blob='\n'.join(a['content'] for a in arts)
    for bad in BANNED:
        if bad in blob.lower():raise ValueError(bad)
    for bad in ('訪問当時の所在地：山口県は','訪問当時の所在地：鳥取県は','訪問当時の所在地：島根県','訪問当時の所在地：広島県民','訪問当時の所在地：大分県日田市は','記事内で使う写真・確認用','1棟貸しプランを</p>'):
        if bad in blob:raise ValueError(bad)
    if any(terminal_heading(a['content']) for a in arts):raise ValueError('terminal heading')
    if any(q['fails_50pct'] for q in qs):raise ValueError('50pct reduction')
    if any(q['became_under_800'] and not any(q['changes_by_reason'].values()) for q in qs):raise ValueError('unexplained short')

def write(out,arts,qs):
    validate(arts,qs);d=out/'articles';d.mkdir(parents=True,exist_ok=True);rows=[]
    for a in sorted(arts,key=lambda x:x['slug']):
        s=a['slug'];(d/f'{s}.html').write_text(a['content'],encoding='utf-8');(d/f'{s}.json').write_text(json.dumps(a,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        rows.append({'slug':s,'title':a['title'],'characters':chars(a['content']),'matched_images_available':int(a.get('matched_images_available',len(a.get('matched_media_ids') or [])+len(a.get('matched_media_omitted_redundant') or []))),'matched_images':len(a.get('matched_media_ids') or []),'matched_images_omitted_redundant':len(a.get('matched_media_omitted_redundant') or []),'placeholders':len(a.get('placeholders') or []),'omitted_photos':len(a.get('omitted_photo_positions') or []),'status':'FINAL_QA_GENERATED'})
    ph=sum(x['placeholders'] for x in rows);om=sum(x['omitted_photos'] for x in rows);summary={'targets':46,'lexus_targets':0,'articles_generated':46,'matched_images_available':sum(x['matched_images_available'] for x in rows),'matched_images_used':sum(x['matched_images'] for x in rows),'matched_images_omitted_redundant':sum(x['matched_images_omitted_redundant'] for x in rows),'placeholders_retained':ph,'unresolved_positions_omitted':om,'unresolved_positions_total':ph+om,'short_articles_under_800_before':sum(q['under_800_before'] for q in qs),'short_articles_under_800_after':sum(q['under_800_after'] for q in qs),'newly_under_800':sum(q['became_under_800'] for q in qs),'articles_reduced_25pct_or_more':sum(q['requires_review_25pct'] for q in qs),'articles_reduced_50pct_or_more':sum(q['fails_50pct'] for q in qs),'wordpress_write_count':0,'draft_creation_count':0,'media_upload_count':0}
    out.mkdir(parents=True,exist_ok=True);(out/'index.json').write_text(json.dumps({'summary':summary,'articles':rows},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (out/'index.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    rep={'summary':summary,'articles':qs};(out/'final-qa-report.json').write_text(json.dumps(rep,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');(out/'summary.md').write_text('\n'.join(['# Phase 3.2 final QA','']+[f'- {k}: **{v}**' for k,v in summary.items()])+'\n',encoding='utf-8');return rep

def build_from_phase31_dir(src,out):
    ps=sorted((src/'articles').glob('*.json'))
    if len(ps)!=N:raise ValueError(f'need 46 phase31 articles, got {len(ps)}')
    arts=[];qs=[]
    for p in ps:a=json.loads(p.read_text(encoding='utf-8'));o,q=finalize(a);arts.append(o);qs.append(q)
    return write(out,arts,qs)
def build(out):
    import old_tsurikue_remake_qa_dry_run as p31
    with tempfile.TemporaryDirectory(prefix='old-tsurikue-p31-') as td:
        src=Path(td)/'p31';p31.build(src);return build_from_phase31_dir(src,out)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output-dir',type=Path,default=Path('reports/old-tsurikue-remake-final-qa-dry-run'));ap.add_argument('--phase31-dir',type=Path);a=ap.parse_args();r=build_from_phase31_dir(a.phase31_dir,a.output_dir) if a.phase31_dir else build(a.output_dir);print(json.dumps(r['summary'],ensure_ascii=False,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
