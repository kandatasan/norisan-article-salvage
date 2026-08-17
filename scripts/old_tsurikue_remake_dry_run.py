#!/usr/bin/env python3
"""Build 46 old-tsurikue remake artifacts locally. No network and no WordPress writes."""
from __future__ import annotations
import argparse,base64,bz2,csv,html,json,re
from collections import Counter,defaultdict
from pathlib import Path
from typing import Any

HERE=Path(__file__).resolve().parent
SOURCE_PART_GLOB='old_tsurikue_remake_sources.bz2.b64.part*'
PHOTO_MATCHES=HERE/'old_tsurikue_phase2_photo_matches.bz2.b64'
PHOTO_REFS=HERE/'old_tsurikue_recovered_photo_refs.tsv'
EXPECTED_TARGETS=46
REQUIRED_MATCHES=110
REQUIRED_UNMATCHED=253
UNDERSTANDING_KEYWORDS=('手順','作り','料理','実食','メニュー','設備','外観','景色','仕掛け','撮影','寝室','展望')
BANNED=('web.archive.org','lexus-diary.com','<script','<style')

def load_json(path:Path)->Any:
    return json.loads(path.read_text(encoding='utf-8'))

def load_bz2_b64(paths)->str:
    if isinstance(paths,Path): paths=(paths,)
    payload=''.join(p.read_text(encoding='ascii').strip() for p in paths)
    return bz2.decompress(base64.b64decode(payload)).decode('utf-8')

def load_sources()->list[dict[str,Any]]:
    parts=tuple(sorted(HERE.glob(SOURCE_PART_GLOB)))
    if not parts: raise ValueError('missing compressed remake source parts')
    return json.loads(load_bz2_b64(parts))

def load_photo_manifest()->dict[str,Any]:
    matches=json.loads(load_bz2_b64(PHOTO_MATCHES))
    match_by={(r['target_slug'],int(r['image_order'])):r for r in matches['matches']}
    refs=[]
    with PHOTO_REFS.open(encoding='utf-8',newline='') as f:
        for raw in csv.reader(f,delimiter='\t'):
            if not raw: continue
            slug,order,filename=(raw+['','',''])[:3]
            heading=raw[3] if len(raw)>3 else ''
            key=(slug,int(order))
            base={'target_slug':slug,'image_order':int(order),'legacy_filename':filename,'nearest_heading':heading}
            if key in match_by:
                m=match_by[key]
                if m['legacy_filename']!=base['legacy_filename']:
                    raise ValueError(f'Phase 2 filename mismatch for {key}')
                base.update({'result':'MATCH_FILENAME','matched_media_id':int(m['matched_media_id']),'matched_media_source_url':m['matched_media_source_url']})
            else:
                base.update({'result':'PLACEHOLDER','matched_media_id':None,'matched_media_source_url':None})
            refs.append(base)
    return {'targets':matches['targets'],'lexus_targets':matches['lexus_targets'],'refs':refs}

def validate_inputs(sources:list[dict[str,Any]], photos:dict[str,Any])->None:
    if len(sources)!=EXPECTED_TARGETS or len({x['slug'] for x in sources})!=EXPECTED_TARGETS:
        raise ValueError('remake sources must contain exactly 46 unique slugs')
    if photos.get('targets')!=46 or photos.get('lexus_targets')!=0:
        raise ValueError('photo manifest target scope mismatch')
    refs=photos.get('refs') or []
    counts=Counter(x.get('result') for x in refs)
    if len(refs)!=363 or counts['MATCH_FILENAME']!=REQUIRED_MATCHES or counts['PLACEHOLDER']!=REQUIRED_UNMATCHED:
        raise ValueError('Phase 2 photo counts mismatch')
    source_slugs={x['slug'] for x in sources}
    if {x['target_slug'] for x in refs} - source_slugs:
        raise ValueError('photo slug missing from source manifest')
    blob=json.dumps({'sources':sources,'photos':photos},ensure_ascii=False).lower()
    if 'lexus-diary.com' in blob:
        raise ValueError('Lexus source contamination')

def select_placeholders(refs:list[dict[str,Any]])->set[tuple[str,int]]:
    by_slug=defaultdict(list)
    for r in refs:
        if r['result']=='PLACEHOLDER': by_slug[r['target_slug']].append(r)
    selected=set()
    for slug, rows in by_slug.items():
        seen_headings=set(); used=0
        for r in rows:
            heading=(r.get('nearest_heading') or '').strip()
            if not heading or heading in seen_headings: continue
            if any(k in heading for k in UNDERSTANDING_KEYWORDS):
                selected.add((slug,int(r['image_order'])))
                seen_headings.add(heading); used+=1
                if used>=3: break
    return selected

def wp_paragraph(text:str)->str:
    safe=html.escape(text,quote=False).replace('\n','<br>')
    return f'<!-- wp:paragraph -->\n<p>{safe}</p>\n<!-- /wp:paragraph -->'

def wp_heading(text:str,level:int)->str:
    level=3 if level==3 else 2
    safe=html.escape(text,quote=False)
    return f'<!-- wp:heading {{"level":{level}}} -->\n<h{level} class="wp-block-heading">{safe}</h{level}>\n<!-- /wp:heading -->'

def wp_image(ref:dict[str,Any])->str:
    mid=int(ref['matched_media_id']); src=html.escape(ref['matched_media_source_url'],quote=True)
    return ('<!-- wp:image {"id":%d,"sizeSlug":"large","linkDestination":"none"} -->\n'
            '<figure class="wp-block-image size-large"><img src="%s" alt="" class="wp-image-%d"/></figure>\n'
            '<!-- /wp:image -->')%(mid,src,mid)

def placeholder_text(ref:dict[str,Any])->str:
    heading=(ref.get('nearest_heading') or '見出し不明').strip()
    return f"【写真差し込み：旧画像{ref['image_order']} / {ref['legacy_filename']} / {heading}】"

def render_article(source:dict[str,Any], refs:list[dict[str,Any]], selected:set[tuple[str,int]])->dict[str,Any]:
    slug=source['slug']
    matched=[r for r in refs if r['result']=='MATCH_FILENAME']
    selected_ph=[r for r in refs if r['result']=='PLACEHOLDER' and (slug,int(r['image_order'])) in selected]
    omitted=[r for r in refs if r['result']=='PLACEHOLDER' and (slug,int(r['image_order'])) not in selected]
    by_heading=defaultdict(list); top=[]
    for r in matched+selected_ph:
        h=(r.get('nearest_heading') or '').strip()
        (by_heading[h] if h else top).append(r)
    for vals in by_heading.values(): vals.sort(key=lambda x:int(x['image_order']))
    top.sort(key=lambda x:int(x['image_order']))

    pieces=[]
    pieces.append(wp_paragraph('この記事は、実際に体験した当時の記録をもとに、内容を読みやすく整理し直したものです。'))
    if source.get('latest_check'):
        pieces.append(wp_paragraph('営業時間・料金・商品仕様などは変更されている場合があります。利用前に最新の公式情報も確認してください。'))
    for r in top:
        pieces.append(wp_image(r) if r['result']=='MATCH_FILENAME' else wp_paragraph(placeholder_text(r)))

    pending_heading=''
    inserted_for_heading=set()
    for b in source['blocks']:
        tx=b['text'].strip()
        if not tx: continue
        if b['type']=='heading':
            pending_heading=tx
            pieces.append(wp_heading(tx,int(b.get('level') or 2)))
        else:
            pieces.append(wp_paragraph(tx))
            if pending_heading and pending_heading in by_heading and pending_heading not in inserted_for_heading:
                for r in by_heading[pending_heading]:
                    pieces.append(wp_image(r) if r['result']=='MATCH_FILENAME' else wp_paragraph(placeholder_text(r)))
                inserted_for_heading.add(pending_heading)
            pending_heading='' if pending_heading else pending_heading
    leftovers=[]
    for h, rr in by_heading.items():
        if h not in inserted_for_heading:
            leftovers.extend(rr)
    leftovers.sort(key=lambda x:int(x['image_order']))
    if leftovers:
        pieces.append(wp_heading('記事内で使う写真・確認用',2))
        for r in leftovers:
            pieces.append(wp_image(r) if r['result']=='MATCH_FILENAME' else wp_paragraph(placeholder_text(r)))

    content='\n\n'.join(pieces).strip()+'\n'
    low=content.lower()
    for bad in BANNED:
        if bad in low: raise ValueError(f'{slug}: banned output {bad}')
    if 'lexus' in low: raise ValueError(f'{slug}: Lexus text leaked')
    used_ids=[int(r['matched_media_id']) for r in matched]
    return {
        'title':source['title'],'slug':slug,'content':content,
        'matched_media_ids':used_ids,
        'matched_media_source_urls':[r['matched_media_source_url'] for r in matched],
        'placeholders':[placeholder_text(r) for r in selected_ph],
        'omitted_photo_positions':[
            {'image_order':r['image_order'],'legacy_filename':r['legacy_filename'],'nearest_heading':r.get('nearest_heading') or '','reason':'写真なしでも本文理解が成立するため省略'}
            for r in omitted
        ],
        'source_provenance':{'source_titles':source.get('source_titles',[]),'source_count':source.get('source_count',1),'rewrite_policy':source.get('rewrite_policy','')},
        'wordpress_write_count':0,'draft_creation_count':0,'media_upload_count':0,
    }

def build(output_dir:Path)->dict[str,Any]:
    sources=load_sources(); photos=load_photo_manifest()
    validate_inputs(sources,photos)
    refs_by=defaultdict(list)
    for r in photos['refs']: refs_by[r['target_slug']].append(r)
    selected=select_placeholders(photos['refs'])
    articles=[]
    article_dir=output_dir/'articles'; article_dir.mkdir(parents=True,exist_ok=True)
    for src in sources:
        article=render_article(src,refs_by[src['slug']],selected)
        if not article['content'].strip(): raise ValueError(f"empty article {src['slug']}")
        (article_dir/f"{src['slug']}.html").write_text(article['content'],encoding='utf-8')
        (article_dir/f"{src['slug']}.json").write_text(json.dumps(article,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        articles.append(article)
    idx=[]
    for a in articles:
        idx.append({'slug':a['slug'],'title':a['title'],'characters':len(re.sub('<[^>]+>','',a['content'])),'matched_images':len(a['matched_media_ids']),'placeholders':len(a['placeholders']),'omitted_photos':len(a['omitted_photo_positions']),'status':'GENERATED'})
    summary={
        'targets':46,'lexus_targets':0,'articles_generated':len(articles),
        'matched_images_used':sum(x['matched_images'] for x in idx),
        'placeholders_used':sum(x['placeholders'] for x in idx),
        'unmatched_photos_omitted':sum(x['omitted_photos'] for x in idx),
        'wordpress_write_count':0,'draft_creation_count':0,'media_upload_count':0,
    }
    if summary['matched_images_used']!=110 or summary['placeholders_used']!=29 or summary['unmatched_photos_omitted']!=224:
        raise ValueError(f'unexpected Phase 3 totals: {summary}')
    output_dir.mkdir(parents=True,exist_ok=True)
    (output_dir/'index.json').write_text(json.dumps({'summary':summary,'articles':idx},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (output_dir/'index.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(idx[0].keys())); w.writeheader(); w.writerows(idx)
    lines=['# 旧つりくえ！46記事 リメイク本文＋写真配置 dry-run','']+[f'- {k}: **{v}**' for k,v in summary.items()]
    lines+=['','| slug | chars | images | placeholders | omitted |','|---|---:|---:|---:|---:|']
    for x in idx: lines.append(f"| `{x['slug']}` | {x['characters']} | {x['matched_images']} | {x['placeholders']} | {x['omitted_photos']} |")
    (output_dir/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return {'summary':summary,'articles':idx}

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--output-dir',type=Path,default=Path('reports/old-tsurikue-remake-dry-run'))
    args=ap.parse_args(); report=build(args.output_dir); print(json.dumps(report['summary'],ensure_ascii=False,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
