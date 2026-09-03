#!/usr/bin/env python3
from __future__ import annotations
import base64, html, json, os, re, time, urllib.parse, urllib.request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
SITE='https://tsurikue.com'; BASE=SITE+'/wp-json/wp/v2'; PAGE_ID=3289; GOURMET_CAT=9; HERO='https://tsurikue.com/wp-content/uploads/2026/09/img_7358.jpg'; UA='tsurikue-gourmet-top/1.0'
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()
GENRE_SLUGS=['ramen','seafood','meat-hearty','local-gourmet','cafe-sweets']
CURATED={'hiroshima-gourmet':[],'chibou':['local-gourmet'],'hiroshima-koorogi':['local-gourmet'],'shiosoba-maeda-hiroshima':['ramen'],'matubagani':['seafood','local-gourmet'],'irohasushi':['seafood'],'higashihiroshima-ramen':['ramen'],'agetate-tenpura-hongo':[]}
REGIONS=[('hiroshima','広島'),('etajima','江田島'),('yamaguchi','山口'),('sanin','山陰')]
def req(path,method='GET',payload=None):
 h={'Authorization':AUTH,'Accept':'application/json','User-Agent':UA}; data=None
 if payload is not None:data=json.dumps(payload,ensure_ascii=False).encode();h['Content-Type']='application/json; charset=utf-8'
 r=urllib.request.Request(BASE+path,data=data,headers=h,method=method)
 with urllib.request.urlopen(r,timeout=60) as x:return json.loads(x.read().decode()),dict(x.headers)
def clean(v):
 if isinstance(v,dict):v=v.get('raw') or v.get('rendered') or ''
 return html.unescape(re.sub(r'<[^>]+>',' ',v or '')).strip()
def rows(ep,params):
 out=[];p=1
 while True:
  q=dict(params,per_page=100,page=p);r,h=req('/'+ep+'?'+urllib.parse.urlencode(q));out+=r
  if p>=int(h.get('X-WP-TotalPages','1')):return out
  p+=1
def totals():
 o={}
 for ep in ('posts','pages'):
  _,h=req(f'/{ep}?status=publish&per_page=1&_fields=id');o[ep]=int(h.get('X-WP-Total','0'))
 return o
def esc(s):return html.escape(str(s),quote=True)
def termmap():
 tags=rows('tags',{'context':'edit','hide_empty':'false','_fields':'id,name,slug,count'});b={t['slug']:t for t in tags};m=[s for s in GENRE_SLUGS if s not in b]
 if m:raise RuntimeError('MISSING_GENRE_TAGS '+','.join(m))
 return b
def posts():return rows('posts',{'context':'edit','status':'publish','categories':str(GOURMET_CAT),'orderby':'date','order':'desc','_fields':'id,slug,link,title,tags,featured_media'})
def media_url(mid):
 if not mid:return ''
 m,_=req(f'/media/{mid}?_fields=source_url');return m.get('source_url') or ''
def curate(ps,tags):
 known={p['slug'] for p in ps}
 if known!=set(CURATED):raise RuntimeError('GOURMET_POST_SET_CHANGED '+json.dumps({'known':sorted(known),'expected':sorted(CURATED)},ensure_ascii=False))
 genre_ids={int(tags[s]['id']) for s in GENRE_SLUGS};changed=[]
 for p in ps:
  old=list(map(int,p.get('tags') or []));new=[x for x in old if x not in genre_ids]+[int(tags[s]['id']) for s in CURATED[p['slug']]]
  if new!=old:req(f"/posts/{p['id']}",method='POST',payload={'tags':new});changed.append({'slug':p['slug'],'genres':CURATED[p['slug']]})
 return changed
def cards(items):
 out=[]
 for p in items:
  img=media_url(p.get('featured_media') or 0);pic=f'<img src="{esc(img)}" alt="" loading="lazy">' if img else '<span class="tq-food-card-ph">つりくえ！</span>'
  out.append(f'<a class="tq-food-card" href="{esc(p["link"])}">{pic}<span>{esc(clean(p["title"]))}</span></a>')
 return ''.join(out)
def build(ps,tags):
 meta=[('ramen','ラーメン','麺をすすりたい日'),('seafood','海鮮','魚・カニ・海鮮丼'),('meat-hearty','肉・がっつり','腹いっぱい食べたい日'),('local-gourmet','ご当地グルメ','旅先・地元の変わり種'),('cafe-sweets','カフェ・甘いもの','甘いもの休憩')];genre=[]
 for slug,name,sub in meta:
  t=tags[slug];matched=[p for p in ps if int(t['id']) in list(map(int,p.get('tags') or []))]
  genre.append(f'<details class="tq-food-acc tq-genre-{slug}"{" open" if slug=="ramen" else ""}><summary><span><small>{esc(sub)}</small><strong>{esc(name)}</strong></span><b>{len(matched)}記事</b></summary><div class="tq-food-list">{cards(matched) if matched else "<p class=\"tq-empty\">これから増やします🍴</p>"}</div><a class="tq-tag-link" href="{SITE}/tag/{esc(t["slug"])}/">#{esc(clean(t["name"]))} を全部見る →</a></details>')
 region=[]
 for slug,name in REGIONS:
  t=tags.get(slug)
  if not t:continue
  matched=[p for p in ps if int(t['id']) in list(map(int,p.get('tags') or []))]
  if matched:region.append(f'<details class="tq-food-acc tq-region-{slug}"><summary><span><small>AREA</small><strong>{esc(name)}で食べる</strong></span><b>{len(matched)}記事</b></summary><div class="tq-food-list">{cards(matched)}</div><a class="tq-tag-link" href="{SITE}/tag/{esc(t["slug"])}/">#{esc(clean(t["name"]))} を全部見る →</a></details>')
 return f'''<!-- wp:html --><style>
body:has(.tq-gourmet-top) .c-pageTitle,body:has(.tq-gourmet-top) .p-breadcrumb{{display:none!important}}body:has(.tq-gourmet-top) .l-content{{padding:0!important;width:100%!important;max-width:none!important}}body:has(.tq-gourmet-top) .l-mainContent,body:has(.tq-gourmet-top) .l-mainContent__inner,body:has(.tq-gourmet-top) .post_content{{width:100%!important;max-width:none!important;margin:0!important;padding:0!important}}body:has(.tq-gourmet-top) .l-sidebar{{display:none!important}}body:has(.tq-gourmet-top){{overflow-x:clip}}.tq-gourmet-top,.tq-gourmet-top *{{box-sizing:border-box}}.tq-gourmet-top{{--ink:#24211d;--sub:#716b62;--paper:#f8f5ee;--line:#e2ddd2;background:var(--paper);color:var(--ink)}}.tq-gourmet-top a{{color:inherit;text-decoration:none}}.tq-food-hero{{position:relative;min-height:540px;background:url('{HERO}') center 56%/cover no-repeat;display:flex;align-items:flex-end;overflow:hidden}}.tq-food-hero:before{{content:"";position:absolute;inset:0;background:linear-gradient(90deg,rgba(25,13,8,.68),rgba(28,16,10,.32) 68%,rgba(0,0,0,.16))}}.tq-food-hero-in{{position:relative;z-index:1;width:min(1080px,90vw);margin:auto;padding:110px 0 74px;color:#fff;text-shadow:0 2px 12px #0007}}.tq-food-kicker{{font-size:11px;font-weight:900;letter-spacing:.18em}}.tq-food-hero h1{{margin:22px 0 0;font-size:clamp(46px,6.7vw,78px);line-height:1.04;letter-spacing:-.055em;color:#fff!important;background:none!important;padding:0!important}}.tq-food-hero p{{max-width:660px;margin:24px 0 0;font-size:clamp(15px,1.7vw,18px);font-weight:700;line-height:1.9}}.tq-food-wrap{{width:min(1080px,90vw);margin:auto}}.tq-food-section{{padding:clamp(62px,8vw,96px) 0}}.tq-food-section.white{{background:#fff}}.tq-food-head small{{font-size:10px;font-weight:900;letter-spacing:.16em;color:#9b6b3e}}.tq-food-head h2{{margin:10px 0 0!important;padding:0!important;border:0!important;background:none!important;color:var(--ink)!important;font-size:clamp(30px,4vw,46px)}}.tq-food-head p{{margin:12px 0 30px;color:var(--sub);font-size:13px;line-height:1.9}}.tq-food-acc{{margin:10px 0;border:1px solid var(--line);border-radius:18px;background:#fff;overflow:hidden}}.tq-food-acc summary{{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:20px 22px;cursor:pointer;list-style:none}}.tq-food-acc summary::-webkit-details-marker{{display:none}}.tq-food-acc summary span{{display:flex;flex-direction:column;gap:4px}}.tq-food-acc summary small{{font-size:9px;font-weight:900;letter-spacing:.12em;color:#9a7a5f}}.tq-food-acc summary strong{{font-size:20px}}.tq-food-acc summary b{{font-size:11px;color:#756f67}}.tq-food-list{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;padding:0 18px 18px}}.tq-food-card{{display:flex;flex-direction:column;gap:10px;padding:10px;border:1px solid var(--line);border-radius:14px;background:var(--paper);font-size:13px;font-weight:800;line-height:1.55}}.tq-food-card img,.tq-food-card-ph{{width:100%;height:135px;object-fit:cover;border-radius:9px;background:#eadfcf;display:flex;align-items:center;justify-content:center;color:#8d795f}}.tq-tag-link{{display:block;margin:0 18px 18px;font-size:11px;font-weight:900;color:#9a6638!important}}.tq-empty{{grid-column:1/-1;margin:0;padding:20px;color:var(--sub);font-size:12px}}.tq-latest-grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}}.tq-food-final{{background:#efb530;padding:54px 0}}.tq-food-final h2{{margin:0!important;padding:0!important;border:0!important;background:none!important;color:#292218!important;font-size:clamp(28px,4vw,44px)}}.tq-food-final a{{display:inline-flex;margin-top:18px;padding:13px 20px;border:1px solid #55461f;border-radius:999px;font-size:12px;font-weight:900}}@media(max-width:760px){{.tq-food-hero{{min-height:500px}}.tq-food-hero-in{{padding:95px 0 55px}}.tq-food-hero h1{{font-size:43px}}.tq-food-list,.tq-latest-grid{{grid-template-columns:1fr 1fr}}}}@media(max-width:520px){{.tq-food-list,.tq-latest-grid{{grid-template-columns:1fr}}.tq-food-card img,.tq-food-card-ph{{height:170px}}}}
</style><div class="tq-gourmet-top"><section class="tq-food-hero"><div class="tq-food-hero-in"><div class="tq-food-kicker">EAT / TSURIKUE!</div><h1>今日は、<br>なに食べる？</h1><p>有名だからではなく、実際に食べたものだけ。近所の一杯も、旅先で見つけたごはんも、また食べたい記憶から選びます。</p></div></section><section class="tq-food-section white"><div class="tq-food-wrap"><div class="tq-food-head"><small>CHOOSE YOUR MEAL</small><h2>食べたいものから探す</h2><p>ラーメン、海鮮、肉、ご当地グルメ。今日のお腹に近いところからどうぞ。</p></div>{''.join(genre)}</div></section><section class="tq-food-section"><div class="tq-food-wrap"><div class="tq-food-head"><small>AREA</small><h2>どこで食べる？</h2><p>記事がある地域だけ表示。旅先のごはん探しにも使えます。</p></div>{''.join(region) if region else '<p>地域別の記事を整理中です。</p>'}</div></section><section class="tq-food-section white"><div class="tq-food-wrap"><div class="tq-food-head"><small>NEW & UPDATED</small><h2>最近のグルメ</h2><p>つりくえ！で公開・復活したグルメ記事です。</p></div><div class="tq-latest-grid">{cards(ps)}</div></div></section><section class="tq-food-final"><div class="tq-food-wrap"><h2>まだ食べる？😏</h2><a href="{SITE}/category/gourmet/">グルメ記事を全部見る →</a></div></section></div><script>(()=>{{const fit=()=>{{const h=document.querySelector('.tq-food-hero');if(!h)return;h.style.left='0';h.style.width=document.documentElement.clientWidth+'px';const r=h.getBoundingClientRect();h.style.position='relative';h.style.left=(-r.left)+'px';document.documentElement.dataset.tqGourmetHero='ready'}};fit();addEventListener('resize',fit,{{passive:true}})}})();</script><!-- /wp:html -->'''
def verify(ps):
 o=Options();o.add_argument('--headless=new');o.add_argument('--no-sandbox');o.add_argument('--disable-dev-shm-usage');o.add_argument('--window-size=1440,1200');d=webdriver.Chrome(options=o)
 try:d.get(SITE+'/gourmet/?v='+str(int(time.time())));time.sleep(6);m=d.execute_script("const h=document.querySelector('.tq-food-hero'),r=h&&h.getBoundingClientRect();return{hero:r?{left:r.left,right:r.right,width:r.width}:null,vw:document.documentElement.clientWidth,sw:document.documentElement.scrollWidth,fit:document.documentElement.dataset.tqGourmetHero,latest:document.querySelectorAll('.tq-latest-grid .tq-food-card').length};")
 finally:d.quit()
 if m['fit']!='ready' or not m['hero'] or abs(m['hero']['left'])>2 or abs(m['hero']['right']-m['vw'])>2 or m['sw']>m['vw']+2 or m['latest']!=len(ps):raise RuntimeError('BROWSER_VERIFY_FAILED '+json.dumps(m))
 return m
def main():
 before=totals();tags=termmap();ps=posts();changes=curate(ps,tags);ps=posts();page,_=req(f'/pages/{PAGE_ID}?context=edit&_fields=id,slug,status,title')
 req(f'/pages/{PAGE_ID}',method='POST',payload={'title':'グルメ','slug':'gourmet','status':'publish','content':build(ps,tags)})
 after=totals();expected=dict(before);expected['pages']+=0 if page.get('status')=='publish' else 1
 if after!=expected:raise RuntimeError('PUBLIC_TOTALS_UNEXPECTED '+json.dumps({'before':before,'after':after,'expected':expected}))
 metrics=verify(ps)
 print(json.dumps({'ok':True,'action':'GOURMET_TOP_PUBLISHED','page_id':PAGE_ID,'url':SITE+'/gourmet/','gourmet_posts':len(ps),'tag_corrections':changes,'genre_counts':{s:sum(int(tags[s]['id']) in list(map(int,p.get('tags') or [])) for p in ps) for s in GENRE_SLUGS},'browser':metrics,'public_before':before,'public_after':after},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
