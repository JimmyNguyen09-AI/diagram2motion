const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

(async () => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'atlas-bundle-'));
  const source = process.env.BUNDLE_PATH || path.resolve(__dirname, 'fixtures/dev-atlas/site/all-in-one.html');
  const target = path.join(temp, 'standalone.html');
  fs.copyFileSync(source, target);

  const executablePath = process.env.BROWSER_PATH || [
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
  ].find(p => fs.existsSync(p));
  const browser = await chromium.launch({ headless: true, ...(executablePath ? { executablePath } : {}) });

  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, acceptDownloads: true });
    const errors = [], requests = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('request', r => requests.push(r.url()));

    await page.goto(pathToFileURL(target).href);
    const frame = page.frameLocator('#viewer');
    await frame.locator('article').first().waitFor();
    const articleCount = await frame.locator('article').count();
    assert.ok(articleCount >= 1);

    await frame.locator('article a').first().click();
    await frame.locator('#scenario').waitFor();
    assert.ok(page.url().includes('#'));

    const ids = await page.locator('#walkthrough option').evaluateAll(options => options.map(o => o.value).filter(x => x !== 'index'));
    let count = 0;
    for (const id of ids) {
      await page.locator('#walkthrough').selectOption(id);
      await page.waitForFunction(id => document.getElementById('viewer').contentDocument?.getElementById('title')?.textContent === document.getElementById('walkthrough').selectedOptions[0].textContent, id);
      const n = await frame.locator('#scenario option').count();
      for (let i = 0; i < n; i++) {
        await frame.locator('#scenario').selectOption(String(i));
        await frame.locator('#next').click();
        assert.match(await frame.locator('#counter').textContent(), /^1 \/ /);
        count++;
      }
    }

    const downloadPromise = page.waitForEvent('download');
    await frame.locator('#export').click();
    const download = await downloadPromise;
    assert.match(download.suggestedFilename(), /\.svg$/);

    await frame.locator('a[href="index.html"]').click();
    await frame.locator('article').first().waitFor();

    await page.goBack();
    await frame.locator('#scenario').waitFor();

    await page.reload();
    await frame.locator('#scenario').waitFor();

    await page.setViewportSize({ width: 390, height: 844 });
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));

    await page.locator('#overview').click();
    await frame.locator('article').first().waitFor();

    assert.deepEqual(errors, []);
    assert.ok(requests.every(url => url.startsWith(pathToFileURL(target).href)), JSON.stringify(requests));
    console.log(`Bundle passed: ${ids.length} walkthroughs / ${count} scenarios, isolated file, navigation, reload, SVG export, mobile, no dependencies.`);
  } finally {
    await browser.close();
    fs.rmSync(temp, { recursive: true, force: true });
  }
})().catch(e => { console.error(e); process.exit(1); });
