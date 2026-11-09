from pathlib import Path
import json
root=Path(__file__).resolve().parents[1]
html=(root/'index.html').read_text(encoding='utf-8')
data=json.loads((root/'data/reference_price_bands.json').read_text(encoding='utf-8'))
assert data['publication_reviewed'] is False and data['research_preview_only'] is True
assert data['price_basis']=='total'
assert set(data['markets_included'])=={'general_market','lexus_cpo'}
assert html.count('id="general-price"')==1 and html.count('id="cpo-price"')==1
assert html.count('https://px.a8.net/svt/ejp?a8mat=')==1
assert html.count('https://www15.a8.net/0.gif?a8mat=')==1
assert 'rel="sponsored nofollow noopener"' in html
assert "maxYear-minYear<=1" in html
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
