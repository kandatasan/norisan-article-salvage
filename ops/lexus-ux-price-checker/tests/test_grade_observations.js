const fs=require('fs'),path=require('path'),assert=require('assert');
const root=path.resolve(__dirname,'..');
const research=JSON.parse(fs.readFileSync(path.join(root,'research/grade_specific_observations_20261111.json'),'utf8'));
const publicData=JSON.parse(fs.readFileSync(path.join(root,'data/reference_price_bands.json'),'utf8'));
const archive=JSON.parse(fs.readFileSync(path.join(root,'research/archived_mixed_grade_cohorts_20261111.json'),'utf8'));
const q=(arr,p)=>{const pos=(arr.length-1)*p,lo=Math.floor(pos),hi=Math.ceil(pos);return arr[lo]+(arr[hi]-arr[lo])*(pos-lo)};
assert.equal(archive.cohorts.length,17);
assert(archive.cohorts.every(b=>b.grade==='all'));
assert(publicData.cohorts.every(b=>b.grade!=='all'));
assert.equal(research.groups.length,3);
const globalKeys=new Set();
for(const g of research.groups){
  assert(g.records.length>=5,'Do not publish tiny groups');
  const prices=[];
  for(const r of g.records){
    assert(Number.isFinite(r.total_price_man)&&r.total_price_man>0);
    assert(Number.isInteger(r.mileage_km)&&r.mileage_km>0);
    assert(/^https:\/\/(ctn-net\.jp|www\.goo-net\.com|cpo\.lexus\.jp)\//.test(r.source_page));
    const key=[g.model,g.grade,g.year,g.market_segment,r.dealer,r.mileage_km].join('|');
    assert(!globalKeys.has(key),'Duplicate seller/model/grade/year/mileage');
    globalKeys.add(key);prices.push(r.total_price_man);
  }
  prices.sort((a,b)=>a-b);
  const lower=Math.floor(q(prices,.25)/10)*10;
  const upper=Math.ceil(q(prices,.75)/10)*10;
  const c=publicData.cohorts.filter(b=>b.model===g.model&&b.grade===g.grade&&b.year===g.year&&b.market_segment===g.market_segment);
  assert.equal(c.length,1);
  assert.equal(c[0].sample_size,prices.length);
  assert.equal(c[0].lower_man,lower);
  assert.equal(c[0].median_man,q(prices,.5));
  assert.equal(c[0].upper_man,upper);
  assert.equal(c[0].research_source,'research/grade_specific_observations_20261111.json');
}
assert.equal(globalKeys.size,17);
console.log('UX_GRADE_OBSERVATIONS_AUDIT=PASS; researched=17; cohorts=3');
