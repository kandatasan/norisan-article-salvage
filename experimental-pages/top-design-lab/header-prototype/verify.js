const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await mobile.goto('https://tsurikue.com/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await mobile.waitForTimeout(1800);

  const closed = await mobile.evaluate(() => {
    const toggle = document.querySelector('#tq-menu-toggle');
    const menu = document.querySelector('.tq-site-menu');
    const native = document.querySelector('.l-header__menuBtn');
    const trigger = document.querySelector('.tq-site-menu-trigger');
    const content = document.querySelector('#content');
    const r = toggle ? toggle.getBoundingClientRect() : null;
    const top = document.elementFromPoint(31, 36);
    const ncs = native ? getComputedStyle(native) : null;
    return {
      toggle: !!toggle,
      checked: toggle ? toggle.checked : null,
      menuPointerEvents: menu ? getComputedStyle(menu).pointerEvents : null,
      nativePointerEvents: ncs ? ncs.pointerEvents : null,
      nativeOpacity: ncs ? ncs.opacity : null,
      nativeVisibility: ncs ? ncs.visibility : null,
      nativeDisplay: ncs ? ncs.display : null,
      triggerDisplay: trigger ? getComputedStyle(trigger).display : null,
      navLinks: document.querySelectorAll('.tq-site-menu__quest a').length,
      contentZIndex: content ? getComputedStyle(content).zIndex : null,
      togglePointerEvents: toggle ? getComputedStyle(toggle).pointerEvents : null,
      toggleLeft: r ? +r.left.toFixed(1) : null,
      toggleTop: r ? +r.top.toFixed(1) : null,
      toggleWidth: r ? +r.width.toFixed(1) : null,
      toggleHeight: r ? +r.height.toFixed(1) : null,
      topId: top ? top.id : null,
    };
  });
  console.log('MOBILE_CLOSED=' + JSON.stringify(closed));
  if (!closed.toggle || closed.checked !== false || closed.navLinks !== 4 || closed.nativePointerEvents !== 'none' || closed.nativeOpacity !== '1' || closed.nativeVisibility !== 'visible' || closed.nativeDisplay === 'none' || closed.triggerDisplay !== 'none' || closed.menuPointerEvents !== 'none' || closed.togglePointerEvents !== 'auto' || closed.contentZIndex !== 'auto' || closed.toggleWidth < 47 || closed.toggleHeight < 47 || Math.abs(closed.toggleLeft - 7) > 1 || Math.abs(closed.toggleTop - 12) > 1 || closed.topId !== 'tq-menu-toggle') {
    throw new Error('MOBILE_BASE_VERIFY_FAILED ' + JSON.stringify(closed));
  }

  await mobile.mouse.click(31, 36);
  await mobile.waitForTimeout(450);
  const opened = await mobile.evaluate(() => {
    const toggle = document.querySelector('#tq-menu-toggle');
    const menu = document.querySelector('.tq-site-menu');
    const drawer = document.querySelector('.tq-site-menu__drawer');
    const r = drawer.getBoundingClientRect();
    const cs = getComputedStyle(menu);
    return {
      checked: toggle ? toggle.checked : null,
      visibility: cs.visibility,
      pointerEvents: cs.pointerEvents,
      opacity: cs.opacity,
      left: +r.left.toFixed(1),
      width: +r.width.toFixed(1),
      title: drawer.innerText.slice(0, 180),
    };
  });
  console.log('MOBILE_OPEN=' + JSON.stringify(opened));
  if (opened.checked !== true || opened.visibility !== 'visible' || opened.pointerEvents !== 'auto' || Math.abs(opened.left) > 0.5 || opened.width < 300 || !opened.title.includes('なにして遊ぶ')) {
    throw new Error('MOBILE_OPEN_VERIFY_FAILED ' + JSON.stringify(opened));
  }

  await mobile.mouse.click(31, 36);
  await mobile.waitForTimeout(300);
  const reclosed = await mobile.evaluate(() => {
    const toggle = document.querySelector('#tq-menu-toggle');
    const menu = document.querySelector('.tq-site-menu');
    return {
      checked: toggle ? toggle.checked : null,
      pointerEvents: getComputedStyle(menu).pointerEvents,
      opacity: getComputedStyle(menu).opacity,
    };
  });
  console.log('MOBILE_RECLOSED=' + JSON.stringify(reclosed));
  if (reclosed.checked !== false || reclosed.pointerEvents !== 'none') {
    throw new Error('MOBILE_RECLOSE_VERIFY_FAILED ' + JSON.stringify(reclosed));
  }

  const desktop = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  await desktop.goto('https://tsurikue.com/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await desktop.waitForTimeout(1600);
  const pc = await desktop.evaluate(() => {
    const n = document.querySelector('.tq-site-nav');
    const old = document.querySelector('#gnav');
    const trigger = document.querySelector('.tq-site-menu-trigger');
    const toggle = document.querySelector('#tq-menu-toggle');
    return {
      display: n ? getComputedStyle(n).display : null,
      links: n ? n.querySelectorAll('a').length : 0,
      oldGnav: old ? getComputedStyle(old).display : null,
      triggerDisplay: trigger ? getComputedStyle(trigger).display : null,
      toggleDisplay: toggle ? getComputedStyle(toggle).display : null,
      text: n ? n.innerText.replace(/\s+/g, ' ').trim() : '',
    };
  });
  console.log('DESKTOP=' + JSON.stringify(pc));
  if (pc.display === 'none' || pc.links !== 5 || pc.oldGnav !== 'none' || pc.triggerDisplay !== 'none' || pc.toggleDisplay !== 'none' || !pc.text.includes('おでかけ') || !pc.text.includes('ABOUT')) {
    throw new Error('DESKTOP_VERIFY_FAILED ' + JSON.stringify(pc));
  }

  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
