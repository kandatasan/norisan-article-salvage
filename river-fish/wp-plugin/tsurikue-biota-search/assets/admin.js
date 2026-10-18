/* The dataset import only starts on explicit administrator click. */
(function(){
  "use strict";
  const admin=window.TsurikueBiotaAdmin||{};
  const root=document.getElementById("tbs-admin");
  if(!root)return;
  const status=root.querySelector("#tbs-status");
  const progress=root.querySelector("#tbs-progress");
  const error=root.querySelector("#tbs-error");
  const start=root.querySelector("#tbs-start");
  const resume=root.querySelector("#tbs-resume");
  const rollback=root.querySelector("#tbs-rollback");
  let busy=false;
  function paint(s){
    status.textContent=s.message||"";
    progress.textContent=s.importing?(s.imported.toLocaleString("ja-JP")+" / "+
      s.expected.toLocaleString("ja-JP")+"件"):"";
    rollback.disabled=busy||!s.rollback_available||s.importing;
  }
  async function call(action){
    const params=new URLSearchParams({action,nonce:admin.nonce||""});
    const response=await fetch(admin.ajax,{
      method:"POST",credentials:"same-origin",
      headers:{"Content-Type":"application/x-www-form-urlencoded;charset=UTF-8"},
      body:params.toString()
    });
    const data=await response.json();
    if(!response.ok||!data.success)throw Error(data?.data?.message||"データ取込操作に失敗しました。");
    return data.data;
  }
  async function run(startFresh){
    if(busy)return;
    busy=true;error.textContent="";
    start.disabled=true;resume.disabled=true;rollback.disabled=true;
    try{
      let s=startFresh?await call("tbs_import_start"):await call("tbs_import_status");
      if(!startFresh&&!s.importing)throw Error("再開できる取込がありません。");
      paint(s);
      while(s.importing){
        s=await call("tbs_import_step");
        paint(s);
      }
    }catch(e){error.textContent=e.message||"取込が中断されました。再開できます。";}
    finally{
      busy=false;start.disabled=false;resume.disabled=false;
      try{paint(await call("tbs_import_status"));}catch(_e){}
    }
  }
  start.addEventListener("click",()=>{
    if(window.confirm("バックアップとDB空き容量を確認しましたか？旧版を残して新データの取込を開始します。")){
      run(true);
    }
  });
  resume.addEventListener("click",()=>run(false));
  rollback.addEventListener("click",async()=>{
    if(busy||!window.confirm("検証済みの直前版へ戻しますか？"))return;
    error.textContent="";
    try{paint(await call("tbs_import_rollback"));}
    catch(e){error.textContent=e.message||"旧版へ戻せませんでした。";}
  });
  call("tbs_import_status").then(paint).catch(e=>{error.textContent=e.message;});
})();
