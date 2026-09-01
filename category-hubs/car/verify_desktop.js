const { chromium } = require('playwright');

const assert = (condition, message) => {
  if (!condition) throw new Error(message);
};

const rgb = value => (value.match(/\d+(?:\.\d+)?/g) || []).slice(0, 3).map(Number);
const isWhite = value => {
  const values = rgb(value);
  return values.length === 3 && values.every(channel => channel >= 235);
};
const normalizeLink = value => {
  const url = new URL(value);
  return url.origin + url.pathname.replace(/\/+$/, '');
};

(async () => {
  const user = process.env.TSURIKUE_WP_USER;
  const password = process.env.TSURIKUE_WP_APP_PASSWORD;
  assert(user && password, 'WordPress credentials are missing');

  const auth = Buffer.from(user + ':' + password).toString('base64');
  const headers = {
    Authorization: 'Basic ' + auth,
    Accept: 'application/json',
    'User-Agent': 'tsurikue-car-desktop-verifier/1.0',
  };

  const draftResponse = await fetch(
    'https://tsurikue.com/wp-json/wp/v2/pages?slug=car-guide&status=draft&context=edit&per_page=5&_fields=id,slug,status,content,title',
    { headers, signal: AbortSignal.timeout(40000) },
  );
  assert(draftResponse.ok, 'Draft lookup failed: HTTP ' + draftResponse.status);
  const drafts = await draftResponse.json();
  assert(drafts.length === 1, 'Expected one car draft, found ' + drafts.length);
  const draft = drafts[0];
  assert(draft.slug === 'car-guide', 'Unexpected slug: ' + draft.slug);
  assert(draft.status === 'draft', 'Unexpected status: ' + draft.status);
  const rendered = draft.content?.rendered || draft.content?.raw || '';
  assert(rendered.includes('tq-car'), 'Rendered car content is missing');
  assert(/IMG_2012|img_2012/i.test(rendered), 'Expected car hero is not saved');
  assert(!rendered.includes('tq-global-site-nav-ref'), 'Temporary navigation remains');
  assert(!rendered.includes('TQ SITEWIDE HOLIDAY MENU'), 'Custom menu remains');

  const categoriesResponse = await fetch(
    'https://tsurikue.com/wp-json/wp/v2/categories?include=10,11&per_page=10&_fields=id,slug,parent,count',
    {
      headers: {
        Accept: 'application/json',
        'User-Agent': 'tsurikue-car-desktop-verifier/1.0',
      },
      signal: AbortSignal.timeout(40000),
    },
  );
  assert(
    categoriesResponse.ok,
    'Car category lookup failed: HTTP ' + categoriesResponse.status,
  );
  const categories = await categoriesResponse.json();
  const categoryMap = new Map(categories.map(category => [category.id, category]));
  assert(categoryMap.get(10)?.slug === 'car', 'Parent car category 10 is invalid');
  assert(
    categoryMap.get(11)?.slug === 'car-goods-wash' &&
      categoryMap.get(11)?.parent === 10,
    'Child car category 11 is invalid',
  );

  const postsResponse = await fetch(
    'https://tsurikue.com/wp-json/wp/v2/posts?categories=10,11&per_page=100&orderby=date&order=desc&_fields=id,link,categories',
    {
      headers: {
        Accept: 'application/json',
        'User-Agent': 'tsurikue-car-desktop-verifier/1.0',
      },
      signal: AbortSignal.timeout(40000),
    },
  );
  assert(postsResponse.ok, 'Car post lookup failed: HTTP ' + postsResponse.status);
  const carPosts = await postsResponse.json();
  assert(carPosts.length >= 15, 'Too few car posts returned: ' + carPosts.length);
  assert(
    carPosts.every(post =>
      post.categories.some(category => category === 10 || category === 11),
    ),
    'The car post API returned a post outside categories 10 and 11',
  );
  const expectedCarLinks = new Set(carPosts.map(post => normalizeLink(post.link)));
  console.log(
    'CAR_EXPECTED_POSTS',
    JSON.stringify(carPosts.map(post => ({
      id: post.id,
      link: post.link,
      categories: post.categories,
    }))),
  );

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
      await page.waitForSelector('.tq-car .tq-car-hero h1', {
        timeout: 30000,
      });
      await page.waitForFunction(
        () => {
          const image = document.querySelector('.tq-car-hero img');
          return Boolean(image?.complete && image?.naturalWidth);
        },
        { timeout: 30000 },
      );
      await page.waitForTimeout(600);

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

        const chooseCards = qa('.tq-car-choice');
        const proofItems = qa('.tq-car-proof-item');
        const featureCards = qa('.tq-car-card');
        const routeCards = qa('.tq-car-route');
        const latestItems = qa('.tq-car-latest-list li');
        const headings = qa('.tq-car-card h3,.tq-car-route h3');
        const heroImage = q('.tq-car-hero img');

        return {
          innerWidth: window.innerWidth,
          scrollWidth: document.documentElement.scrollWidth,
          hero: rect('.tq-car-hero'),
          heroTitle: rect('.tq-car-hero h1'),
          heroTitleColor: getComputedStyle(q('.tq-car-hero h1')).color,
          heroImage: heroImage?.currentSrc || heroImage?.src || '',
          heroImageLoaded: Boolean(heroImage?.naturalWidth),
          heroImageNaturalWidth: heroImage?.naturalWidth || 0,
          heroImageNaturalHeight: heroImage?.naturalHeight || 0,
          heroObjectPosition: getComputedStyle(heroImage).objectPosition,
          wrap: rect('.tq-car-wrap'),
          chooseColumns: columns('.tq-car-choose-grid'),
          chooseCount: chooseCards.length,
          chooseWidths: chooseCards.map(card => card.getBoundingClientRect().width),
          proofColumns: columns('.tq-car-proof-grid'),
          proofCount: proofItems.length,
          proofWidths: proofItems.map(item => item.getBoundingClientRect().width),
          featureColumns: columns('.tq-car-feature-grid'),
          featureCount: featureCards.length,
          featureWidths: featureCards.map(card => card.getBoundingClientRect().width),
          routeColumns: columns('.tq-car-route-grid'),
          routeCount: routeCards.length,
          routeWidths: routeCards.map(card => card.getBoundingClientRect().width),
          latestColumns: columns('.tq-car-latest-list'),
          latestCount: latestItems.length,
          latestWidths: latestItems.map(item => item.getBoundingClientRect().width),
          latestLinks: [...new Set(
            qa('.tq-car-latest-list a').map(link => link.href),
          )],
          headingWritingModes: headings.map(
            heading => getComputedStyle(heading).writingMode,
          ),
          overflowCards: [...featureCards, ...routeCards]
            .filter(card => card.scrollWidth > card.clientWidth + 1)
            .length,
        };
      });

      assert(
        metrics.scrollWidth <= metrics.innerWidth + 1,
        'Horizontal overflow at ' + viewport.width + 'px: ' + metrics.scrollWidth,
      );
      assert(
        metrics.hero.width >= viewport.width - 2,
        'Hero is not full width at ' + viewport.width + 'px: ' + metrics.hero.width,
      );
      assert(
        metrics.heroTitle.left >= 0 && metrics.heroTitle.right <= viewport.width,
        'Hero title is clipped at ' + viewport.width + 'px',
      );
      assert(
        isWhite(metrics.heroTitleColor),
        'Hero title is not white at ' + viewport.width + 'px: ' + metrics.heroTitleColor,
      );
      assert(
        metrics.heroImageLoaded,
        'Hero image failed at ' + viewport.width + 'px: ' + metrics.heroImage,
      );
      assert(
        /img_2012/i.test(metrics.heroImage),
        'Unexpected hero image at ' + viewport.width + 'px: ' + metrics.heroImage,
      );
      assert(
        metrics.heroImageNaturalWidth >= 1000 &&
          metrics.heroImageNaturalHeight >= 700,
        'Hero image is too small at ' + viewport.width + 'px: ' +
          metrics.heroImageNaturalWidth + 'x' + metrics.heroImageNaturalHeight,
      );
      assert(
        metrics.chooseCount === 4 && metrics.chooseColumns.length === 4,
        'Start cards are not four columns at ' + viewport.width + 'px',
      );
      assert(
        metrics.proofCount === 4 && metrics.proofColumns.length === 4,
        'Proof items are not four columns at ' + viewport.width + 'px',
      );
      assert(
        metrics.featureCount === 4 && metrics.featureColumns.length === 3,
        'Feature cards are not three columns at ' + viewport.width + 'px',
      );
      assert(
        metrics.routeCount === 4 && metrics.routeColumns.length === 4,
        'Route cards are not four columns at ' + viewport.width + 'px',
      );
      assert(
        metrics.latestCount === Math.min(6, carPosts.length) &&
          metrics.latestColumns.length === 3,
        'Latest car cards are invalid at ' + viewport.width + 'px',
      );
      for (const [label, widths] of [
        ['start', metrics.chooseWidths],
        ['proof', metrics.proofWidths],
        ['feature', metrics.featureWidths],
        ['route', metrics.routeWidths],
        ['latest', metrics.latestWidths],
      ]) {
        assert(
          widths.every(width => width > 150),
          label + ' card collapsed at ' + viewport.width + 'px: ' + widths,
        );
      }
      const wrongLatestLinks = metrics.latestLinks.filter(
        link => !expectedCarLinks.has(normalizeLink(link)),
      );
      assert(
        wrongLatestLinks.length === 0,
        'Non-car posts detected at ' + viewport.width + 'px: ' +
          wrongLatestLinks.join(', '),
      );
      assert(
        metrics.headingWritingModes.every(mode => mode === 'horizontal-tb'),
        'Vertical text detected at ' + viewport.width + 'px: ' +
          metrics.headingWritingModes,
      );
      assert(
        metrics.overflowCards === 0,
        'Card content overflow at ' + viewport.width + 'px',
      );

      console.log(
        'CAR_DESKTOP_VERIFIED',
        viewport.width,
        JSON.stringify(metrics),
      );

      if (viewport.width === 1440) {
        await page.screenshot({
          path: 'car-desktop-1440.png',
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
