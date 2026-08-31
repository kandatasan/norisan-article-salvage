const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await page.goto('https://tsurikue.com/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(1600);

  const initial = await page.evaluate(() => {
    const nav = document.querySelector('.tq-site-nav');
    const links = nav ? [...nav.querySelectorAll('a')] : [];
    const visibleLinks = links.filter((a) => getComputedStyle(a).display !== 'none');
    const r = nav ? nav.getBoundingClientRect() : null;
    const privacy = document.querySelector('.tq-site-menu__utility a[href="/privacy-policy/"]');
    return {
      navDisplay: nav ? getComputedStyle(nav).display : null,
      navPosition: nav ? getComputedStyle(nav).position : null,
      navTop: r ? +r.top.toFixed(1) : null,
      navWidth: r ? +r.width.toFixed(1) : null,
      navHeight: r ? +r.height.toFixed(1) : null,
      visibleCount: visibleLinks.length,
      visibleText: visibleLinks.map((a) => a.textContent.trim()),
      aboutDisplay: links[links.length - 1] ? getComputedStyle(links[links.length - 1]).display : null,
      privacyExists: !!privacy,
      privacyText: privacy ? privacy.textContent.trim() : null,
      privacyHref: privacy ? privacy.getAttribute('href') : null,
    };
  });
  console.log('MOBILE_QUICK_NAV_INITIAL=' + JSON.stringify(initial));

  const expected = ['おでかけ', 'グルメ', '釣り', 'クルマ'];
  if (
    initial.navDisplay === 'none' ||
    initial.navPosition !== 'sticky' ||
    initial.navWidth < 389 ||
    initial.navHeight < 43 ||
    initial.visibleCount !== 4 ||
    JSON.stringify(initial.visibleText) !== JSON.stringify(expected) ||
    initial.aboutDisplay !== 'none' ||
    !initial.privacyExists ||
    initial.privacyText !== 'プライバシーポリシー' ||
    initial.privacyHref !== '/privacy-policy/'
  ) {
    throw new Error('MOBILE_QUICK_NAV_INITIAL_VERIFY_FAILED ' + JSON.stringify(initial));
  }

  await page.evaluate(() => window.scrollTo(0, 700));
  await page.waitForTimeout(300);
  const sticky = await page.evaluate(() => {
    const nav = document.querySelector('.tq-site-nav');
    const header = document.querySelector('#header');
    const nr = nav.getBoundingClientRect();
    const hr = header.getBoundingClientRect();
    return {
      navTop: +nr.top.toFixed(1),
      navBottom: +nr.bottom.toFixed(1),
      headerTop: +hr.top.toFixed(1),
      headerBottom: +hr.bottom.toFixed(1),
    };
  });
  console.log('MOBILE_QUICK_NAV_STICKY=' + JSON.stringify(sticky));
  if (Math.abs(sticky.navTop - sticky.headerBottom) > 2) {
    throw new Error('MOBILE_QUICK_NAV_STICKY_VERIFY_FAILED ' + JSON.stringify(sticky));
  }

  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(200);
  await page.mouse.click(31, 36);
  await page.waitForTimeout(350);
  const drawer = await page.evaluate(() => {
    const privacy = document.querySelector('.tq-site-menu__utility a[href="/privacy-policy/"]');
    const menu = document.querySelector('.tq-site-menu');
    return {
      menuVisible: menu ? getComputedStyle(menu).visibility : null,
      privacyVisible: privacy ? getComputedStyle(privacy).display !== 'none' : false,
      privacyText: privacy ? privacy.textContent.trim() : null,
    };
  });
  console.log('MOBILE_DRAWER_PRIVACY=' + JSON.stringify(drawer));
  if (drawer.menuVisible !== 'visible' || !drawer.privacyVisible || drawer.privacyText !== 'プライバシーポリシー') {
    throw new Error('MOBILE_DRAWER_PRIVACY_VERIFY_FAILED ' + JSON.stringify(drawer));
  }

  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
