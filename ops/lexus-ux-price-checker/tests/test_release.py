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
assert all('color' not in cohort for cohort in data['cohorts'])
assert data.get('display_facets')==['grade','year','mileage']
assert len(data['cohorts'])>=20
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
