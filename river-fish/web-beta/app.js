/* Nationwide river beta. All data remain source-scoped; never join by name. */
(function () {
  "use strict";
  const data=window.TSURIRIVER_BETA_DATA;
  const core=window.RiverBetaCore;
  const $=id=>document.getElementById(id);
  const PAGE=25;
  let mode="codes", offset=0;

  const note={
    codes:"国交省の河川コード掲載行です。所在地の都道府県・直接合流先・この川に生息する魚は確認できません。",
    local:"県・自治体の公式資料に掲載された名称です。水系・計画圏域を個別の川とは扱いません。同名でも出典が違えば別の掲載行です。",
    fish:"国交省による地域×水系×年度の魚類名称記録です。支流・釣り場・県単位の生息魚へ割り当てたものではありません。"
  };
  const kindLabels={river:"河川名（資料掲載）",watershed:"水系名（資料掲載）",planning_region:"整備計画圏域"};
  function el(tag,klass,value) {
    const e=document.createElement(tag);
    if (klass)e.className=klass;
    if (value!==undefined)e.textContent=String(value);
    return e;
  }
  function metaLine(parts) {
    const e=el("div","meta");
    for (const [label,value] of parts) {
      if (!value) continue;
      const span=el("span");
      span.append(el("strong","",label+": "),document.createTextNode(String(value)));
      e.append(span);
    }
    return e;
  }
  function badge(value,extra="") {return el("span","type "+extra,value);}
  function officialLink(parent,url,label) {
    if (!core.isOfficialSource(url))return;
    const a=el("a","",label);
    a.href=url;a.target="_blank";a.rel="noopener noreferrer";
    parent.append(a);
  }
  function itemWrap(title,type,typeClass) {
    const article=el("article","result-item");
    article.setAttribute("role","listitem");
    const row=el("div","item-top");
    row.append(el("h3","",title),badge(type,typeClass));
    article.append(row);
    return article;
  }
  function addSource(article,url,desc) {
    const row=el("div","result-source");
    row.append(el("span","",desc+"："));
    officialLink(row,url,"原資料を開く ↗");
    article.append(row);
  }
  function riverResult(row) {
    const [code,name,watershed,watershedCode]=row;
    const article=itemWrap(name,"河川コード一覧");
    article.append(metaLine([
      ["10桁コード",code],["水系",watershed||"未照合"],["水系コード",watershedCode]
    ]));
    article.append(el("div","note-flag","所在地県・合流先・生息魚は、このコード表では未確認"));
    addSource(article,data.meta.officialRiverSource,"国交省・河川コード一覧");
    return article;
  }
  function localResult(row) {
    const [pref,name,kind,watershed,area,url,evidenceId,scope,date]=row;
    const article=itemWrap(name,kindLabels[kind]||"資料掲載名","local");
    article.append(metaLine([
      ["資料の都道府県",pref],["水系名（出典に明記）",watershed],
      ["資料中の地域・市町",area],["資料の時点",date]
    ]));
    article.append(el("div","note-flag","出典掲載の証拠のみ。正式な全国河川コードとの同一性・生息魚は未確認。"));
    const scopeText=el("div","meta");
    scopeText.append(el("span","",scope),el("span","code","資料行 "+evidenceId));
    article.append(scopeText);
    addSource(article,url,"出典");
    return article;
  }
  function fishResult(row) {
    const [region,watershed,year,name,url]=row;
    const article=itemWrap(name,"水系単位の魚類記録","fish");
    article.append(metaLine([
      ["調査地域",data.regionLabels[region]||region],["水系",watershed],
      ["調査年度",year]
    ]));
    article.append(el("div","note-flag","この魚が水系内の特定の川にいる、あるいは現在もいるという意味ではありません。"));
    addSource(article,url,"国交省・河川水辺の国勢調査");
    return article;
  }
  function selected() {
    if (mode==="codes")return core.searchCodes(data,$("codeQuery").value,PAGE,offset);
    if (mode==="local")return core.searchLocal(
      data,$("localQuery").value,$("localPrefecture").value,$("localKind").value,PAGE,offset);
    return core.searchFish(data,$("fishQuery").value,$("fishWatershed").value,$("fishRegion").value,PAGE,offset);
  }
  function isBlank() {
    if (mode==="codes")return !$("codeQuery").value.trim();
    if (mode==="local")return !($("localQuery").value.trim()||$("localPrefecture").value||$("localKind").value);
    return !($("fishQuery").value.trim()||$("fishWatershed").value.trim()||$("fishRegion").value);
  }
  function render() {
    const results=selected();
    const list=$("resultList");
    list.replaceChildren();
    $("scopeNote").textContent=note[mode];
    const empty=isBlank();
    const count=results.total;
    $("resultCount").textContent=empty?"":"（"+count.toLocaleString("ja-JP")+"件）";
    if (empty) {
      const message=el("div","empty");
      message.append(el("strong","","検索条件を入力してみよう"),document.createTextNode(
        mode==="codes"?"「諸木川」「太田川」「8707090023」などで探せます。":
        mode==="local"?"都道府県を選ぶだけでも、資料に載った川や水系が見られます。":
        "「アユ」や「筑後川」などで、水系単位の調査記録を探せます。"));
      list.append(message);
    } else if(!count) {
      const message=el("div","empty");
      message.append(el("strong","","一致する資料掲載行は見つかりませんでした"),document.createTextNode(
        "未収録＝川や魚が存在しない、という意味ではありません。表記を変えて検索してみてください。"));
      list.append(message);
    } else {
      for(const row of results.rows) {
        list.append(mode==="codes"?riverResult(row):mode==="local"?localResult(row):fishResult(row));
      }
    }
    $("pager").hidden=count<=PAGE;
    $("prevPage").disabled=offset<=0;
    $("nextPage").disabled=offset+PAGE>=count;
    $("pageInfo").textContent=count?String(Math.min(offset+1,count))+"〜"+String(Math.min(offset+PAGE,count))+" / "+count.toLocaleString("ja-JP")+"件":"";
  }
  function activate(next,focus) {
    if (!["codes","local","fish"].includes(next))return;
    mode=next;offset=0;
    document.querySelectorAll("[role=tab]").forEach(tab=>{
      const on=tab.dataset.tab===mode;
      tab.classList.toggle("active",on);
      tab.setAttribute("aria-selected",String(on));
      tab.tabIndex=on?0:-1;
      if (on && focus)tab.focus();
    });
    for(const key of ["codes","local","fish"])$("panel-"+key).hidden=key!==mode;
    render();
  }
  function newSearch() {offset=0;render();}
  function init() {
    if (!data||!core||data.meta.rivers!==35449||data.meta.fishCensus!==18814||
        data.meta.sourceMentions!==1449||data.meta.prefectures!==47) {
      $("scopeNote").textContent="データを読み込めませんでした。配布ZIPをすべて展開してからindex.htmlを開いてください。";
      return;
    }
    $("statRivers").textContent=data.meta.rivers.toLocaleString("ja-JP");
    $("statSources").textContent=data.meta.sourceMentions.toLocaleString("ja-JP");
    $("statFish").textContent=data.meta.fishCensus.toLocaleString("ja-JP");
    const prefs=$("localPrefecture");
    data.prefectures.forEach(p=>{const o=el("option","",p);o.value=p;prefs.append(o);});
    for(const [id,label] of Object.entries(data.regionLabels)){
      const o=el("option","",label);o.value=id;$("fishRegion").append(o);
    }
    document.querySelectorAll("[role=tab]").forEach(tab=>{
      tab.addEventListener("click",()=>activate(tab.dataset.tab,true));
      tab.addEventListener("keydown",e=>{
        if (!["ArrowLeft","ArrowRight","Home","End"].includes(e.key))return;
        const all=["codes","local","fish"];
        const ix=all.indexOf(mode);
        const next=e.key==="Home"?0:e.key==="End"?2:
          (ix+(e.key==="ArrowRight"?1:2))%3;
        e.preventDefault();activate(all[next],true);
      });
    });
    for(const key of ["codes","local","fish"]){
      $("form-"+key).addEventListener("submit",e=>{e.preventDefault();newSearch();});
    }
    for(const id of ["codeQuery","localQuery","fishQuery","fishWatershed"]){
      $(id).addEventListener("input",debounce(newSearch,230));
    }
    for(const id of ["localPrefecture","localKind","fishRegion"]){
      $(id).addEventListener("change",newSearch);
    }
    $("clearSearch").addEventListener("click",()=>{
      if(mode==="codes")$("codeQuery").value="";
      else if(mode==="local"){$("localPrefecture").value="";$("localQuery").value="";$("localKind").value="";}
      else {$("fishQuery").value="";$("fishWatershed").value="";$("fishRegion").value="";}
      newSearch();
    });
    $("prevPage").addEventListener("click",()=>{offset=Math.max(0,offset-PAGE);render();$("results-title").scrollIntoView({block:"start"});});
    $("nextPage").addEventListener("click",()=>{offset+=PAGE;render();$("results-title").scrollIntoView({block:"start"});});
    activate("codes",false);
  }
  function debounce(fn,ms) {
    let timer;
    return function () {window.clearTimeout(timer);timer=window.setTimeout(fn,ms);};
  }
  document.addEventListener("DOMContentLoaded",init,{once:true});
})();
