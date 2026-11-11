// Judge harness: serve a dist/, upload photos, wait, orbit, screenshot, export.
// usage: node run.mjs <distDir> <outDir> <order: a|b> <photo1> <photo2> ...
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import puppeteer from 'puppeteer-core';

const [distDir, outDir, label, ...photos] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
const log = [];
const L = (...a) => { const s = a.join(' '); log.push(s); console.log(s); };

const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.wasm': 'application/wasm', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png' };
const server = http.createServer((req, res) => {
  let p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  if (p.endsWith('/')) p += 'index.html';
  const f = path.join(distDir, p);
  if (!f.startsWith(path.resolve(distDir)) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end('nf'); }
  res.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream', 'Cross-Origin-Opener-Policy': 'same-origin', 'Cross-Origin-Embedder-Policy': 'credentialless' });
  fs.createReadStream(f).pipe(res);
});
await new Promise(r => server.listen(0, r));
const url = `http://localhost:${server.address().port}/`;

const browser = await puppeteer.launch({
  executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  headless: 'new',
  args: ['--use-angle=metal', '--enable-gpu', '--ignore-gpu-blocklist', '--enable-unsafe-webgpu', '--enable-features=Vulkan,WebGPU', '--window-size=1400,900'],
  defaultViewport: { width: 1400, height: 900 },
});
const page = await browser.newPage();
page.on('console', m => { if (['error', 'warning'].includes(m.type())) L('[console.' + m.type() + ']', m.text().slice(0, 300)); });
page.on('pageerror', e => L('[pageerror]', String(e).slice(0, 300)));
const cdp = await page.createCDPSession();
const dl = path.resolve(outDir, 'downloads-' + label); fs.mkdirSync(dl, { recursive: true });
await cdp.send('Browser.setDownloadBehavior', { behavior: 'allow', downloadPath: dl });

const t0 = Date.now();
await page.goto(url, { waitUntil: 'networkidle2', timeout: 60000 }).catch(e => L('[goto]', e.message));
await page.screenshot({ path: `${outDir}/${label}-0-load.png` });
const gpu = await page.evaluate(async () => ({ webgpu: !!navigator.gpu && !!(await navigator.gpu.requestAdapter().catch(() => null)), webgl2: !!document.createElement('canvas').getContext('webgl2') }));
L('[gpu]', JSON.stringify(gpu));

const input = await page.$('input[type=file]');
if (!input) { L('[fatal] no file input'); } else {
  await input.uploadFile(...photos);
  L('[upload]', photos.map(p => path.basename(p)).join(','));
  await new Promise(r => setTimeout(r, 1500));
  // click an obvious start button if present
  const clicked = await page.evaluate(() => {
    const bs = [...document.querySelectorAll('button')].filter(b => !b.disabled && b.offsetParent !== null);
    const b = bs.find(b => /reconstruct|start|build|run|process|generate|go\b/i.test(b.textContent));
    if (b) { b.click(); return b.textContent.trim().slice(0, 60); } return null;
  });
  L('[start-button]', clicked);
}

// poll until terminal state or timeout
const deadline = Date.now() + 300000;
let last = '', stable = 0, n = 0;
while (Date.now() < deadline) {
  await new Promise(r => setTimeout(r, 5000));
  const txt = await page.evaluate(() => document.body.innerText.replace(/\s+/g, ' ').slice(0, 4000));
  const exportReady = await page.evaluate(() => [...document.querySelectorAll('button,a')].some(b => /export|\.ply|download/i.test(b.textContent) && !b.disabled));
  n++;
  if (n % 6 === 0) await page.screenshot({ path: `${outDir}/${label}-poll-${n}.png` });
  if (txt === last) stable++; else stable = 0;
  last = txt;
  const terminal = /error|failed|no visible primitives|context lost/i.test(txt) && stable >= 1;
  if ((exportReady && stable >= 2) || terminal || stable >= 8) { L('[poll-end] after', ((Date.now() - t0) / 1000).toFixed(0) + 's', 'exportReady=' + exportReady, 'stable=' + stable); break; }
}
L('[elapsed]', ((Date.now() - t0) / 1000).toFixed(0) + 's');
fs.writeFileSync(`${outDir}/${label}-text.txt`, last);
await page.screenshot({ path: `${outDir}/${label}-1-result.png` });

// orbit: find largest canvas
const box = await page.evaluate(() => {
  const cs = [...document.querySelectorAll('canvas')].map(c => c.getBoundingClientRect()).filter(r => r.width > 100);
  cs.sort((a, b) => b.width * b.height - a.width * a.height);
  const r = cs[0]; return r ? { x: r.x, y: r.y, w: r.width, h: r.height } : null;
});
if (box) {
  const cx = box.x + box.w / 2, cy = box.y + box.h / 2;
  const drag = async (dx, dy, button = 'left') => { await page.mouse.move(cx, cy); await page.mouse.down({ button }); for (let i = 1; i <= 10; i++) await page.mouse.move(cx + dx * i / 10, cy + dy * i / 10); await page.mouse.up({ button }); await new Promise(r => setTimeout(r, 800)); };
  await drag(220, 0); await page.screenshot({ path: `${outDir}/${label}-2-orbitR.png` });
  await drag(-440, 60); await page.screenshot({ path: `${outDir}/${label}-3-orbitL.png` });
  await drag(220, -60);
  await page.mouse.move(cx, cy); await page.mouse.wheel({ deltaY: -400 }); await new Promise(r => setTimeout(r, 800));
  await page.screenshot({ path: `${outDir}/${label}-4-zoom.png` });
  await drag(-120, 0, 'right'); await page.screenshot({ path: `${outDir}/${label}-5-pan.png` });
} else L('[orbit] no canvas');

// export
const ex = await page.evaluate(() => { const b = [...document.querySelectorAll('button,a')].find(b => /export|\.ply/i.test(b.textContent) && !b.disabled); if (b) { b.click(); return b.textContent.trim(); } return null; });
L('[export-click]', ex);
await new Promise(r => setTimeout(r, 4000));
L('[downloads]', fs.readdirSync(dl).join(','));
fs.writeFileSync(`${outDir}/${label}-log.txt`, log.join('\n'));
await browser.close(); server.close();
