const { chromium } = require('playwright');

(async()=>{
  const browser = await chromium.launch({headless:true});
  const page = await browser.newPage({viewport:{width:390,height:844}, deviceScaleFactor:1});
  await page.goto('https://tsurikue.com/ux-koukai/?tq_nav_canary=1',{waitUntil:'domcontentloaded',timeout:60000});
  await page.waitForTimeout(1200);

  const closed = await page.evaluate(()=>{
    const root=document.querySelector('.tq-global-site-nav-root');
    const toggle=document.querySelector('#tq-global-menu-toggle');
    const menu=document.querySelector('.tq-site-menu');
    const drawer=document.querySelector('.tq-site-menu__drawer');
    const nav=document.querySelector('.tq-site-nav');
    const native=document.querySelector('#header .l-header__menuBtn');
    const r=toggle?.getBoundingClientRect();
    const hit=document.elementFromPoint(31,36);
    return {
      root:!!root,
      toggle:!!toggle,
      checked:toggle?.checked,
      toggleRect:r?{left:r.left,top:r.top,width:r.width,height:r.height}:null,
      hitId:hit?.id||'', hitClass:hit?.className||'',
      nativeDisplay:native?getComputedStyle(native).display:null,
      nativeVisibility:native?getComputedStyle(native).visibility:null,
      nativeOpacity:native?getComputedStyle(native).opacity:null,
      navDisplay:nav?getComputedStyle(nav).display:null,
      navPosition:nav?getComputedStyle(nav).position:null,
      navTop:nav?nav.getBoundingClientRect().top:null,
      navLinks:nav?[...nav.querySelectorAll('a')].map(a=>a.textContent.trim()):[],
      menuOpacity:menu?getComputedStyle(menu).opacity:null,
      drawerLeft:drawer?drawer.getBoundingClientRect().left:null,
    };
  });
  console.log('CANARY_MOBILE_CLOSED='+JSON.stringify(closed));
  if(!closed.root || !closed.toggle) throw new Error('GLOBAL_NAV_ROOT_OR_TOGGLE_MISSING');
  if(closed.hitId!=='tq-global-menu-toggle') throw new Error('TOGGLE_NOT_TOP_HIT_TARGET');
  if(closed.navPosition!=='fixed' || Math.abs(closed.navTop-64)>3) throw new Error('MOBILE_QUICK_NAV_POSITION_BAD');
  if(closed.navLinks.slice(0,4).join('|')!=='おでかけ|グルメ|釣り|クルマ') throw new Error('MOBILE_QUICK_NAV_LINKS_BAD');
  if(closed.nativeVisibility!=='visible' || closed.nativeOpacity==='0') throw new Error('NATIVE_HAMBURGER_NOT_VISIBLE');

  await page.mouse.click(31,36);
  await page.waitForTimeout(350);
  const opened = await page.evaluate(()=>{
    const t=document.querySelector('#tq-global-menu-toggle');
    const m=document.querySelector('.tq-site-menu');
    const d=document.querySelector('.tq-site-menu__drawer');
    return {
      checked:t?.checked,
      opacity:m?getComputedStyle(m).opacity:null,
      pointer:m?getComputedStyle(m).pointerEvents:null,
      drawerLeft:d?d.getBoundingClientRect().left:null,
      text:d?.innerText||'',
      privacy:!!d?.querySelector('a[href="/privacy-policy/"]')
    };
  });
  console.log('CANARY_MOBILE_OPEN='+JSON.stringify(opened));
  if(!opened.checked || opened.opacity!=='1' || opened.pointer!=='auto' || Math.abs(opened.drawerLeft)>3) throw new Error('DRAWER_DID_NOT_OPEN');
  for(const text of ['今日は、','おでかけ','グルメ','釣り','クルマ','のんびり冒険中。']) if(!opened.text.includes(text)) throw new Error('DRAWER_TEXT_MISSING_'+text);
  if(!opened.privacy) throw new Error('PRIVACY_LINK_MISSING');

  await page.mouse.click(31,36);
  await page.waitForTimeout(300);
  const reclosed=await page.evaluate(()=>({
    checked:document.querySelector('#tq-global-menu-toggle')?.checked,
    opacity:getComputedStyle(document.querySelector('.tq-site-menu')).opacity
  }));
  console.log('CANARY_MOBILE_RECLOSED='+JSON.stringify(reclosed));
  if(reclosed.checked || reclosed.opacity!=='0') throw new Error('DRAWER_DID_NOT_RECLOSE');

  const desktop=await browser.newPage({viewport:{width:1280,height:900}});
  await desktop.goto('https://tsurikue.com/ux-koukai/?tq_nav_canary=desktop',{waitUntil:'domcontentloaded',timeout:60000});
  await desktop.waitForTimeout(900);
  const desk=await desktop.evaluate(()=>{
    const nav=document.querySelector('.tq-site-nav');
    return {root:!!document.querySelector('.tq-global-site-nav-root'),display:nav?getComputedStyle(nav).display:null,text:nav?.innerText||'',links:nav?.querySelectorAll('a').length||0,oldGnav:document.querySelector('#gnav')?getComputedStyle(document.querySelector('#gnav')).display:null};
  });
  console.log('CANARY_DESKTOP='+JSON.stringify(desk));
  if(!desk.root || desk.display!=='flex' || desk.links!==5 || !desk.text.includes('ABOUT') || desk.oldGnav!=='none') throw new Error('DESKTOP_NAV_BAD');
  await browser.close();
})();
