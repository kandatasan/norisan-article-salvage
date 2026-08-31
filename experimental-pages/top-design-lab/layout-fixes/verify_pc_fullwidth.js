const { chromium } = require('playwright');

async function checkDesktop(browser){
  const page=await browser.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:1});
  await page.goto('https://tsurikue.com/',{waitUntil:'domcontentloaded',timeout:90000});
  await page.waitForSelector('.tq4',{timeout:30000});
  await page.waitForTimeout(1200);
  const data=await page.evaluate(()=>{
    const sels=['.tq4','.tq4-party','.tq4-hero','.tq4-cats','.tq4-concept','.tq4-start','.tq4-about','.tq4-final'];
    const metrics={};
    for(const s of sels){const el=document.querySelector(s);if(!el){metrics[s]=null;continue;}const r=el.getBoundingClientRect();metrics[s]={left:r.left,right:r.right,width:r.width};}
    const inner=document.querySelector('.tq4-cats>.wp-block-group__inner-container');
    const ir=inner?inner.getBoundingClientRect():null;
    return {viewport:innerWidth,scrollWidth:document.documentElement.scrollWidth,metrics,inner:ir?{left:ir.left,right:ir.right,width:ir.width}:null};
  });
  console.log('TOP_DESKTOP='+JSON.stringify(data));
  for(const [s,m] of Object.entries(data.metrics)){
    if(!m) throw new Error('DESKTOP_MISSING '+s);
    if(m.width<1918 || m.left>1.5 || m.right<1918.5) throw new Error('DESKTOP_NOT_FULLWIDTH '+s+' '+JSON.stringify(m));
  }
  if(data.scrollWidth>1922) throw new Error('DESKTOP_HORIZONTAL_OVERFLOW '+data.scrollWidth);
  if(data.inner && data.inner.width>1100) throw new Error('DESKTOP_INNER_CONTENT_STRETCHED '+JSON.stringify(data.inner));
  await page.close();
}

async function checkMobile(browser){
  const page=await browser.newPage({viewport:{width:390,height:844},deviceScaleFactor:1});
  await page.goto('https://tsurikue.com/',{waitUntil:'domcontentloaded',timeout:90000});
  await page.waitForSelector('.tq4',{timeout:30000});
  await page.waitForTimeout(900);
  const data=await page.evaluate(()=>{
    const sels=['.tq4','.tq4-party','.tq4-hero','.tq4-cats','.tq4-concept','.tq4-start','.tq4-about','.tq4-final','.tq-site-nav'];
    const metrics={};
    for(const s of sels){const el=document.querySelector(s);if(!el){metrics[s]=null;continue;}const r=el.getBoundingClientRect();metrics[s]={left:r.left,right:r.right,width:r.width,display:getComputedStyle(el).display};}
    return {viewport:innerWidth,scrollWidth:document.documentElement.scrollWidth,metrics};
  });
  console.log('TOP_MOBILE='+JSON.stringify(data));
  for(const s of ['.tq4','.tq4-party','.tq4-hero','.tq4-cats','.tq4-concept','.tq4-start','.tq4-about','.tq4-final']){
    const m=data.metrics[s]; if(!m) throw new Error('MOBILE_MISSING '+s);
    if(m.width<388.5 || m.width>391.5 || m.left<-1.5 || m.right>391.5) throw new Error('MOBILE_WIDTH_REGRESSION '+s+' '+JSON.stringify(m));
  }
  if(data.scrollWidth>392) throw new Error('MOBILE_HORIZONTAL_OVERFLOW '+data.scrollWidth);
  const nav=data.metrics['.tq-site-nav']; if(!nav || nav.display==='none' || nav.width<388.5) throw new Error('MOBILE_QUICK_NAV_REGRESSION '+JSON.stringify(nav));
  await page.close();
}

(async()=>{const browser=await chromium.launch({headless:true});try{await checkDesktop(browser);await checkMobile(browser);console.log('TOP_PC_FULLWIDTH_VERIFIED')}finally{await browser.close();}})().catch(e=>{console.error(e);process.exit(1)});
