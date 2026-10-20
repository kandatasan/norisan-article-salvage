"use strict";
// v24 compatibility copy of watershed lazy reference smoke; not a replacement for Safari/Chromium.
const fs=require("fs"),path=require("path"),vm=require("vm"),assert=require("assert");
const root=process.argv[2];
if(!root)throw Error("Missing extracted research ZIP path");
const read=(f)=>JSON.parse(fs.readFileSync(path.join(root,f),"utf8"));
const atlas=read("atlas.json"),table={};
class El{
 constructor(tag){this.tag=tag;this.children=[];this.events={};this._text="";this.value="";this.hidden=false;this.disabled=false;this.open=false;this.dataset={};}
 get firstChild(){return this.children[0]||null}
 appendChild(el){this.children.push(el);return el}
 removeChild(el){const i=this.children.indexOf(el);if(i<0)throw Error("missing child");this.children.splice(i,1);return el}
 set textContent(v){this._text=String(v);this.children=[]}
 get textContent(){return this._text+this.children.map(c=>c.textContent).join("")}
 addEventListener(t,fn){(this.events[t]??=[]).push(fn)}
 prepend(e){this.children.unshift(e)}
}
for(const id of ["pref","water","river","details","heading","attribution","fishsearch","fishlist","count","more","reverseFishV24","reverseStatusV24","reverseResultsV24","reverseMoreV24"]){table[id]=new El(id)}
const document={getElementById(id){return table[id]},createElement(tag){return new El(tag)},querySelector(sel){assert(sel==="main");return new El("main")}};
const calls=[];
const context=vm.createContext({document,console,fetch:async f=>{calls.push(f);const full=path.join(root,f);return{ok:fs.existsSync(full),status:200,json:async()=>read(f)}}});
const html=fs.readFileSync(path.join(root,"index.html"),"utf8");
vm.runInContext(html.split("<script>")[1].split("</script>")[0],context);
const run=s=>vm.runInContext(s,context);
const walk=e=>[e,...e.children.flatMap(walk)];
(async()=>{
 await new Promise(resolve=>setTimeout(resolve,0));
 const e=atlas.entries.find(x=>x.source_only_name_evidence_v21&&x.watershed_fish_reference_v23);
 assert(e,"need official source-name with Chinese watershed reference");
 table.pref.value=e.source_prefecture;run("choosePref()");
 table.water.value=e.water;run("chooseWater()");
 table.river.value=e.id;await run("chooseRiver()");
 const dl=walk(table.fishlist).find(x=>x.tag==="details"&&x.textContent.includes("同名水系の魚記録を参考"));
 assert(dl,"reference accordion missing");
 assert(!calls.some(x=>x.startsWith("watershed-reference/")),"pack must load lazily");
 dl.open=true;
 await dl.events.toggle[0]();
 const src=e.watershed_fish_reference_v23.pack;
 assert(calls.includes(src),"missing lazy-water reference fetch");
 const pack=read(src);
 assert(pack.geographic_scope==="WHOLE_WATERSHED_YEAR_NAME_RECORD_NOT_SPECIFIC_RIVER");
 assert(pack.source_region==="中国地方");
 assert(pack.name_groups.length>0);
 assert(dl.textContent.includes("個別河川の記録ではありません"));
 const cards=walk(dl).filter(x=>x.tag==="article"&&x.className==="fish");
 // More exactly 30, unless the source has <30 distinct fish name groups.
 assert(cards.length===Math.min(30,pack.name_groups.length));
 assert(!dl.textContent.includes("読み込みに失敗"));
 console.log(JSON.stringify({status:"WATERSHED_REFERENCE_LAZY_CLICK_OK",water:e.water,pref:e.source_prefecture,
   pack_groups:pack.name_groups.length,first_page_cards:cards.length,loaded_lazily:true}));
})().catch(e=>{console.error(e);process.exitCode=1});
