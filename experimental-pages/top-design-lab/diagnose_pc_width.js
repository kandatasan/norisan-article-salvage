const { chromium } = require('playwright');
(async()=>{
  const browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:1});
  await page.goto('https://tsurikue.com/',{waitUntil:'networkidle',timeout:90000});
  const result=await page.evaluate(()=>{
    const metric=el=>{if(!el)return null;const r=el.getBoundingClientRect(),cs=getComputedStyle(el);return{tag:el.tagName,cls:el.className,id:el.id,left:r.left,right:r.right,width:r.width,cssWidth:cs.width,maxWidth:cs.maxWidth,paddingLeft:cs.paddingLeft,paddingRight:cs.paddingRight,marginLeft:cs.marginLeft,marginRight:cs.marginRight,position:cs.position,display:cs.display}};
    const concept=document.querySelector('.tq4-concept');
    const cats=document.querySelector('.tq4-cats');
    const chain=[]; let n=concept;
    while(n&&chain.length<8){chain.push({...metric(n),matchesDirect:n.matches('.tq4>.alignfull')});n=n.parentElement;}
    return {
      viewport:{w:innerWidth,h:innerHeight},
      tq4:metric(document.querySelector('.tq4')),
      cats:metric(cats),
      concept:metric(concept),
      conceptDirectMatch:concept?.matches('.tq4>.alignfull')||false,
      rootLayout:getComputedStyle(document.querySelector('.tq4')).getPropertyValue('--wp--style--global--content-size'),
      chain
    };
  });
  console.log('TOP_PC_LAYOUT='+JSON.stringify(result));
  await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
