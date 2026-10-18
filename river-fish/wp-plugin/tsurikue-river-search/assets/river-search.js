/* WordPress plugin front end. Data fetched in bounded pages, never preload 55k records. */
(function () {
  "use strict";
  const conf=window.TsurikueRiverSearchSettings||{};
  const hints={
    codes:"国交省の10桁コード一覧です。所在県や、その川での魚の生息は未確認です。",
    local:"県の資料に出てきた河川名・水系名・計画圏域名です。県内全河川の一覧ではありません。",
    fish:"水系×調査年度の魚名記録です。特定の川で釣れる魚を示すものではありません。"
  };
  const typeLabel={river:"河川名",watershed:"水系名",planning_region:"河川整備計画圏域"};
  const regionNames={
    hokkaido:"北海道",tohoku:"東北",kanto:"関東",hokuriku:"北陸",
    chubu:"中部",kinki:"近畿",chugoku:"中国",shikoku:"四国",kyushu:"九州"
  };

  function el(tag, cls, text) {
    const item=document.createElement(tag);
    if(cls)item.className=cls;
    if(text!==undefined)item.textContent=String(text);
    return item;
  }
  function validOfficialUrl(str) {
    try {
      const u=new URL(str);
      return u.protocol==="https:" && u.hostname.endsWith(".jp");
    } catch(e) {return false;}
  }
  function addInfo(container,label,value) {
    if (!value) return;
    const detail=el("span","tsr-detail");
    detail.append(el("b","",label+"："),document.createTextNode(String(value)));
    container.append(detail);
  }
  function appendSource(card,url) {
    if (!validOfficialUrl(url))return;
    const a=el("a","tsr-source","公式の出典を開く ↗");
    a.href=url;a.target="_blank";a.rel="noopener noreferrer";
    card.append(a);
  }
  function itemCard(mode,r) {
    const card=el("article","tsr-result");
    const head=el("div","tsr-result-head");
    let name="",label="",detail=el("div","tsr-details");
    if(mode==="codes"){
      name=r.river_name;label="国の河川コード一覧";
      addInfo(detail,"河川コード",r.river_code);
      addInfo(detail,"水系",r.watershed_name);
      addInfo(detail,"水系コード",r.watershed_code);
    } else if(mode==="local"){
      name=r.label_name;label=typeLabel[r.label_kind]||"資料掲載名";
      addInfo(detail,"資料の県",r.prefecture);
      addInfo(detail,"明記された水系",r.watershed_name);
      addInfo(detail,"掲載地域",r.source_area);
      addInfo(detail,"掲載時点",r.source_date);
      addInfo(detail,"出典の範囲",r.source_scope);
    } else {
      name=r.fish_name;label="水系単位の魚類記録";
      addInfo(detail,"調査地域",regionNames[r.region_code]||r.region_code);
      addInfo(detail,"水系",r.watershed_name);
      addInfo(detail,"調査年度",r.survey_year);
    }
    head.append(el("h3","",name),el("span","tsr-label",label));
    card.append(head,detail);
    const note=(mode==="codes"?"所在地県・個別の生息魚は、このコード表では未確認。":
      mode==="local"?"資料掲載名のみ。国の10桁コードと同一かは未照合。":
      "この魚が特定の支流に生息するとは断定できません。");
    card.append(el("p","tsr-warning",note));
    appendSource(card,r.source_url);
    return card;
  }
  function setup(root){
    const tabs=Array.from(root.querySelectorAll(".tsr-tabs [data-mode]"));
    const form=root.querySelector(".tsr-form");
    const q=form.querySelector('[name="q"]');
    const p=form.querySelector('[name="prefecture"]');
    const kind=form.querySelector('[name="kind"]');
    const region=form.querySelector('[name="region"]');
    const watershed=form.querySelector('[name="watershed"]');
    const prefWrap=form.querySelector(".tsr-pref-wrap");
    const kindWrap=form.querySelector(".tsr-kind-wrap");
    const regionWrap=form.querySelector(".tsr-region-wrap");
    const watershedWrap=form.querySelector(".tsr-watershed-wrap");
    const queryWrap=form.querySelector(".tsr-query-wrap");
    const note=root.querySelector("[data-scope]");
    const status=root.querySelector("[data-status]");
    const results=root.querySelector("[data-results]");
    const pager=root.querySelector("[data-pager]");
    const previous=root.querySelector("[data-prev]");
    const next=root.querySelector("[data-next]");
    const pageInfo=root.querySelector("[data-page-info]");
    let mode="codes", page=1, requestSeq=0, timer=null, total=0;

    (conf.prefectures||[]).forEach(pref=>{
      const option=el("option","",pref);option.value=pref;p.append(option);
    });
    function hasQuery() {
      if(mode==="codes")return Boolean(q.value.trim());
      if(mode==="local")return Boolean(q.value.trim()||p.value||kind.value);
      return Boolean(q.value.trim()||watershed.value.trim()||region.value);
    }
    function showEmpty(message){
      results.replaceChildren(el("p","tsr-empty",message));
      pager.hidden=true;
    }
    async function search(){
      const token=++requestSeq;
      if(!conf.isReady){
        status.textContent="データ未取込です。管理者が「ツール → 全国河川DB」で取込を完了すると検索できます。";
        showEmpty("");return;
      }
      if(!hasQuery()){
        status.textContent="検索条件を入れてみよう。";
        showEmpty(mode==="codes"?"例：諸木川・太田川・8707090023":
          mode==="local"?"都道府県を選ぶだけでも資料の掲載行を表示します。":
          "例：アユ・筑後川（水系単位での記録）");
        return;
      }
      status.textContent="検索中…";
      const url=new URL(conf.endpoint);
      url.searchParams.set("mode",mode);
      url.searchParams.set("q",q.value.trim());
      url.searchParams.set("page",String(page));
      url.searchParams.set("per_page","20");
      if(mode==="local"){
        url.searchParams.set("prefecture",p.value);
        url.searchParams.set("kind",kind.value);
      } else if(mode==="fish"){
        url.searchParams.set("watershed",watershed.value.trim());
        url.searchParams.set("region",region.value);
      }
      try {
        const response=await fetch(url.toString(),{credentials:"same-origin",headers:{Accept:"application/json"}});
        if(!response.ok)throw new Error("検索API: HTTP "+response.status);
        const data=await response.json();
        if(token!==requestSeq)return;
        total=Number(data.total||0);
        const rows=Array.isArray(data.rows)?data.rows:[];
        status.textContent=total.toLocaleString("ja-JP")+"件の資料掲載行が一致しました。";
        note.textContent=data.notice||hints[mode];
        results.replaceChildren();
        if(!rows.length){
          showEmpty("該当の掲載行は見つかりません。未収録は川・魚がいないという意味ではありません。");
        }else{
          rows.forEach(r=>results.append(itemCard(mode,r)));
        }
        pager.hidden=total<=20;
        previous.disabled=page<=1;
        next.disabled=page*20>=total;
        pageInfo.textContent=String(page)+" / "+String(Math.max(1,Math.ceil(total/20)))+" ページ";
      } catch(e) {
        if(token!==requestSeq)return;
        status.textContent="検索できませんでした。管理者にご確認ください。";
        showEmpty("通信またはデータベースのエラーです。");
      }
    }
    function reset(){page=1;search();}
    function activate(value){
      if(!["codes","local","fish"].includes(value))return;
      mode=value;page=1;
      tabs.forEach(tab=>{
        const active=tab.dataset.mode===mode;
        tab.classList.toggle("tsr-selected",active);
        tab.setAttribute("aria-selected",active?"true":"false");
        tab.tabIndex=active?0:-1;
      });
      prefWrap.hidden=kindWrap.hidden=mode!=="local";
      regionWrap.hidden=watershedWrap.hidden=mode!=="fish";
      q.parentElement.querySelector('input').placeholder=(mode==="codes"?"例：諸木川・8707090023":
        mode==="local"?"例：国場川（県だけの選択も可）":"例：アユ");
      queryWrap.firstChild.textContent=(mode==="codes"?"川名・水系名・10桁コード":
        mode==="local"?"河川名・水系名・地域名":"魚の名前");
      q.value="";p.value="";kind.value="";region.value="";watershed.value="";
      note.textContent=hints[mode];
      reset();
    }
    tabs.forEach(tab=>{
      tab.addEventListener("click",()=>activate(tab.dataset.mode));
      tab.addEventListener("keydown",evt=>{
        if(!["ArrowLeft","ArrowRight","Home","End"].includes(evt.key))return;
        evt.preventDefault();
        const modes=["codes","local","fish"],i=modes.indexOf(mode);
        const idx=evt.key==="Home"?0:evt.key==="End"?2:
          evt.key==="ArrowRight"?(i+1)%3:(i+2)%3;
        activate(modes[idx]);tabs[idx].focus();
      });
    });
    form.addEventListener("submit",evt=>{evt.preventDefault();reset();});
    form.addEventListener("input",()=>{
      window.clearTimeout(timer);timer=window.setTimeout(reset,280);
    });
    form.addEventListener("change",reset);
    previous.addEventListener("click",()=>{page=Math.max(1,page-1);search();});
    next.addEventListener("click",()=>{page+=1;search();});
    activate("codes");
  }
  function init(){document.querySelectorAll("[data-tsr-app]").forEach(setup);}
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init,{once:true});
  else init();
})();
