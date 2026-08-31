const { chromium } = require('playwright');
(async()=>{
  const browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:1});
  await page.goto('https://tsurikue.com/',{waitUntil:'networkidle',timeout:90000});
  const result=await page.evaluate(()=>{
    const sels=['html','body','#content','.l-content','.l-container','.l-mainContent','.l-mainContent__inner','.post_content','.tq4','.tq4 .tq4-choose','.tq4 .tq4-concept'];
    const out={viewport:{w:innerWidth,h:innerHeight},bodyClass:document.body.className};
    for(const s of sels){
      const el=document.querySelector(s);
      if(!el){out[s]=null;continue;}
      const r=el.getBoundingClientRect(); const cs=getComputedStyle(el);
      out[s]={left:r.left,right:r.right,width:r.width,maxWidth:cs.maxWidth,paddingLeft:cs.paddingLeft,paddingRight:cs.paddingRight,marginLeft:cs.marginLeft,marginRight:cs.marginRight,position:cs.position,display:cs.display};
    }
    return out;
  });
  console.log('TOP_PC_WIDTH='+JSON.stringify(result));
  await page.screenshot({path:'top-pc-diagnostic.png',fullPage:true});
  await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
