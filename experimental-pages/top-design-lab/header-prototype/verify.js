const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await mobile.goto('https://tsurikue.com/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await mobile.waitForTimeout(1800);

  const base = await mobile.evaluate(() => {
    const toggle = document.querySelector('#tq-menu-toggle');
    const menu = document.querySelector('.tq-site-menu');
    const native = document.querySelector('.l-header__menuBtn');
    const r = toggle ? toggle.getBoundingClientRect() : null;
    const describe = (e) => {
      if (!e) return null;
      const cs = getComputedStyle(e);
      const rr = e.getBoundingClientRect();
      return {
        tag: e.tagName,
        id: e.id,
        cls: typeof e.className === 'string' ? e.className : '',
        position: cs.position,
        zIndex: cs.zIndex,
        pointerEvents: cs.pointerEvents,
        opacity: cs.opacity,
        transform: cs.transform,
        isolation: cs.isolation,
        left: +rr.left.toFixed(1),
        top: +rr.top.toFixed(1),
        width: +rr.width.toFixed(1),
        height: +rr.height.toFixed(1),
      };
    };
    const ancestors = [];
    let p = toggle;
    for (let i = 0; p && i < 10; i++, p = p.parentElement) ancestors.push(describe(p));
    return {
      toggle: describe(toggle),
      checked: toggle ? toggle.checked : null,
      menuPointerEvents: menu ? getComputedStyle(menu).pointerEvents : null,
      nativePointerEvents: native ? getComputedStyle(native).pointerEvents : null,
      navLinks: document.querySelectorAll('.tq-site-menu__quest a').length,
      hitStack: document.elementsFromPoint(31, 36).slice(0, 12).map(describe),
      ancestors,
      rect: r ? { left: r.left, top: r.top, width: r.width, height: r.height } : null,
    };
  });
  console.log('MOBILE_DIAGNOSTIC_BASE=' + JSON.stringify(base));

  if (!base.toggle || base.checked !== false || base.navLinks !== 4 || base.nativePointerEvents !== 'none') {
    throw new Error('MOBILE_DIAGNOSTIC_BASE_FAILED ' + JSON.stringify(base));
  }

  await mobile.mouse.click(31, 36);
  await mobile.waitForTimeout(250);
  let checked = await mobile.locator('#tq-menu-toggle').isChecked();
  console.log('PHYSICAL_CLICK_CHECKED=' + checked);

  if (!checked) {
    await mobile.locator('#tq-menu-toggle').evaluate((el) => el.click());
    await mobile.waitForTimeout(150);
    checked = await mobile.locator('#tq-menu-toggle').isChecked();
    console.log('PROGRAMMATIC_CLICK_CHECKED=' + checked);
    if (checked) {
      throw new Error('PHYSICAL_HIT_OBSTRUCTED');
    }
    throw new Error('CHECKBOX_DEFAULT_ACTION_BLOCKED');
  }

  throw new Error('DIAGNOSTIC_PHYSICAL_CLICK_WORKED');
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
