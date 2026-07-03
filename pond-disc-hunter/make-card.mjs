// Composites a finished Pond Disc Hunter card from a photo + disc data,
// using the generator page in headless Chromium.
//
//   node make-card.mjs <photo> --name "INNOVA THUNDERBIRD" \
//     --speed 9 --glide 5 --turn 0 --fade 2 --story "..." \
//     [--unknown] [--zoom 1.2] [--out card.png]
//
// Requires playwright (preinstalled in the Claude remote environment at
// /opt/node22/lib/node_modules/playwright with browsers in /opt/pw-browsers).

import { resolve, dirname } from 'node:path';
import { writeFileSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));

async function loadChromium() {
  for (const spec of ['playwright', '/opt/node22/lib/node_modules/playwright/index.mjs']) {
    try { return (await import(spec)).chromium; } catch {}
  }
  throw new Error('playwright not found — npm i -g playwright');
}

const args = process.argv.slice(2);
const photo = args.find(a => !a.startsWith('--'));
const opt = (k, d) => { const i = args.indexOf('--' + k); return i >= 0 ? args[i + 1] : d; };
const has = k => args.includes('--' + k);
if (!photo) { console.error('usage: node make-card.mjs <photo> [--name ... --speed ... --story ... --unknown --zoom --out]'); process.exit(1); }

const chromium = await loadChromium();
const browser = await chromium.launch({
  executablePath: process.env.PW_CHROMIUM || '/opt/pw-browsers/chromium',
}).catch(() => chromium.launch());
const page = await browser.newPage({ viewport: { width: 1400, height: 1100 } });
await page.goto(pathToFileURL(resolve(here, 'index.html')).href);
await page.evaluate(() => localStorage.clear());
await page.reload();

// orientation first (it resets pan), then unknown: the checkbox handler
// prefills defaults, and explicit --name/--story flags should win over them
if (has('vertical')) await page.selectOption('#orient', 'vertical');
if (has('unknown')) await page.check('#unknown');
for (const f of ['name', 'speed', 'glide', 'turn', 'fade', 'story']) {
  const v = opt(f);
  if (v != null) await page.fill('#' + f, String(v));
}
const zoom = parseFloat(opt('zoom', '1'));
if (zoom !== 1) {
  await page.locator('#zoom').evaluate((el, z) => {
    el.value = Math.round(z * 100);
    el.dispatchEvent(new Event('input', { bubbles: true }));
  }, zoom);
}
await page.setInputFiles('#photo', resolve(photo));
await page.waitForTimeout(500);

const dataUrl = await page.evaluate(() => document.getElementById('card').toDataURL('image/png'));
const out = resolve(opt('out', 'card.png'));
writeFileSync(out, Buffer.from(dataUrl.split(',')[1], 'base64'));
await browser.close();
console.log('wrote', out);
