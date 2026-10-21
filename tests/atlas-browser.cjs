const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

const root = process.env.ATLAS_ROOT || path.resolve(__dirname, 'fixtures', 'dev-atlas');
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'atlas.json'), 'utf8'));

(async () => {
  const executablePath = process.env.BROWSER_PATH || [
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
  ].find(p => fs.existsSync(p));
  const browser = await chromium.launch({ headless: true, ...(executablePath ? { executablePath } : {}) });
  let count = 0;
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
    const errors = [], network = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('request', r => { if (/^https?:/.test(r.url())) network.push(r.url()); });
    const open = name => page.goto(pathToFileURL(path.join(root, 'site', name + '.html')).href);

    await open('index');
    assert.equal(await page.locator('article:visible').count(), manifest.demos.length);
    await page.locator('#search').fill('no-such-scenario-123');
    assert.equal(await page.locator('article:visible').count(), 0);
    await page.locator('#search').fill(manifest.demos[0].id.slice(0, 4));
    assert.ok(await page.locator('article:visible').count() >= 1);
    await page.locator('#search').fill('');

    for (const demo of manifest.demos) {
      const story = JSON.parse(fs.readFileSync(path.join(root, demo.story), 'utf8'));
      await open(demo.id);
      assert.equal(await page.locator('html').getAttribute('lang'), 'en');
      assert.equal(await page.locator('a[href="index.html"]').count(), 1);
      for (const [i, scenario] of story.scenarios.entries()) {
        await page.locator('#scenario').selectOption(String(i));
        assert.equal(await page.locator('#counter').textContent(), `0 / ${scenario.steps.length}`);
        assert.ok(await page.locator('#diagram [data-node]').count() >= 1);
        assert.equal(await page.locator('#conditions li').count(), scenario.preconditions.length);
        assert.equal(await page.locator('#outcome').textContent(), 'Outcome: ' + scenario.outcome);
        for (const [j, step] of scenario.steps.entries()) {
          await page.locator('#next').click();
          assert.equal(await page.locator('#step-title').textContent(), step.title);
          const evidenceSnippet = typeof step.evidence[0] === 'object' ? step.evidence[0].symbol : step.evidence[0];
          assert.ok((await page.locator('#step-evidence').textContent()).includes(evidenceSnippet));
          assert.equal(await page.locator(`[data-edge="${step.edge}"]`).getAttribute('stroke'), '#c6f27c');
          assert.equal(await page.locator('#counter').textContent(), `${j + 1} / ${scenario.steps.length}`);
        }
        await page.locator('#reset').click();
        await page.locator('#play').click();
        await page.waitForTimeout(80);
        const before = await page.locator('circle[aria-hidden]').getAttribute('cx');
        await page.waitForTimeout(100);
        assert.notEqual(await page.locator('circle[aria-hidden]').getAttribute('cx'), before);
        await page.locator('#reset').click();
        count++;
      }
    }

    await open(manifest.demos[0].id);
    await page.locator('#next').click();
    await page.setViewportSize({ width: 390, height: 844 });
    for (const name of ['index', ...manifest.demos.map(x => x.id)]) {
      await open(name);
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `Mobile overflow: ${name}`);
    }
    assert.deepEqual(errors, []);
    assert.deepEqual(network, []);
    console.log(`Atlas browser checks passed: ${manifest.demos.length} walkthroughs, ${count} scenarios, desktop/mobile, offline.`);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
