(function(){
  "use strict";
  const conf=window.TsurikueRiverImport||{};
  function init(){
    const root=document.getElementById("tsr-admin-import");
    if(!root)return;
    const msg=document.getElementById("tsr-import-status");
    const count=document.getElementById("tsr-import-count");
    const err=document.getElementById("tsr-import-error");
    const start=document.getElementById("tsr-import-start");
    const resume=document.getElementById("tsr-import-resume");
    let running=false;

    function display(d){
      msg.textContent=d.message||"";
      const done=Object.values(d.imported||{}).reduce((a,b)=>a+Number(b||0),0);
      const total=Object.values(d.expected||{}).reduce((a,b)=>a+Number(b||0),0);
      count.textContent="取込 "+done.toLocaleString("ja-JP")+
        " / "+total.toLocaleString("ja-JP")+" 行"+
        (d.ready?"（検索可能な旧版も維持）":"");
    }
    async function ajax(action){
      const params=new URLSearchParams({action,nonce:conf.nonce});
      const response=await fetch(conf.ajaxUrl,{
        method:"POST",credentials:"same-origin",
        headers:{"Content-Type":"application/x-www-form-urlencoded;charset=UTF-8"},
        body:params.toString()
      });
      let body;
      try {body=await response.json();} catch (_){throw new Error("サーバーからJSONの応答がありません。");}
      if(!response.ok||!body.success){
        throw new Error(body&&body.data&&body.data.message?body.data.message:"処理に失敗しました（HTTP "+response.status+"）。");
      }
      return body.data;
    }
    function busy(value){
      running=value;start.disabled=value;resume.disabled=value;
    }
    async function loop(shouldStart){
      if(running)return;
      busy(true);err.textContent="";
      try{
        let state=shouldStart?await ajax("tsr_import_start"):await ajax("tsr_import_status");
        if(!shouldStart&&!state.importing){
          display(state);throw new Error("再開できるデータ取込がありません。最初から開始してください。");
        }
        display(state);
        // Strict sequential requests: avoid duplicate batches on shared hosting.
        while(state.importing){
          state=await ajax("tsr_import_step");
          display(state);
        }
        msg.textContent="データ検証と切替が完了しました。ショートコードで確認できます。";
      } catch(e){
        err.textContent=e.message||"取込が中断しました。";
      } finally {busy(false);}
    }
    start.addEventListener("click",()=>loop(true));
    resume.addEventListener("click",()=>loop(false));
    ajax("tsr_import_status").then(display).catch(e=>{err.textContent=e.message;});
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init,{once:true});
  else init();
})();