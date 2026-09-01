const { chromium } = require('playwright');

const assert = (condition, message) => {
  if (!condition) throw new Error(message);
};

const rgb = value => (value.match(/\d+(?:\.\d+)?/g) || []).slice(0, 3).map(Number);
const isWhite = value => {
  const values = rgb(value);
  return values.length === 3 && values.every(channel => channel >= 235);
};

(async () => {
  const user = process.env.TSURIKUE_WP_USER;
  const password = process.env.TSURIKUE_WP_APP_PASSWORD;
  assert(user && password, 'WordPress credentials are missing');

  const auth = Buffer.from(`${user}:${password}`).toString('base64');
  const response = await fetch(
    'https://tsurikue.com/wp-json/wp/v2/pages/3289?context=edit&_fields=id,slug,status,content',
    {
      headers: {
        Authorization: `Basic ${auth}`,
        Accept: 'application/json',
        'User-Agent': 'tsurikue-gourmet-desktop-verifier/1.0',
      },
    },
  );
  assert(response.ok, `Draft fetch failed: HTTP ${response.status}`);
  const draft = await response.json();
  assert(draft.id === 3289, `Unexpected page id: ${draft.id}`);
  assert(draft.slug === 'gourmet-guide', `Unexpected slug: ${draft.slug}`);
  assert(draft.status === 'draft', `Unexpected status: ${draft.status}`);
  const rendered = draft.content?.rendered || draft.content?.raw || '';
  assert(rendered.includes('tq-gourmet'), 'Rendered gourmet content is missing');

  const browser = await chromium.launch({ headless: true });
  try {
    for (const viewport of [
      { width: 1024, height: 900 },
      { width: 1440, height: 1000 },
    ]) {
      const page = await browser.newPage({ viewport });
      await page.goto('https://tsurikue.com/', {
        waitUntil: 'domcontentloaded',
        timeout: 90000,
      });
      await page.waitForSelector('.post_content', { timeout: 30000 });
      await page.evaluate(html => {
        const target = document.querySelector('.post_content');
        target.innerHTML = html;
        window.scrollTo(0, 0);
      }, rendered);
      await page.waitForSelector('.tq-gourmet .tq-gourmet-hero h1', {
        timeout: 30000,
      });
      await page.waitForTimeout(1500);

      const metrics = await page.evaluate(() => {
        const q = selector => document.querySelector(selector);
        const qa = selector => [...document.querySelectorAll(selector)];
        const rect = selector => {
          const box = q(selector).getBoundingClientRect();
          return {
            left: box.left,
            right: box.right,
            top: box.top,
            bottom: box.bottom,
            width: box.width,
            height: box.height,
          };
        };
        const columns = selector =>
          getComputedStyle(q(selector)).gridTemplateColumns
            .split(' ')
            .filter(Boolean);

        const chooseCards = qa('.tq-gourmet-choice');
        const mealCards = qa('.tq-gourmet-card');
        const latestItems = qa('.tq-gourmet-latest-list li');
        const headings = qa('.tq-gourmet-card h3');

        return {
          innerWidth: window.innerWidth,
          scrollWidth: document.documentElement.scrollWidth,
          hero: rect('.tq-gourmet-hero'),
          heroTitle: rect('.tq-gourmet-hero h1'),
          heroTitleColor: getComputedStyle(q('.tq-gourmet-hero h1')).color,
          heroImage: q('.tq-gourmet-hero img')?.src || '',
          heroImageLoaded: Boolean(q('.tq-gourmet-hero img')?.naturalWidth),
          wrap: rect('.tq-gourmet-wrap'),
          chooseColumns: columns('.tq-gourmet-choose-grid'),
          chooseCount: chooseCards.length,
          chooseWidths: chooseCards.map(card => card.getBoundingClientRect().width),
          mealColumns: columns('.tq-gourmet-grid'),
          mealCount: mealCards.length,
          mealWidths: mealCards.map(card => card.getBoundingClientRect().width),
          latestColumns: columns('.tq-gourmet-latest-list'),
          latestCount: latestItems.length,
          latestWidths: latestItems.map(item => item.getBoundingClientRect().width),
          headingWritingModes: headings.map(
            heading => getComputedStyle(heading).writingMode,
          ),
          verticalOverflowCards: mealCards
            .filter(card => card.scrollWidth > card.clientWidth + 1)
            .length,
        };
      });

      assert(
        metrics.scrollWidth <= metrics.innerWidth + 1,
        `Horizontal overflow at ${viewport.width}px: ${metrics.scrollWidth}`,
      );
      assert(
        metrics.hero.width >= viewport.width - 2,
        `Hero is not full width at ${viewport.width}px: ${metrics.hero.width}`,
      );
      assert(
        metrics.heroTitle.left >= 0 && metrics.heroTitle.right <= viewport.width,
        `Hero title is clipped at ${viewport.width}px`,
      );
      assert(
        isWhite(metrics.heroTitleColor),
        `Hero title is not white at ${viewport.width}px: ${metrics.heroTitleColor}`,
      );
      assert(
        metrics.heroImage.includes('img_4017.jpg') && metrics.heroImageLoaded,
        `Hero image failed at ${viewport.width}px: ${metrics.heroImage}`,
      );
      assert(
        metrics.chooseCount === 4 && metrics.chooseColumns.length === 4,
        `Meal chooser is not four columns at ${viewport.width}px`,
      );
      assert(
        metrics.mealCount === 4 && metrics.mealColumns.length === 3,
        `Feature cards are not three columns at ${viewport.width}px`,
      );
      assert(
        metrics.latestCount > 0 && metrics.latestColumns.length === 3,
        `Latest cards are not three columns at ${viewport.width}px`,
      );
      assert(
        metrics.chooseWidths.every(width => width > 150),
        `Chooser card collapsed at ${viewport.width}px: ${metrics.chooseWidths}`,
      );
      assert(
        metrics.mealWidths.every(width => width > 150),
        `Feature card collapsed at ${viewport.width}px: ${metrics.mealWidths}`,
      );
      assert(
        metrics.latestWidths.every(width => width > 150),
        `Latest card collapsed at ${viewport.width}px: ${metrics.latestWidths}`,
      );
      assert(
        metrics.headingWritingModes.every(mode => mode === 'horizontal-tb'),
        `Vertical text detected at ${viewport.width}px: ${metrics.headingWritingModes}`,
      );
      assert(
        metrics.verticalOverflowCards === 0,
        `Card content overflow at ${viewport.width}px`,
      );

      console.log(
        'GOURMET_DESKTOP_VERIFIED',
        viewport.width,
        JSON.stringify(metrics),
      );

      if (viewport.width === 1440) {
        await page.screenshot({
          path: 'gourmet-desktop-1440.png',
          fullPage: true,
        });
      }
      await page.close();
    }
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error(error);
  process.exit(1);
});
