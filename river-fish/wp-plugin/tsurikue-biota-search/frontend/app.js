/* Research source scope: original region×watershed×survey-year literal labels only. */
(function(){
  "use strict";
  const config=window.TsurikueBiotaSettings||{};
  const regionNames={hokkaido:"北海道",tohoku:"東北",kanto:"関東",hokuriku:"北陸",
    chubu:"中部",kinki:"近畿",chugoku:"中国",shikoku:"四国",kyushu:"九州"};
  function el(tag,text,cls){
    const x=document.createElement(tag);
    if(text!==undefined)x.textContent=String(text);
    if(cls)x.className=cls;
    return x;
  }
  function attach(host){
    if(host.shadowRoot)return;
    const template=host.querySelector("template[data-tbs-view]");
    if(!template)return;
    const shadow=host.attachShadow({mode:"open"});
    const style=el("link");
    style.rel="stylesheet";style.href=config.css||"";
    shadow.append(style,template.content.cloneNode(true));
    const form=shadow.querySelector("[data-tbs-form]");
    const status=shadow.querySelector("[data-tbs-status]");
    const records=shadow.querySelector("[data-tbs-results]");
    const paging=shadow.querySelector("[data-tbs-pager]");
    const prev=shadow.querySelector("[data-tbs-prev]");
    const next=shadow.querySelector("[data-tbs-next]");
    const pageInfo=shadow.querySelector("[data-tbs-page]");
    const groupBox=shadow.querySelector("[data-tbs-groups]");
    const pending=shadow.querySelector("[data-tbs-pending]");
    const tabs=[...shadow.querySelectorAll("[data-direction]")];
    let direction="region_explore",page=1,total=0,request=0,catalog=null,exact=false;
    function reset(msg){
      ++request;page=1;total=0;records.replaceChildren();
      paging.hidden=true;status.textContent=msg;
    }
    function switchDirection(to,drill){
      direction=to;
      tabs.forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.direction===to)));
      if(!drill){
        if(to==="region_explore"){
          form.elements.watershed.value="";form.elements.organism.value="";
        } else if(to==="watershed_to_organism"){
          form.elements.organism.value="";
        } else {
          form.elements.watershed.value="";
        }
        exact=false;
      }
      reset("検索条件を選択してください。");
    }
    tabs.forEach(b=>b.addEventListener("click",()=>switchDirection(b.dataset.direction,false)));
    form.elements.watershed.addEventListener("input",()=>{exact=false;});
    function label(id){
      return catalog?.groups?.find(g=>g.id===id)?.label||id;
    }
    function renderGroup(group,enabled){
      const item=el("label",undefined,"tbs-check");
      const checkbox=el("input");
      checkbox.type="checkbox";checkbox.name="group";checkbox.value=group.id;
      checkbox.checked=enabled;checkbox.disabled=!enabled;
      item.append(checkbox,el("span",group.label));
      if(!enabled)item.append(el("small",group.note||"分類の監査待ち"));
      (enabled?groupBox:pending).append(item);
    }
    async function loadCatalog(){
      if(!config.catalog)throw Error("検索の設定がありません。");
      const response=await fetch(config.catalog,{credentials:"same-origin",cache:"no-store"});
      if(!response.ok)throw Error(response.status===503?
        "データは準備中です。管理者による取込完了後に検索できます。":"分類データを読めません。");
      const c=await response.json();
      if(!Array.isArray(c.groups)||!c.groups.length)throw Error("利用できる分類がありません。");
      catalog=c;groupBox.replaceChildren();pending.replaceChildren();
      c.groups.forEach(g=>renderGroup(g,true));
      Object.entries(c.unavailable_groups||{}).forEach(([id,note])=>{
        renderGroup({id,label:id==="aquatic_insects"?"水生昆虫のみ":id,note},false);
      });
      reset("地方・水系・生物名を選んでください。");
    }
    function appendMeta(card,value){card.append(el("div",value,"tbs-meta"));}
    function sourceLink(card,url){
      try{
        const u=new URL(url);
        if(u.protocol!=="https:"||u.hostname!=="www.nilim.go.jp"||
          !u.pathname.startsWith("/lab/fbg/ksnkankyo/"))return;
        const a=el("a","原資料を確認する ↗","tbs-link");
        a.href=u.href;a.target="_blank";a.rel="noopener noreferrer";
        card.append(a);
      }catch(_e){}
    }
    function waterCard(row){
      const card=el("article",undefined,"tbs-card");
      card.append(el("h4",row.watershed_name+"水系"));
      appendMeta(card,(regionNames[row.region_code]||row.region_code)+"の過去の調査記録");
      const chips=el("div",undefined,"tbs-chips");
      Object.entries(row.group_label_counts||{}).forEach(([g,n])=>{
        chips.append(el("span",label(g)+" "+Number(n).toLocaleString("ja-JP")+"掲載名","tbs-chip"));
      });
      card.append(chips);
      appendMeta(card,"調査年の範囲 "+row.first_year+"～"+row.last_year+
        "（延べ掲載記録 "+row.historical_records+"件）");
      const button=el("button","この水系の生物を見る →","tbs-detail");
      button.type="button";
      button.addEventListener("click",()=>{
        form.elements.region.value=row.region_code;
        form.elements.watershed.value=row.watershed_name;
        form.elements.organism.value="";form.elements.year.value="";
        switchDirection("watershed_to_organism",true);
        exact=true;search();
      });
      card.append(button);records.append(card);
    }
    function organismCard(row){
      const card=el("article",undefined,"tbs-card");
      card.append(el("h4",row.recorded_name+" ／ "+row.watershed_name+"水系"));
      appendMeta(card,(regionNames[row.region_code]||row.region_code)+
        "・"+label(row.survey_group)+"・"+row.survey_year_count+"年度で掲載");
      const details=el("details");
      details.append(el("summary","調査年度を確認"));
      details.append(el("p",(row.survey_years||[]).join("年、")+"年","tbs-meta"));
      card.append(details);sourceLink(card,row.source_url);
      if(row.source_count>1)card.append(el("p","代表する出典へのリンクです。","tbs-meta"));
      records.append(card);
    }
    async function search(){
      if(!catalog){reset("データの準備が必要です。");return;}
      const params=new URLSearchParams(new FormData(form));
      // PHP collapses repeated bare query names. Use group[] for multiple selections.
      const groups=params.getAll("group");
      params.delete("group");
      groups.forEach(g=>params.append("group[]",g));
      params.set("direction",direction);
      params.set("watershed_match",exact?"exact":"contains");
      params.set("page",String(page));params.set("per_page","20");
      if(groups.length===0){reset("生物分類を1つ以上選んでください。");return;}
      if(direction==="region_explore"&&!params.get("region")){reset("地方を選んでください。");return;}
      if(direction==="watershed_to_organism"&&!params.get("watershed")?.trim()){reset("水系名を入力してください。");return;}
      if(direction==="organism_to_watershed"&&!params.get("organism")?.trim()){reset("生物名を入力してください。");return;}
      const mine=++request;records.replaceChildren();paging.hidden=true;
      status.textContent="検索中…";
      try{
        const url=new URL(config.search);
        url.search=params.toString();
        const response=await fetch(url.href,{credentials:"same-origin",cache:"no-store"});
        const result=await response.json();
        if(mine!==request)return;
        if(!response.ok)throw Error(result.message||"検索できませんでした。");
        total=Number(result.total||0);
        status.textContent=total.toLocaleString("ja-JP")+"件の"+
          (result.result_type==="watershed_summary"?"水系":"水系別掲載名")+"が見つかりました。";
        (result.results||[]).forEach(r=>result.result_type==="watershed_summary"?waterCard(r):organismCard(r));
        if(!result.results?.length)records.append(el("p","掲載記録がありません（生物がいない意味ではありません）。"));
        paging.hidden=total===0;prev.disabled=page===1;next.disabled=page*20>=total;
        pageInfo.textContent=page+" / "+Math.ceil(total/20)+"ページ";
      }catch(e){
        if(mine===request)status.textContent=e.message||"検索に失敗しました。";
      }
    }
    form.addEventListener("submit",e=>{e.preventDefault();page=1;search();});
    prev.addEventListener("click",()=>{if(page>1){page--;search();}});
    next.addEventListener("click",()=>{if(page*20<total){page++;search();}});
    loadCatalog().catch(e=>{groupBox.replaceChildren();status.textContent=e.message||"データを確認できません。";});
  }
  function init(){document.querySelectorAll("[data-tbs-mount]").forEach(attach);}
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init,{once:true});
  else init();
})();
