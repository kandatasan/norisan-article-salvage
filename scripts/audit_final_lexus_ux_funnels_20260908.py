#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, os, re, urllib.request

SITE='https://tsurikue.com'
UA='tsurikue-final-ux-funnel-audit-20260908/1.0'
G='[blog_parts id="2843"]'
B='[blog_parts id="2846"]'
C='[blog_parts id="2184"]'
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
 (3570,'lexus-ux-emotional-explorer','レクサスUX Emotional Explorerとは？特別仕様車を実際に買って感じた魅力と注意点',(1,1,1)),
]
TOKEN=re.compile(r'<!--\s+/?wp:[\s\S]*?-->')
OPEN=re.compile(r'<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->')
CLOSE=re.compile(r'<!--\s+/wp:([\w\-/]+)\s+-->')
TAG=re.compile(r'<[^>]+>')

def auth():
    raw=f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()
    return 'Basic '+base64.b64encode(raw).decode()

def get(pid):
    req=urllib.request.Request(f'{SITE}/wp-json/wp/v2/posts/{pid}?context=edit',headers={'Authorization':auth(),'Accept':'application/json','User-Agent':UA})
    with urllib.request.urlopen(req,timeout=60) as r:return json.loads(r.read().decode())

def raw(row,key):
    v=row.get(key) or {}
    return (v.get('raw') or v.get('rendered') or '') if isinstance(v,dict) else str(v)

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

def pct_positions(text, needle):
    if not text: return '-'
    out=[]; start=0
    while True:
        i=text.find(needle,start)
        if i<0: break
        out.append(f'{round(i/len(text)*100)}%')
        start=i+len(needle)
    return ','.join(out) if out else '-'

def plain(text):
    s=TOKEN.sub(' ',text); s=TAG.sub(' ',s); s=re.sub(r'\s+',' ',s)
    return s.strip()

def timeline_snips(text):
    p=plain(text); hits=[]
    for m in re.finditer(r'(?:約)?[35]か月',p):
        a=max(0,m.start()-120); b=min(len(p),m.end()+180); sn=p[a:b]
        if '査定' in sn or '売却' in sn:
            hits.append(sn)
    return hits[:4]

def yesno(v): return 'Y' if v else '-'

def main():
    print('# Lexus UX monetization final audit (GET only)')
    print('- wordpress_write_count: **0**')
    print('- live authenticated WordPress GET is authoritative')
    print()
    print('|id|slug|G|CTN banner|CTN button|expected|CTA positions|phone note|2-company note|GB problems|status/title|')
    print('|---:|---|---:|---:|---:|---|---|---|---|---:|---|')
    warnings=[]; timeline=[]; shas=[]
    for pid,slug,title,exp in POSTS:
        row=get(pid); c=raw(row,'content'); t=raw(row,'title')
        counts=(c.count(G),c.count(B),c.count(C))
        ident=(row.get('slug')==slug and row.get('status')=='publish' and t==title)
        phone=any(x in c for x in ['電話が少なくて快適','電話が少なく','電話の量は少な','電話ラッシュはもういらない','電話ラッシュはいらない'])
        two=any(x in c for x in ['カーセブンとネクステージの2社','カーセブン＋ネクステージ','2社から連絡'])
        gb=problems(c)
        pos=f'G:{pct_positions(c,G)} B:{pct_positions(c,B)} C:{pct_positions(c,C)}'
        print(f'|{pid}|{slug}|{counts[0]}|{counts[1]}|{counts[2]}|{exp[0]}/{exp[1]}/{exp[2]}|{pos}|{yesno(phone)}|{yesno(two)}|{gb}|{"OK" if ident else "NG"}|')
        shas.append((pid,slug,hashlib.sha256(c.encode()).hexdigest(),len(c),row.get('featured_media')))
        if counts!=exp: warnings.append(f'{slug}: CTA count {counts} != expected {exp}')
        if gb!=0: warnings.append(f'{slug}: Gutenberg problems={gb}')
        if not ident: warnings.append(f'{slug}: identity/status/title mismatch: live slug={row.get("slug")} status={row.get("status")} title={t}')
        # CTN button should not be present without some nearby monetization bridge in the preceding 1800 chars.
        if counts[2]:
            idx=c.find(C)
            pre=plain(c[max(0,idx-2200):idx])
            if not any(k in pre for k in ['査定','売却','今の車','愛車','CTN','買取','乗り換え']):
                warnings.append(f'{slug}: CTN button lacks obvious preceding bridge')
        # Gulliver should live in used/purchase context, not after the final CTN button.
        if counts[0] and counts[2] and c.find(G)>c.rfind(C):
            warnings.append(f'{slug}: Gulliver appears after final CTN button; review flow')
        for sn in timeline_snips(c): timeline.append((slug,sn))
    print('\n## Warnings')
    if warnings:
        for w in warnings: print(f'- ⚠️ {w}')
    else: print('- **None** — CTA counts, identities, publish status, and Gutenberg structure match the intended final design.')
    print('\n## Appraisal timeline snippets touching funnel-adjacent copy')
    if timeline:
        for slug,sn in timeline:
            print(f'- **{slug}**: {sn}')
    else: print('- none')
    print('\n## Live fingerprints')
    for pid,slug,sha,n,featured in shas:
        print(f'- {pid} `{slug}` sha `{sha}` chars {n} featured_media {featured}')

if __name__=='__main__': main()
