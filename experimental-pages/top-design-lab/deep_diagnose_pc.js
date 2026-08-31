const { chromium } = require('playwright');

function metric(el){
  if(!el) return null;
  const r=el.getBoundingClientRect();
  const cs=getComputedStyle(el);
  return {
    tag:el.tagName,
    cls:el.className,
    left:r.left,right:r.right,width:r.width,height:r.height,
    maxWidth:cs.maxWidth,widthCss:cs.width,
    marginLeft:cs.marginLeft,marginRight:cs.marginRight,
    paddingLeft:cs.paddingLeft,paddingRight:cs.paddingRight,
    display:cs.display,position:cs.position,
    gridTemplateColumns:cs.gridTemplateColumns,
    justifyContent:cs.justifyContent,alignItems:cs.alignItems,
    boxSizing:cs.boxSizing,
    contentSize:cs.getPropertyValue('--wp--style--global--content-size'),
    wideSize:cs.getPropertyValue('--wp--style--global--wide-size')
  };
}

(async()=>{
  const browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:1});
  await page.goto('https://tsurikue.com/?deepdiag=1',{waitUntil:'networkidle',timeout:90000});
  await page.waitForSelector('.tq4',{timeout:30000});
  const out=await page.evaluate(()=>{
    function m(el){
      if(!el)return null; const r=el.getBoundingClientRect(); const cs=getComputedStyle(el);
      return {tag:el.tagName,cls:String(el.className),left:r.left,right:r.right,width:r.width,height:r.height,maxWidth:cs.maxWidth,widthCss:cs.width,marginLeft:cs.marginLeft,marginRight:cs.marginRight,paddingLeft:cs.paddingLeft,paddingRight:cs.paddingRight,display:cs.display,position:cs.position,gridTemplateColumns:cs.gridTemplateColumns,justifyContent:cs.justifyContent,alignItems:cs.alignItems,boxSizing:cs.boxSizing,contentSize:cs.getPropertyValue('--wp--style--global--content-size'),wideSize:cs.getPropertyValue('--wp--style--global--wide-size')};
    }
    const sels=['#content','.l-content','.l-mainContent','.l-mainContent__inner','.post_content','.tq4','.tq4>.wp-block-group__inner-container','.tq4-cats','.tq4-cats>.wp-block-group__inner-container','.tq4-cats .tq4-head','.tq4-cats .tq4-cat-grid','.tq4-concept','.tq4-concept>.wp-block-group__inner-container','.tq4-concept .tq4-concept-grid','.tq4-start','.tq4-start>.wp-block-group__inner-container','.tq4-start .tq4-head','.tq4-start .tq4-pick-grid'];
    const metrics={}; for(const s of sels)metrics[s]=m(document.querySelector(s));
    const root=document.querySelector('.tq4');
    const tree=[];
    function walk(el,depth){if(!el||depth>4)return;tree.push({depth,metric:m(el)});for(const ch of el.children)walk(ch,depth+1)}
    walk(root,0);
    return {viewport:innerWidth,scrollWidth:document.documentElement.scrollWidth,bodyClass:document.body.className,metrics,tree};
  });
  console.log('DEEP_PC='+JSON.stringify(out));
  await page.screenshot({path:'deep-top-pc.png',fullPage:true});
  await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
