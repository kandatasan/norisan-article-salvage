const { chromium } = require('playwright');

const targets=[
  ['car','https://tsurikue.com/ux-koukai/'],
  ['outing','https://tsurikue.com/hiroshima-sightseeing/'],
  ['fishing','https://tsurikue.com/kantan-aoriika/'],
  ['gourmet','https://tsurikue.com/higashihiroshima-ramen/'],
  ['page','https://tsurikue.com/profile/'],
];

(async()=>{
  const browser=await chromium.launch({headless:true});
  for(const [name,url] of targets){
    const page=await browser.newPage({viewport:{width:390,height:844}});
    await page.goto(url+'?tq_nav_rollout='+Date.now(),{waitUntil:'domcontentloaded',timeout:60000});
    await page.waitForTimeout(700);
    const info=await page.evaluate(()=>{
      const root=document.querySelector('.tq-global-site-nav-root');
      const toggle=document.querySelector('#tq-global-menu-toggle');
      const nav=document.querySelector('.tq-site-nav');
      const roots=document.querySelectorAll('.tq-global-site-nav-root').length;
      const links=nav?[...nav.querySelectorAll('a')].map(a=>a.textContent.trim()):[];
      const r=toggle?.getBoundingClientRect();
      const hit=document.elementFromPoint(31,36);
      return {root:!!root,roots,toggle:!!toggle,hitId:hit?.id||'',rect:r?{left:r.left,top:r.top,width:r.width,height:r.height}:null,links,navTop:nav?.getBoundingClientRect().top,navPosition:nav?getComputedStyle(nav).position:null};
    });
    console.log(`ROLLOUT_${name.toUpperCase()}=`+JSON.stringify(info));
    if(!info.root || info.roots!==1 || !info.toggle) throw new Error(name+'_ROOT_OR_TOGGLE_BAD');
    if(info.hitId!=='tq-global-menu-toggle') throw new Error(name+'_TOGGLE_NOT_HIT');
    if(info.links.slice(0,4).join('|')!=='おでかけ|グルメ|釣り|クルマ') throw new Error(name+'_QUICK_NAV_BAD');
    if(info.navPosition!=='fixed' || Math.abs(info.navTop-64)>3) throw new Error(name+'_QUICK_NAV_POSITION_BAD');
    await page.mouse.click(31,36);
    await page.waitForTimeout(260);
    const open=await page.evaluate(()=>({
      checked:document.querySelector('#tq-global-menu-toggle')?.checked,
      opacity:getComputedStyle(document.querySelector('.tq-site-menu')).opacity,
      text:document.querySelector('.tq-site-menu__drawer')?.innerText||'',
      privacy:!!document.querySelector('.tq-site-menu__drawer a[href="/privacy-policy/"]')
    }));
    console.log(`ROLLOUT_${name.toUpperCase()}_OPEN=`+JSON.stringify(open));
    if(!open.checked || open.opacity!=='1' || !open.privacy || !open.text.includes('今日は、')) throw new Error(name+'_DRAWER_BAD');
    await page.close();
  }

  const desktop=await browser.newPage({viewport:{width:1280,height:900}});
  await desktop.goto('https://tsurikue.com/ux-koukai/?tq_nav_rollout=desktop',{waitUntil:'domcontentloaded',timeout:60000});
  await desktop.waitForTimeout(700);
  const d=await desktop.evaluate(()=>{
    const nav=document.querySelector('.tq-site-nav');
    return {display:nav?getComputedStyle(nav).display:null,links:nav?.querySelectorAll('a').length||0,text:nav?.innerText||'',oldGnav:document.querySelector('#gnav')?getComputedStyle(document.querySelector('#gnav')).display:null};
  });
  console.log('ROLLOUT_DESKTOP='+JSON.stringify(d));
  if(d.display!=='flex' || d.links!==5 || !d.text.includes('ABOUT') || d.oldGnav!=='none') throw new Error('ROLLOUT_DESKTOP_BAD');
  await browser.close();
})();
