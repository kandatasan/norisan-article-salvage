const { chromium } = require('playwright');
const assert = (ok,msg)=>{ if(!ok) throw new Error(msg); };
const rgb = s => (s.match(/\d+(?:\.\d+)?/g)||[]).slice(0,3).map(Number);
const isWhite = s => { const a=rgb(s); return a.length===3 && a.every(v=>v>=235); };
const isDark = s => { const a=rgb(s); return a.length===3 && a.reduce((x,y)=>x+y,0)<420; };

(async()=>{
  const browser=await chromium.launch({headless:true});
  try{
    for (const viewport of [{width:390,height:844},{width:1440,height:1000}]){
      const page=await browser.newPage({viewport});
      await page.goto('https://tsurikue.com/',{waitUntil:'networkidle',timeout:90000});
      await page.waitForSelector('.tq4 .tq4-hero h1',{timeout:30000});
      const data=await page.evaluate(()=>{
        const q=s=>document.querySelector(s), qa=s=>[...document.querySelectorAll(s)];
        const cs=s=>getComputedStyle(q(s));
        return {
          innerWidth:innerWidth, scrollWidth:document.documentElement.scrollWidth,
          heroH1Color:cs('.tq4 .tq4-hero h1').color,
          heroOverlayBg:cs('.tq4 .tq4-hero .wp-block-cover__background').backgroundImage,
          heroImg:q('.tq4 .tq4-hero img')?.src||'',
          cats:qa('.tq4 .tq4-cat').map(el=>({
            cls:el.className,
            titleColor:getComputedStyle(el.querySelector('h3')).color,
            descColor:getComputedStyle(el.querySelector('.tq4-card-desc')).color,
            overlayBg:getComputedStyle(el.querySelector('.wp-block-cover__background')).backgroundImage,
            img:el.querySelector('img')?.src||''
          })),
          outingImg:q('.tq4 .tq4-cat--outing img')?.src||'',
          h2Color:cs('.tq4 .tq4-cats h2').color,
          h2Bg:cs('.tq4 .tq4-cats h2').backgroundColor,
          menuToggle:!!q('.tq-site-menu-toggle')
        };
      });
      assert(data.scrollWidth<=data.innerWidth+1,`horizontal overflow ${viewport.width}: ${data.scrollWidth}`);
      assert(isWhite(data.heroH1Color),`hero h1 not white ${viewport.width}: ${data.heroH1Color}`);
      assert(data.heroOverlayBg.includes('linear-gradient'),`hero gradient missing ${viewport.width}`);
      assert(data.cats.length===4,`expected 4 cats, got ${data.cats.length}`);
      for(const c of data.cats){
        assert(isWhite(c.titleColor),`cat title not white ${viewport.width} ${c.cls}: ${c.titleColor}`);
        assert(c.overlayBg.includes('linear-gradient'),`cat gradient missing ${viewport.width} ${c.cls}`);
      }
      assert(data.outingImg.includes('img_2419'),`outing image is not dolphin ${viewport.width}: ${data.outingImg}`);
      assert(isDark(data.h2Color),`section h2 became light ${viewport.width}: ${data.h2Color}`);
      assert(data.h2Bg==='rgba(0, 0, 0, 0)' || data.h2Bg==='transparent',`section h2 bg regression ${viewport.width}: ${data.h2Bg}`);
      assert(data.menuToggle,'menu toggle missing');
      console.log('TOP_PHOTO_FIRST_VERIFIED',viewport,data);
      await page.close();
    }
  } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exit(1)});
