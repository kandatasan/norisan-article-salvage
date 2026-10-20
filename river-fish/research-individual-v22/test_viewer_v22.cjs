// Research-only DOM-mock click smoke test for real v22 offline viewer.
// Not a substitute for Safari/real-device QA.
"use strict";
const fs=require("fs"),vm=require("vm"),path=require("path"),assert=require("assert");
const root=process.argv[2];
if(!root)throw Error("Need extracted v22 preview directory");
const atlas=JSON.parse(fs.readFileSync(path.join(root,"atlas.json"),"utf8"));
const elById={};
class Element {
  constructor(tag) {this.tag=tag;this.children=[];this.listeners={};this.value="";this.disabled=false;this.hidden=false;this._text="";this.className="";this.dataset={};}
  get firstChild(){return this.children[0]||null}
  appendChild(x){this.children.push(x);x.parent=this;return x}
  removeChild(x){const i=this.children.indexOf(x);if(i<0)throw Error("Missing child");this.children.splice(i,1);return x}
  set textContent(v){this._text=String(v);this.children=[]}
  get textContent(){return this._text+this.children.map(x=>x.textContent).join("")}
  addEventListener(type,fn){(this.listeners[type]??=[]).push(fn)}
  prepend(x){this.children.unshift(x)}
}
for(const id of ["pref","water","river","details","heading","attribution","fishsearch","fishlist","count","more"]){elById[id]=new Element(id==="pref"||id==="water"||id==="river"?"select":"div")}
const document={getElementById(id){assert(elById[id],id);return elById[id]},createElement(tag){return new Element(tag)},querySelector(sel){assert.equal(sel,"main");return new Element("main")}};
const calls=[];
async function fetchData(name){calls.push(name); const file=path.resolve(root,name);if(!file.startsWith(path.resolve(root)+path.sep))throw Error("Path outside preview");return {ok:fs.existsSync(file),status:fs.existsSync(file)?200:404,json:async()=>JSON.parse(fs.readFileSync(file,"utf8"))}}
const context=vm.createContext({document,fetch:fetchData,console,Map,Set,Promise,Error,Array,Number,Boolean,Math,String});
const html=fs.readFileSync(path.join(root,"index.html"),"utf8");
const match=html.match(/<script>([\s\S]*?)<\/script>/);
assert(match && !html.includes("eval("));
vm.runInContext(match[1],context);
const invoke=(code)=>vm.runInContext(code,context);
const delay=()=>new Promise(ok=>setTimeout(ok,0));
function selectEntry(entry,pref){
  elById.pref.value=pref;invoke("choosePref()");
  assert.equal(elById.water.disabled,false,"watershed dropdown must be enabled");
  elById.water.value=entry.water;invoke("chooseWater()");
  const available=elById.river.children.some(x=>x.value===entry.id);
  assert(available,"river dropdown must contain selected entry");
  elById.river.value=entry.id;
  return invoke("chooseRiver()");
}
function walk(el){return [el,...el.children.flatMap(walk)]}
(async()=>{
 await delay();await delay();
 assert.equal(elById.pref.disabled,false);
 assert.equal(atlas.entries.length,1568);
 const official=atlas.entries.find(x=>x.source_only_name_evidence_v21&&x.source_label_type==="river");
 assert(official,"need source-only river fixture");
 await selectEntry(official,official.source_prefecture);
 assert(elById.fishlist.textContent.includes("未接続"),"name-only entry needs explicit no evidence notice");
 assert(!elById.fishlist.textContent.includes("★".repeat(5)),"name-only must not invent fish stars");
 assert(elById.river.children.some(x=>x.textContent.includes("川名資料・魚未接続")));
 const old=atlas.entries.slice(0,511).find(x=>x.old&&x.old.fish);
 assert(old,"need historical fish record fixture");
 const oldLink=atlas.links.find(x=>x.river_id===old.id);
 assert(oldLink);
 await selectEntry(old,oldLink.prefecture);
 await delay();
 assert(elById.fishlist.textContent.includes("★")||elById.fishlist.textContent.includes("魚類の公開調査記録を収録していません")||elById.fishlist.textContent.includes("掲載名")||elById.fishlist.textContent.includes("調査記録"),"old fish path must render or explain absence");
 assert(!elById.fishlist.textContent.includes("読み込み中に検証エラー"),"old fish path errors");
 const linked=atlas.entries.find(e=>e.same_name_survey_reference_v22?.candidate_ids?.length);
 if(linked){
    await selectEntry(linked,linked.source_prefecture);
    const btns=walk(elById.fishlist).filter(x=>x.tag==="button");
    assert(btns.length,"same-name entry needs explicit navigation");
    assert(elById.fishlist.textContent.includes("同じ河川・区間とはまだ確認できていません"));
    const target=linked.same_name_survey_reference_v22.candidate_ids[0];
    btns[0].listeners.click[0]();
    await delay();await delay();
    assert.equal(elById.river.value,target,"same-name link must navigate to original survey record");
 }
 assert(calls.includes("atlas.json")&&calls.includes("fish_master.json"));
 console.log(JSON.stringify({status:"DOM_MOCK_CLICK_SMOKE_OK",official_name:official.name,old_name:old.name,
                          source_names:atlas.entries.length-511,reference_tested:Boolean(linked),
                          json_requests:calls.length}));
})().catch(e=>{console.error(e);process.exitCode=1});
