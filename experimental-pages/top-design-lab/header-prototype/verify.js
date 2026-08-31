const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await mobile.goto('https://tsurikue.com/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await mobile.waitForTimeout(1800);

  const closed = await mobile.evaluate(() => {
    const d = document.querySelector('.tq-site-menu');
    const summary = document.querySelector('.tq-site-menu > summary');
    const native = document.querySelector('.l-header__menuBtn');
    const logo = document.querySelector('#header .c-headLogo__link');
    return {
      details: !!d,
      open: d ? d.open : null,
      summaryDisplay: summary ? getComputedStyle(summary).display : null,
      nativePointerEvents: native ? getComputedStyle(native).pointerEvents : null,
      navLinks: document.querySelectorAll('.tq-site-menu__quest a').length,
      logoText: logo ? logo.textContent.trim() : null,
      headerPosition: getComputedStyle(document.querySelector('#header')).position,
    };
  });
  console.log('MOBILE_CLOSED=' + JSON.stringify(closed));
  if (!closed.details || closed.navLinks !== 4 || closed.nativePointerEvents !== 'none') {
    throw new Error('MOBILE_BASE_VERIFY_FAILED ' + JSON.stringify(closed));
  }

  await mobile.locator('.tq-site-menu > summary').click({ force: true });
  await mobile.waitForTimeout(350);
  const opened = await mobile.evaluate(() => {
    const d = document.querySelector('.tq-site-menu');
    const drawer = document.querySelector('.tq-site-menu__drawer');
    const r = drawer.getBoundingClientRect();
    return {
      open: d.open,
      left: +r.left.toFixed(1),
      width: +r.width.toFixed(1),
      title: drawer.innerText.slice(0, 120),
    };
  });
  console.log('MOBILE_OPEN=' + JSON.stringify(opened));
  if (!opened.open || Math.abs(opened.left) > 0.5 || opened.width < 300) {
    throw new Error('MOBILE_OPEN_VERIFY_FAILED ' + JSON.stringify(opened));
  }

  const desktop = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  await desktop.goto('https://tsurikue.com/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await desktop.waitForTimeout(1600);
  const pc = await desktop.evaluate(() => {
    const n = document.querySelector('.tq-site-nav');
    const old = document.querySelector('#gnav');
    return {
      display: n ? getComputedStyle(n).display : null,
      links: n ? n.querySelectorAll('a').length : 0,
      oldGnav: old ? getComputedStyle(old).display : null,
      headerPosition: getComputedStyle(document.querySelector('#header')).position,
    };
  });
  console.log('DESKTOP=' + JSON.stringify(pc));
  if (pc.display === 'none' || pc.links !== 5 || pc.oldGnav !== 'none') {
    throw new Error('DESKTOP_VERIFY_FAILED ' + JSON.stringify(pc));
  }

  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
