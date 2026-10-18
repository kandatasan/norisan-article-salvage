/* Node verification of the *actual generated* offline beta search data. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const base = process.argv[2] || "river-fish/build-preview";
const env = vm.createContext({window:{},URL});
for (const file of ["data.js","search-core.js"]) {
  vm.runInContext(fs.readFileSync(path.join(base,file),"utf8"),env,{filename:file});
}
const d=env.window.TSURIRIVER_BETA_DATA, c=env.window.RiverBetaCore;
assert.equal(d.meta.rivers,35449);
assert.equal(d.meta.sourceMentions,1449);
assert.equal(d.meta.fishCensus,18814);
assert.equal(d.meta.prefectures,47);

const moroki=c.searchCodes(d,"諸木川",25,0);
assert.ok(moroki.total>0);
assert.ok(moroki.rows.some(r=>r[0]==="8707090023"&&r[1]==="諸木川"&&r[2]==="太田川"));
assert.ok(moroki.rows.every(r=>r.length===4)); // no derived prefecture/individual fish

const byCode=c.searchCodes(d,"8707090023",25,0);
assert.equal(byCode.total,1);
assert.equal(byCode.rows[0][1],"諸木川");

const tokyo=c.searchLocal(d,"神田川","東京都","river",25,0);
assert.ok(tokyo.total>0);
assert.ok(tokyo.rows.every(r=>r[0]==="東京都"&&r[2]==="river"&&r.length===9));
const okinawa=c.searchLocal(d,"国場川","沖縄県","",25,0);
assert.ok(okinawa.total>0);
const gunma=c.searchLocal(d,"","群馬県","planning_region",100,0);
assert.equal(gunma.total,10);
assert.ok(gunma.rows.every(r=>r[2]==="planning_region"));

const fish=c.searchFish(d,"アユ","","kyushu",30,0);
assert.ok(fish.total>0);
assert.ok(fish.rows.every(r=>r[0]==="kyushu"&&r.length===5));
const none=c.searchFish(d,"架空魚類","","hokkaido",25,0);
assert.equal(none.total,0);

const broad=c.searchCodes(d,"川",25,0);
assert.ok(broad.total>25);
const second=c.searchCodes(d,"川",25,25);
assert.equal(second.offset,25);
assert.notEqual(broad.rows[0][0],second.rows[0][0]);

assert.equal(c.isOfficialSource("javascript:alert(1)"),false);
assert.equal(c.isOfficialSource("https://invalid.example.com/data"),false);
assert.equal(c.isOfficialSource("https://nlftp.mlit.go.jp/ksj/gml/codelist/RiverCodeCd.html"),true);
console.log("PASS: 35,449 official code names / 1,449 local mentions / 18,814 watershed fish names, scope-safe search");
