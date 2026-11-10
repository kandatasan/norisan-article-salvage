const fs=require('fs'),path=require('path'),assert=require('assert');
const root=path.resolve(__dirname,'..');
const data=JSON.parse(fs.readFileSync(path.join(root,'data/reference_price_bands.json'),'utf8'));
const research=JSON.parse(fs.readFileSync(path.join(root,'research/grade_specific_observations_20261111.json'),'utf8'));
const q=(a,p)=>{const x=(a.length-1)*p,lo=Math.floor(x),hi=Math.ceil(x);return a[lo]+(a[hi]-a[lo])*(x-lo)};
const keys=new Set();
for(const g of research.groups){
 assert(g.records.length>=5);
 const prices=g.records.map(r=>{
   assert(r.total_price_man>0&&r.mileage_km>0&&r.dealer&&r.source_page.startsWith('https://'));
   const key=[g.model,g.grade,g.year,g.market_segment,r.dealer,r.mileage_km].join('|');
   assert(!keys.has(key),'Duplicate same grade/year/seller/mileage');
   keys.add(key);
   return r.total_price_man;
 }).sort((a,b)=>a-b);
 const matching=data.cohorts.filter(b=>b.model===g.model&&b.grade===g.grade&&b.year===g.year&&b.market_segment===g.market_segment);
 assert.equal(matching.length,1);
 if(g.incorporation==='new_grade_specific_candidate'){
  assert.equal(matching[0].sample_size,g.records.length);
  assert.equal(matching[0].lower_man,Math.floor(q(prices,.25)/10)*10);
  assert.equal(matching[0].median_man,q(prices,.5));
  assert.equal(matching[0].upper_man,Math.ceil(q(prices,.75)/10)*10);
  assert.equal(matching[0].research_source,'research/grade_specific_observations_20261111.json');
 }else{
  assert.equal(g.year,2020);
  assert.equal(matching[0].sample_size,7,'Preserve 2020 grade cohort from prior PR');
 }
}
assert.equal(keys.size,17);
assert(data.cohorts.every(b=>b.grade!=='all'));
console.log('UX_GRADE_RESEARCH_AUDIT=PASS: 17 observations; 2 new cohorts; 2020 retained');
