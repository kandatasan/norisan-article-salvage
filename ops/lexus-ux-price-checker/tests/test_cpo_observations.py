#!/usr/bin/env python3
"""Recompute published UX CPO reference bands from source-linked per-car observations.
No inventory/availability claim, no network access, and no modification to production data.
"""
from pathlib import Path
from collections import defaultdict
from math import floor, ceil, isclose
import json
from urllib.parse import urlsplit

root=Path(__file__).resolve().parents[1]
raw=json.loads((root/'research/ux_cpo_grade_observations_20261111.json').read_text(encoding='utf-8'))
published=json.loads((root/'data/reference_price_bands.json').read_text(encoding='utf-8'))
records=raw['observations']
assert len(records)==33
assert len(raw['derived_bands'])==4
assert len({r['identity_key'] for r in records})==len(records)
by_group=defaultdict(list)
for r in records:
    assert r['market_segment']=='lexus_cpo'
    assert r['grade'] in {'fs','l'}
    assert r['model'] in {'250h','300h'}
    assert r['year'] in {2023,2024}
    assert isinstance(r['odometer_km'],int) and 0<=r['odometer_km']<=100000
    assert isinstance(r['total_man'],(int,float)) and r['total_man']>100
    assert urlsplit(r['source_url']).hostname=='cpo.lexus.jp'
    assert r['availability_claim'] is False
    expected=f"{r['model']}-{r['grade']}-{r['year']}|{r['dealer']}|{r['odometer_km']}|{r['total_man']}"
    assert r['identity_key']==expected
    by_group[(r['model'],r['grade'],r['year'],r['market_segment'])].append(r)

def quantile(values,p):
    seq=sorted(values)
    index=(len(seq)-1)*p
    a,b=floor(index),ceil(index)
    return seq[a]+(seq[b]-seq[a])*(index-a)

for (model,grade,year,segment),observations in by_group.items():
    assert len(observations)>=5
    assert len({r['dealer'] for r in observations})==len(observations), 'same dealer requires additional identity verification'
    total=[r['total_man'] for r in observations]
    expected={
        'sample_size':len(total),
        'lower_man':floor(quantile(total,.25)/10)*10,
        'median_man':quantile(total,.5),
        'upper_man':ceil(quantile(total,.75)/10)*10,
        'observed_km_span':[min(r['odometer_km'] for r in observations),max(r['odometer_km'] for r in observations)]
    }
    cohort=next(c for c in published['cohorts'] if
        (c['model'],c['grade'],c['year'],c['market_segment'])==(model,grade,year,segment))
    assert cohort['research_audit_file']=='research/ux_cpo_grade_observations_20261111.json'
    for key,value in expected.items():
        actual=cohort[key]
        if key=='median_man':assert isclose(actual,value,abs_tol=.00001),(cohort,key,actual,value)
        else:assert actual==value,(cohort,key,actual,value)
assert len(by_group)==4
print('UX_CPO_33_INDIVIDUAL_OBSERVATIONS=PASS; auditable_grade_bands=4')
