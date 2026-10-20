"use strict";
// Synthetic DOM navigation/regression smoke. Does NOT substitute for Safari QA.
const fs=require("fs"),path=require("path"),vm=require("vm"),assert=require("assert");
const root=process.argv[2];if(!root)throw Error("Missing extracted research ZIP");
const read=n=>JSON.parse(fs.readFileSync(path.join(root,n),"utf8"));
const atlas=read("atlas.json"),meta=read("river_fish_label_counts_v25.json");
const byId={},fetches=[];
class El{
 constructor(tag){this.tag=tag;this._text="";this.children=[];this.listeners={};this.value="";this.checked=false;this.hidden=false;this.disabled=false;this.dataset={};}
 get firstChild(){return this.children[0]||null}
 appendChild(e){this.children.push(e);return e}
 removeChild(e){const i=this.children.indexOf(e);if(i<0)throw Error("DOM child absent");this.children.splice(i,1);return e}
 set textContent(t){this._text=String(t);this.children=[]}
 get textContent(){return this._text+this.children.map(e=>e.textContent).join("")}
 addEventListener(t,cb){(this.listeners[t]??=[]).push(cb)}
 prepend(e){this.children.unshift(e)}
}
for(const id of ["pref","water","river","details","heading","attribution","fishsearch","fishlist","count","more",
"reverseFishV24","reverseStatusV24","reverseResultsV24","reverseMoreV24",
"riverSearchV25","riverFishOnlyV25","riverSearchStatusV25","riverSearchResultsV25","riverSearchMoreV25"]){byId[id]=new El(id)}
const document={getElementById(id){assert(byId[id],id);return byId[id]},createElement(tag){return new El(tag)},querySelector(s){assert.equal(s,"main");return new El("main")}};
const fetch=async p=>{fetches.push(p);const full=path.join(root,p);return{ok:fs.existsSync(full),status:fs.existsSync(full)?200:404,json:async()=>read(p)}};
const html=fs.readFileSync(path.join(root,"index.html"),"utf8");
const context=vm.createContext({document,fetch,console});
vm.runInContext(html.split("<script>")[1].split("</script>")[0],context);
const run=c=>vm.runInContext(c,context),wait=()=>new Promise(done=>setTimeout(done,0));
const walk=e=>[e,...e.children.flatMap(walk)];
(async()=>{
 await wait();await wait();
 assert.equal(atlas.entries.length,1568);
 assert.equal(meta.entries.length,511);
 assert(!fetches.includes("river_fish_label_counts_v25.json"),"Source metadata should be loaded on search only");
 const fishItems=meta.entries.filter(x=>x.fish_name_in_source_records);
 assert(fishItems.length>0);
 const emptyItems=meta.entries.filter(x=>!x.fish_name_in_source_records);
 assert(fishItems.length+emptyItems.length===511);
 byId.riverSearchV25.value="太田川";
 await run("searchRiverV25()");
 assert(fetches.includes("river_fish_label_counts_v25.json"));
 assert(byId.riverSearchStatusV25.textContent.includes("該当する資料掲載名"));
 assert(byId.riverSearchResultsV25.textContent.includes("太田川"));
 const hits=run("riverSearchHitsV25");
 assert(hits.length>0 && hits[0].entry.name==="太田川");
 const buttons=walk(byId.riverSearchResultsV25).filter(x=>x.tag==="button" && x.listeners.click);
 assert(buttons.length>0);
 const toId=hits[0].entry.id;
 buttons[0].listeners.click[0]();
 await wait();await wait();
 assert.equal(byId.river.value,toId);
 assert(!byId.fishlist.textContent.includes("読み込み中に検証エラー"));
 byId.riverFishOnlyV25.checked=true;
 await run("searchRiverV25()");
 assert(run("riverSearchHitsV25.every(x=>x.fish_meta.historical_fish_literal_name_count>0||x.fish_meta.environmental_DNA_fish_literal_name_rows>0)"));
 const all=meta.entries.reduce((a,v)=>a+v.historical_fish_literal_name_count,0);
 const dna=meta.entries.reduce((a,v)=>a+v.environmental_DNA_fish_literal_name_rows,0);
 assert(all>0&&dna>0);
 byId.riverSearchV25.value="この名前の川は存在しないABCXX";
 await run("searchRiverV25()");
 assert(byId.riverSearchStatusV25.textContent.includes("該当資料なし"));
 console.log(JSON.stringify({status:"RIVER_NAME_V25_DOM_SMOKE_OK",query:"太田川",
   original_source_groups:511,official_source_name_groups:1057,
   original_groups_with_any_fish_labels:fishItems.length,original_without_fish_labels:emptyItems.length,
   full_historical_fish_source_labels:all,DNA_fish_name_rows:dna,
   clicked_source_id:toId,fish_only_filter_tested:true}));
})().catch(e=>{console.error(e);process.exitCode=1});
