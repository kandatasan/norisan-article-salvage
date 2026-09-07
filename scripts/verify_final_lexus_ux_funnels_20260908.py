#!/usr/bin/env python3
from __future__ import annotations
import base64, json, os, re, urllib.request

SITE='https://tsurikue.com'
UA='tsurikue-verify-final-ux-funnels-20260908/1.0'
G='[blog_parts id="2843"]'; B='[blog_parts id="2846"]'; C='[blog_parts id="2184"]'
POSTS=[
 (2222,'ux-resale','レクサスUXのリセールは？616万円で購入し427万円で売却した記録',(0,2,1)),
 (2240,'ux-mitsumori','レクサスUXの見積もり公開｜総額616万円で選んだ特別仕様車とオプション',(0,0,1)),
 (2329,'ux300h','レクサスUX300hを試乗｜UX250hオーナーが比較して感じた3つの違い',(1,1,1)),
 (2517,'ux-koukai','レクサスUXはひどい？616万円で買って後悔した欠点と満足している理由',(1,1,2)),
 (2870,'lexus-ux-review','レクサスUXの評価・感想は？1万km以上乗った元オーナーが本音レビュー',(1,1,1)),
 (2874,'lexus-ux-poor','レクサスUXは貧乏・見栄っ張りに見える？実際に所有して感じたこと',(1,0,1)),
 (2881,'lexus-ux-buyer','レクサスUXを買う人はどんな人？年齢層・年収・向いている使い方を考える',(1,0,1)),
 (2886,'lexus-ux-size','レクサスUXのサイズは大きい？車幅・全長・取り回しを元オーナー目線で解説',(1,0,1)),
 (2897,'lexus-ux-interior','レクサスUXの内装はしょぼい？実際に触って感じた高級感と気になる部分',(1,0,1)),
 (2902,'lexus-ux-rear-seat','レクサスUXの後部座席は狭い？大人4人で乗った感想と使い勝手を確認',(1,0,1)),
 (2907,'lexus-ux-cargo','レクサスUXの荷室は狭い？ゴルフバッグ・買い物で使えるかをチェック',(1,0,1)),
 (2948,'lexus-ux-used','レクサスUXの中古は狙い目？新車と比べて中古をおすすめしたい理由',(1,0,1)),
 (2956,'lexus-ux-price','レクサスUXの価格はいくら？乗り出し価格とグレード別の違い',(1,0,1)),
 (2962,'lexus-ux-discount','レクサスUXは値引きできる？値引き0円だった実体験と安く買う方法',(1,0,1)),
 (2975,'lexus-ux-model-change','レクサスUXのモデルチェンジはいつ？次期型は出る？生産終了の噂も整理',(1,0,1)),
 (3570,'lexus-ux-emotional-explorer','レクサスUXの特別仕様車エモーショナルエクスプローラーはお得？実際に選んだ理由',(1,1,1)),
]
TOKEN=re.compile(r'<!--\s+/?wp:[\s\S]*?-->'); OPEN=re.compile(r'<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->'); CLOSE=re.compile(r'<!--\s+/wp:([\w\-/]+)\s+-->'); TAG=re.compile(r'<[^>]+>')

def auth():
    raw=f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode(); return 'Basic '+base64.b64encode(raw).decode()

def get(pid):
    req=urllib.request.Request(f'{SITE}/wp-json/wp/v2/posts/{pid}?context=edit',headers={'Authorization':auth(),'Accept':'application/json','User-Agent':UA})
    with urllib.request.urlopen(req,timeout=60) as r:return json.loads(r.read().decode())

def raw(row,key):
    v=row.get(key) or {}; return (v.get('raw') or v.get('rendered') or '') if isinstance(v,dict) else str(v)

def problems(text):
    stack=[]
    for m in TOKEN.finditer(text):
        t=m.group(0); o=OPEN.fullmatch(t); c=CLOSE.fullmatch(t)
        if o:
            if not o.group(2): stack.append(o.group(1))
        elif c:
            if not stack or stack[-1]!=c.group(1): return 1
            stack.pop()
    return len(stack)

def plain(text):
    s=TOKEN.sub(' ',text); s=TAG.sub(' ',s); return re.sub(r'\s+',' ',s).strip()

def main():
    rows=[]
    for pid,slug,title,exp in POSTS:
        row=get(pid); c=raw(row,'content'); t=raw(row,'title')
        assert row['id']==pid and row['slug']==slug and row['status']=='publish' and t==title
        counts=(c.count(G),c.count(B),c.count(C)); assert counts==exp
        assert problems(c)==0
        # Every CTN button must have a recognizable money/vehicle-value bridge immediately before it.
        if counts[2]:
            first=c.find(C); pre=plain(c[max(0,first-2600):first])
            assert any(k in pre for k in ['査定','売却','今の車','愛車','CTN','買取','乗り換え'])
        rows.append((pid,slug,*counts,row.get('featured_media')))

    # Targeted final invariants.
    r=get(2222); rc=raw(r,'content')
    assert rc.count(B)==2
    assert '最初の好奇心査定で「査定先によって、ここまで金額が違うのか」と知っていたので、実際の売却でも1社だけでは決めませんでした。' in rc
    assert 'CTNは最大15社で査定し、高額査定の上位3社とやり取りする仕組みです。</p>\n<!-- /wp:paragraph -->\n\n<!-- wp:shortcode -->\n[blog_parts id="2846"]' not in rc

    k=get(2517); kc=raw(k,'content')
    assert '5か月' not in kc
    for s in ['納車約3か月・5,000km','査定時点：納車約3か月後・走行距離約5,000km','納車から約3か月、走行距離約5,000km','納車約3か月、走行距離約5,000kmの時点']:
        assert s in kc

    # Intentional exception: discount article ends with used-car/Gulliver after the CTN section; this matches its “安く買う” search intent.
    d=get(2962); dc=raw(d,'content'); assert dc.find(C) < dc.find(G)

    print('# Lexus UX monetization final verification')
    print('- result: **SUCCESS**')
    print('- wordpress_write_count: **0**')
    print('- **16/16 published UX articles passed** identity/status/title, CTA-count and Gutenberg checks')
    print('- `ux-resale`: CTN banners **2** at the intended high-intent stages')
    print('- `ux-koukai`: appraisal timing unified to **約3か月・約5,000km**; stale `5か月` references **0**')
    print('- `lexus-ux-discount`: CTN → later Gulliver flow intentionally retained for “安く買う” intent')
    print('- `lexus-ux-emotional-explorer`: live title is valid; earlier warning was audit expectation mismatch only')
    print('\n|id|slug|G|CTN banner|CTN button|featured|')
    print('|---:|---|---:|---:|---:|---:|')
    for row in rows: print(f'|{row[0]}|{row[1]}|{row[2]}|{row[3]}|{row[4]}|{row[5]}|')

if __name__=='__main__': main()
