"use strict";
// Research archive UI smoke in Node DOM mock: not a substitute for iPhone Safari.
const fs=require("fs"),vm=require("vm"),path=require("path"),assert=require("assert");
const root=process.argv[2];if(!root)throw Error("Need extracted research ZIP directory");
const dataFile=name=>JSON.parse(fs.readFileSync(path.join(root,name),"utf8"));
const atlas=dataFile("atlas.json"),index=dataFile("fish_to_river_reverse_v24.json");
const byId={},fetches=[];
class El{
 constructor(tag){this.tag=tag;this._text="";this.children=[];this.events={};this.value="";this.hidden=false;this.disabled=false;this.dataset={};}
 get firstChild(){return this.children[0]||null}
 appendChild(e){this.children.push(e);return e}
 removeChild(e){const ix=this.children.indexOf(e);if(ix<0)throw Error("missing DOM child");this.children.splice(ix,1);return e}
 set textContent(v){this._text=String(v);this.children=[]}
 get textContent(){return this._text+this.children.map(c=>c.textContent).join("")}
 addEventListener(type,fn){(this.events[type]??=[]).push(fn)}
 prepend(e){this.children.unshift(e)}
}
for(const id of ["pref","water","river","details","heading","attribution","fishsearch","fishlist","count","more",
"reverseFishV24","reverseStatusV24","reverseResultsV24","reverseMoreV24","riverSearchV25","riverFishOnlyV25","riverSearchStatusV25","riverSearchResultsV25","riverSearchMoreV25"]){byId[id]=new El(id)}
const document={getElementById(id){assert(byId[id],"Unknown DOM id "+id);return byId[id]},
 createElement(tag){return new El(tag)},querySelector(sel){assert(sel==="main");return new El("main")}};
const fetch=async p=>{fetches.push(p);assert(!p.includes("..")&&!p.startsWith("/"));const filepath=path.join(root,p);return{ok:fs.existsSync(filepath),status:fs.existsSync(filepath)?200:404,json:async()=>dataFile(p)}};
const context=vm.createContext({document,fetch,console});
const page=fs.readFileSync(path.join(root,"index.html"),"utf8");
assert(page.includes('id="reverseFishV24"'));
vm.runInContext(page.split("<script>")[1].split("</script>")[0],context);
const run=code=>vm.runInContext(code,context),wait=()=>new Promise(ok=>setTimeout(ok,0));
const walk=e=>[e,...e.children.flatMap(walk)];
(async()=>{
 await wait();await wait();
 assert.equal(byId.pref.disabled,false);
 assert(!fetches.includes("fish_to_river_reverse_v24.json"),"reverse index should load only when requested");
 const ordinary=index.lookups.find(x=>x.recorded_fish_name==="アユ");
 assert(ordinary && ordinary.river_survey_groups.length,"Missing sampled common fish evidence");
 byId.reverseFishV24.value="アユ";
 await run("reverseQueryV24()");
 assert(fetches.includes("fish_to_river_reverse_v24.json"));
 assert(byId.reverseStatusV24.textContent.includes("該当する魚名"));
 assert(byId.reverseResultsV24.textContent.includes("アユ"));
 const b=walk(byId.reverseResultsV24).find(x=>x.tag==="button"&&x.events.click);
 assert(b,"Reverse search must have clickable source river");
 b.events.click[0]();
 await wait();await wait();
 assert.equal(byId.river.value,ordinary.river_survey_groups[0].river_id);
 assert(byId.heading.textContent.includes("水系"));
 assert(!byId.fishlist.textContent.includes("読み込み中に検証エラー"));
 const excluded=dataFile("fish_master.json");
 for(const name of ["キンギョ","カダヤシ属"]){
  const tax=excluded.taxa[name];
  if(tax && tax.classification_status!=="named_fish"){
    assert(!index.lookups.some(x=>x.recorded_fish_name===name),"Held/nonfish must be excluded from reverse");
  }
 }
 const dna=index.lookups.find(x=>x.river_survey_groups.some(p=>p.method_flags.includes("ENVIRONMENTAL_DNA_DETECTED_NOT_CAPTURED")));
 assert(dna,"Need real environmental DNA detection in reverse index");
 byId.reverseFishV24.value=dna.recorded_fish_name;
 await run("reverseQueryV24()");
 assert(byId.reverseResultsV24.textContent.includes(dna.recorded_fish_name));
 assert(byId.reverseResultsV24.textContent.includes("DNA検出"),"eDNA must be labeled as DNA detection");
 byId.reverseFishV24.value="絶対ありえない魚名XYZ";
 await run("reverseQueryV24()");
 assert(byId.reverseStatusV24.textContent.includes("一致する魚名はありません"));
 console.log(JSON.stringify({status:"REVERSE_FISH_V24_DOM_CLICKS_OK",reverse_fish:dna.recorded_fish_name,first_fish:"アユ",matched_ayu:ordinary.river_survey_groups.length,source_navigated:true,method_distinction:true,fetch_count:fetches.length}))
})().catch(e=>{console.error(e);process.exitCode=1});
