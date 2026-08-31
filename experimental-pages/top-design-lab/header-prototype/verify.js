const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await mobile.goto('https://tsurikue.com/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await mobile.waitForTimeout(1800);

  const closed = await mobile.evaluate(() => {
    const menu = document.querySelector('.tq-site-menu');
    const trigger = document.querySelector('.tq-site-menu-trigger');
    const native = document.querySelector('.l-header__menuBtn');
    const logo = document.querySelector('#header .c-headLogo__link');
    return {
      menu: !!menu,
      trigger: !!trigger,
      visibility: menu ? getComputedStyle(menu).visibility : null,
      pointerEvents: menu ? getComputedStyle(menu).pointerEvents : null,
      nativePointerEvents: native ? getComputedStyle(native).pointerEvents : null,
      navLinks: document.querySelectorAll('.tq-site-menu__quest a').length,
      logoText: logo ? logo.textContent.trim() : null,
      headerPosition: getComputedStyle(document.querySelector('#header')).position,
      hash: location.hash,
    };
  });
  console.log('MOBILE_CLOSED=' + JSON.stringify(closed));
  if (!closed.menu || !closed.trigger || closed.navLinks !== 4 || closed.nativePointerEvents !== 'none') {
    throw new Error('MOBILE_BASE_VERIFY_FAILED ' + JSON.stringify(closed));
  }

  await mobile.locator('.tq-site-menu-trigger').click({ force: true });
  await mobile.waitForTimeout(450);
  const opened = await mobile.evaluate(() => {
    const menu = document.querySelector('.tq-site-menu');
    const drawer = document.querySelector('.tq-site-menu__drawer');
    const r = drawer.getBoundingClientRect();
    const cs = getComputedStyle(menu);
    return {
      hash: location.hash,
      visibility: cs.visibility,
      pointerEvents: cs.pointerEvents,
      opacity: cs.opacity,
      left: +r.left.toFixed(1),
      width: +r.width.toFixed(1),
      title: drawer.innerText.slice(0, 140),
    };
  });
  console.log('MOBILE_OPEN=' + JSON.stringify(opened));
  if (opened.hash !== '#tq-holiday-menu' || opened.visibility !== 'visible' || opened.pointerEvents !== 'auto' || Math.abs(opened.left) > 0.5 || opened.width < 300 || !opened.title.includes('なにして遊ぶ')) {
    throw new Error('MOBILE_OPEN_VERIFY_FAILED ' + JSON.stringify(opened));
  }

  await mobile.locator('.tq-site-menu__close').click({ force: true });
  await mobile.waitForTimeout(250);
  const reclosed = await mobile.evaluate(() => {
    const menu = document.querySelector('.tq-site-menu');
    return {
      hash: location.hash,
      visibility: getComputedStyle(menu).visibility,
      pointerEvents: getComputedStyle(menu).pointerEvents,
    };
  });
  console.log('MOBILE_RECLOSED=' + JSON.stringify(reclosed));
  if (reclosed.hash === '#tq-holiday-menu' || reclosed.pointerEvents !== 'none') {
    throw new Error('MOBILE_RECLOSE_VERIFY_FAILED ' + JSON.stringify(reclosed));
  }

  const desktop = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  await desktop.goto('https://tsurikue.com/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await desktop.waitForTimeout(1600);
  const pc = await desktop.evaluate(() => {
    const n = document.querySelector('.tq-site-nav');
    const old = document.querySelector('#gnav');
    const trigger = document.querySelector('.tq-site-menu-trigger');
    return {
      display: n ? getComputedStyle(n).display : null,
      links: n ? n.querySelectorAll('a').length : 0,
      oldGnav: old ? getComputedStyle(old).display : null,
      triggerDisplay: trigger ? getComputedStyle(trigger).display : null,
      headerPosition: getComputedStyle(document.querySelector('#header')).position,
    };
  });
  console.log('DESKTOP=' + JSON.stringify(pc));
  if (pc.display === 'none' || pc.links !== 5 || pc.oldGnav !== 'none' || pc.triggerDisplay !== 'none') {
    throw new Error('DESKTOP_VERIFY_FAILED ' + JSON.stringify(pc));
  }

  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
