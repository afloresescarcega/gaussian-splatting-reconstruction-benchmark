// v5 judge harness: serve a dist/, upload photos, wait, capture panel + console, orbit, export .ply + cameras.json.
// usage: node judge-harness-v5.mjs <distDir> <outDir> <label> <photo1> <photo2> ...
// Needs puppeteer-core and Google Chrome. Writes <label>-*.png, <label>-text.txt, <label>-log.txt, <label>-summary.json, downloads-<label>/.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import puppeteer from 'puppeteer-core';

const [distDir, outDir, label, ...photos] = process.argv.slice(2);
const WAIT_MS = +(process.env.WAIT_MS || 600000);
fs.mkdirSync(outDir, { recursive: true });
const log = [];
const L = (...a) => { const s = a.join(' '); log.push(s); console.log(label, s); };
const sleep = ms => new Promise(r => setTimeout(r, ms));

const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.wasm': 'application/wasm', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.onnx': 'application/octet-stream' };
const root = path.resolve(distDir);
const server = http.createServer((req, res) => {
  let p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  if (p.endsWith('/')) p += 'index.html';
  const f = path.join(root, p);
  if (!f.startsWith(root) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end('nf'); }
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
  protocolTimeout: 900000,
});
const page = await browser.newPage();
const consoleErrors = [];
page.on('console', m => { if (m.type() === 'error') { consoleErrors.push(m.text().slice(0, 300)); L('[console.error]', m.text().slice(0, 300)); } });
page.on('pageerror', e => { consoleErrors.push(String(e).slice(0, 300)); L('[pageerror]', String(e).slice(0, 300)); });
const cdp = await page.createCDPSession();
const dl = path.resolve(outDir, 'downloads-' + label); fs.mkdirSync(dl, { recursive: true });
await cdp.send('Browser.setDownloadBehavior', { behavior: 'allow', downloadPath: dl });

const bodyText = () => page.evaluate(() => {
  document.querySelectorAll('details').forEach(d => d.open = true);
  return document.body.innerText;
});
const findButton = (reSrc, notSrc) => page.evaluate((reSrc, notSrc) => {
  const re = new RegExp(reSrc, 'i'), not = notSrc ? new RegExp(notSrc, 'i') : null;
  const els = [...document.querySelectorAll('button,a,[role=button],input[type=button]')].filter(b => b.offsetParent !== null || b.getClientRects().length);
  const b = els.find(b => { const t = (b.textContent || b.value || b.title || b.getAttribute('aria-label') || '').trim(); return re.test(t) && !(not && not.test(t)); });
  return b ? { text: (b.textContent || b.value || '').trim().slice(0, 60), disabled: !!b.disabled || b.getAttribute('aria-disabled') === 'true' } : null;
}, reSrc, notSrc);
const clickButton = (reSrc, notSrc) => page.evaluate((reSrc, notSrc) => {
  const re = new RegExp(reSrc, 'i'), not = notSrc ? new RegExp(notSrc, 'i') : null;
  const els = [...document.querySelectorAll('button,a,[role=button],input[type=button]')];
  const b = els.find(b => { const t = (b.textContent || b.value || b.title || b.getAttribute('aria-label') || '').trim(); return re.test(t) && !(not && not.test(t)) && !b.disabled; });
  if (b) { b.click(); return (b.textContent || b.value || '').trim().slice(0, 60); } return null;
}, reSrc, notSrc);
const PLY = '(export|download|save).*\\.?ply|\\.ply', CAM = 'camera';

const t0 = Date.now();
await page.goto(url, { waitUntil: 'networkidle2', timeout: 90000 }).catch(e => L('[goto]', e.message));
await page.screenshot({ path: `${outDir}/${label}-0-load.png` });
const gpu = await page.evaluate(async () => ({ webgpu: !!navigator.gpu && !!(await navigator.gpu.requestAdapter().catch(() => null)), webgl2: !!document.createElement('canvas').getContext('webgl2') }));
L('[gpu]', JSON.stringify(gpu));

const summary = { label, photos: photos.map(p => path.basename(p)), gpu };
const input = await page.$('input[type=file]');
if (!input) { L('[fatal] no file input'); summary.fatal = 'no file input'; } else {
  await input.uploadFile(...photos);
  L('[upload]', summary.photos.join(','));
  await sleep(2500);
  const clicked = await clickButton('reconstruct|start|run|process|generate|build|go\\b|begin|splat');
  L('[start-button]', clicked); summary.startButton = clicked;
}

let last = '', stable = 0, n = 0, endReason = 'timeout';
const deadline = Date.now() + WAIT_MS;
while (!summary.fatal && Date.now() < deadline) {
  await sleep(5000);
  const txt = await bodyText().catch(() => last);
  const ply = await findButton(PLY, CAM), cam = await findButton(CAM, 'orbit|reset|view');
  n++;
  if (n % 12 === 0) await page.screenshot({ path: `${outDir}/${label}-poll-${n}.png` });
  stable = txt === last ? stable + 1 : 0; last = txt;
  const ready = ply && !ply.disabled && (!cam || !cam.disabled);
  const terminal = /(error|failed|no visible primitives|context lost)/i.test(txt.slice(0, 3000)) && stable >= 2 && !/progress|running|optimi[sz]ing|step \d+/i.test(txt.slice(0, 400));
  if (ready && stable >= 3) { endReason = 'export-ready+stable'; break; }
  if (terminal) { endReason = 'terminal-error-text'; break; }
  if (stable >= 24) { endReason = 'stable-120s'; break; }
}
summary.elapsedS = Math.round((Date.now() - t0) / 1000); summary.endReason = endReason;
L('[poll-end]', endReason, summary.elapsedS + 's');
fs.writeFileSync(`${outDir}/${label}-text.txt`, last);
await page.screenshot({ path: `${outDir}/${label}-1-result.png` });

// pixel check on largest canvas (our own, independent of the app's)
const box = await page.evaluate(() => {
  const cs = [...document.querySelectorAll('canvas')].map(c => c.getBoundingClientRect()).filter(r => r.width > 100 && r.height > 100);
  cs.sort((a, b) => b.width * b.height - a.width * a.height);
  const r = cs[0]; return r ? { x: r.x, y: r.y, w: r.width, h: r.height } : null;
});
summary.canvas = box;
if (box) {
  const cx = box.x + box.w / 2, cy = box.y + box.h / 2;
  const drag = async (dx, dy, button = 'left') => { await page.mouse.move(cx, cy); await page.mouse.down({ button }); for (let i = 1; i <= 12; i++) { await page.mouse.move(cx + dx * i / 12, cy + dy * i / 12); await sleep(16); } await page.mouse.up({ button }); await sleep(900); };
  await drag(260, 0); await page.screenshot({ path: `${outDir}/${label}-2-orbitR.png` });
  await drag(-520, 80); await page.screenshot({ path: `${outDir}/${label}-3-orbitL.png` });
  await drag(260, -80);
  await page.mouse.move(cx, cy); await page.mouse.wheel({ deltaY: -400 }); await sleep(900);
  await page.screenshot({ path: `${outDir}/${label}-4-zoom.png` });
  await drag(-140, 0, 'right'); await page.screenshot({ path: `${outDir}/${label}-5-pan.png` });
} else L('[orbit] no canvas');

summary.exportPly = await clickButton(PLY, CAM); L('[export-ply]', summary.exportPly); await sleep(5000);
summary.exportCam = await clickButton(CAM, 'orbit|reset|view|fit'); L('[export-cam]', summary.exportCam); await sleep(4000);
summary.downloads = fs.readdirSync(dl).map(f => ({ f, bytes: fs.statSync(path.join(dl, f)).size }));
L('[downloads]', JSON.stringify(summary.downloads));
summary.consoleErrors = consoleErrors.slice(0, 40);
fs.writeFileSync(`${outDir}/${label}-summary.json`, JSON.stringify(summary, null, 2));
fs.writeFileSync(`${outDir}/${label}-log.txt`, log.join('\n'));
await browser.close(); server.close();
