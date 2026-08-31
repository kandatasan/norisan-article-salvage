const { chromium } = require('playwright');

(async()=>{
  const browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1648,height:920},deviceScaleFactor:1});
  await page.goto('https://tsurikue.com/?deepdiag=h2',{waitUntil:'networkidle',timeout:90000});
  await page.waitForSelector('.tq4',{timeout:30000});
  const out=await page.evaluate(()=>{
    function m(el){
      if(!el)return null;
      const r=el.getBoundingClientRect(),cs=getComputedStyle(el);
      return {
        tag:el.tagName,cls:String(el.className),text:(el.textContent||'').trim().slice(0,80),
        left:r.left,right:r.right,width:r.width,height:r.height,
        display:cs.display,maxWidth:cs.maxWidth,widthCss:cs.width,
        margin:cs.margin,padding:cs.padding,
        paddingTop:cs.paddingTop,paddingRight:cs.paddingRight,paddingBottom:cs.paddingBottom,paddingLeft:cs.paddingLeft,
        background:cs.background,backgroundColor:cs.backgroundColor,color:cs.color,
        border:cs.border,borderTop:cs.borderTop,borderRight:cs.borderRight,borderBottom:cs.borderBottom,borderLeft:cs.borderLeft,
        boxShadow:cs.boxShadow,fontSize:cs.fontSize,lineHeight:cs.lineHeight
      };
    }
    const sels=['.tq4-cats>.wp-block-group__inner-container','.tq4-cats .tq4-head','.tq4-cats .tq4-head-left','.tq4-cats .tq4-head h2','.tq4-cats .tq4-head-note','.tq4-concept h2','.tq4-start .tq4-head h2','.tq4-about h2','.tq4-final h2'];
    const metrics={};for(const s of sels)metrics[s]=m(document.querySelector(s));
    const h2s=[...document.querySelectorAll('.tq4 h2')].map(m);
    return {viewport:innerWidth,metrics,h2s};
  });
  console.log('H2_DIAG='+JSON.stringify(out));
  await page.screenshot({path:'deep-top-pc.png',fullPage:true});
  await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
