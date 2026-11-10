from pathlib import Path
import json
root=Path(__file__).resolve().parents[1]
html=(root/'index.html').read_text(encoding='utf-8')
data=json.loads((root/'data/reference_price_bands.json').read_text(encoding='utf-8'))
assert data['publication_reviewed'] is True and data['research_preview_only'] is False
assert data['limited_sample_release'] is True
assert 'publication_caveats' in data and len(data['publication_caveats']) >= 3
assert data['price_basis']=='total'
assert set(data['markets_included'])=={'general_market','lexus_cpo'}
assert html.count('id="general-price"')==1 and html.count('id="cpo-price"')==1
assert '<h1>レクサスUX 中古相場チェックツール</h1>' in html
assert '※価格は参考程度です。' in html
assert '価格について：</strong>' not in html
assert 'カーセンサーでUXの中古相場を見る' not in html
assert '本気で愛車を探すなら' not in html
assert 'px.a8.net' not in html
assert 'www15.a8.net' not in html
assert 'ガリバー' not in html
assert 'PR｜' not in html
assert 'class="cta"' not in html

assert "maxYear-minYear<=4" in html
assert 'id="color"' not in html
assert "c=$('color')" not in html
assert 'カラー未反映' not in html
assert '複数年式の参考値' in html
assert "if(b.grade==='all'||b.grade!==grade) return false;" in html
assert "'all','全グレード'" not in html
assert '全グレード' not in html
assert '中央値約' in html
assert data.get('grade_specific_display_policy') == 'no_grade_all; exact_grade_only; no_same_price_fallback; exact_year_or_same_grade_observed_range'
assert data.get('archived_pooled_cohort_count') == 17
assert len(data['cohorts']) == data.get('active_specific_grade_cohort_count') == 12
assert all(c['grade']!='all' for c in data['cohorts'])
assert len([c for c in data['cohorts'] if c.get('research_audit_file')=='research/ux_cpo_grade_observations_20261111.json'])==3
assert any(c['model']=='250h' and c['grade']=='fs' and c['year']==2021 and c['market_segment']=='general_market' and c['sample_size']==5 for c in data['cohorts'])
assert any(c['model']=='250h' and c['grade']=='fs' and c['year']==2019 and c['market_segment']=='general_market' and c['sample_size']==5 for c in data['cohorts'])
assert any(c['model']=='300h' and c['grade']=='fs' and c['year']==2024 and c['market_segment']=='lexus_cpo' and c['sample_size']==7 for c in data['cohorts'])
assert any(c['model']=='250h' and c['grade']=='c' and c['year']==2020 and c['market_segment']=='general_market' and c['sample_size']==7 for c in data['cohorts'])
assert any(c['model']=='250h' and c['grade']=='c' and c['year']==2020 and c['market_segment']=='lexus_cpo' and c['sample_size']==6 for c in data['cohorts'])
assert all('color' not in cohort for cohort in data['cohorts'])
assert data.get('display_facets')==['grade','year','mileage']
assert len(data['cohorts']) >= 12
keys=set()
for b in data['cohorts']:
  assert b['market_segment'] in {'lexus_cpo','general_market'}
  assert b['model'] in {'200','250h','300h','300e'}
  assert b['year']=='any' or (2018<=b['year']<=2026)
  assert b['sample_size']>=5
  assert b['lower_man']<=b['median_man']<=b['upper_man']
  assert len(b['observed_years'])==2
  assert b['observed_years'][0]<=b['observed_years'][1]
  key=(b['market_segment'],b['model'],b['grade'],str(b['year']),tuple(b['observed_years']))
  assert key not in keys,key
  keys.add(key)
print('UX_PRICE_GUARDED_RELEASE=PASS; sample_cohorts='+str(len(keys)))
