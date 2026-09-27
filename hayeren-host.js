const http = require('http');
const zlib = require('zlib');

function getHtml() {
  try {
    const packed = [process.env.H1, process.env.H2, process.env.H3, process.env.H4].filter(Boolean).join('');
    if (!packed) throw new Error('Hayeren payload is not configured');
    return zlib.gunzipSync(Buffer.from(packed, 'base64')).toString('utf8');
  } catch (error) {
    console.error('Hayeren payload error:', error.message);
    return '<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Hayeren</title></head><body><main style="font-family:-apple-system,sans-serif;padding:32px"><h1>Hayeren обновляется</h1><p>Попробуйте открыть приложение через несколько секунд.</p></main></body></html>';
  }
}

const manifest = JSON.stringify({
  name: 'Hayeren — Армянский с нуля',
  short_name: 'Hayeren',
  start_url: '/',
  display: 'standalone',
  background_color: '#f7f1e9',
  theme_color: '#f7f1e9',
  lang: 'ru'
});

const sw = "const CACHE='hayeren-v6';self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(['/']))));self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));self.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;e.respondWith(fetch(e.request).then(r=>{const copy=r.clone();caches.open(CACHE).then(c=>c.put(e.request,copy)).catch(()=>{});return r}).catch(()=>caches.match(e.request).then(r=>r||caches.match('/'))))});";

http.createServer((req, res) => {
  if (req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
    return res.end(JSON.stringify({ ok: true, app: 'Hayeren', version: 6 }));
  }
  if (req.url === '/manifest.webmanifest') {
    res.writeHead(200, { 'Content-Type': 'application/manifest+json; charset=utf-8', 'Cache-Control': 'public, max-age=3600' });
    return res.end(manifest);
  }
  if (req.url === '/sw.js') {
    res.writeHead(200, { 'Content-Type': 'application/javascript; charset=utf-8', 'Cache-Control': 'no-cache', 'Service-Worker-Allowed': '/' });
    return res.end(sw);
  }
  res.writeHead(200, {
    'Content-Type': 'text/html; charset=utf-8',
    'Cache-Control': 'no-store',
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'strict-origin-when-cross-origin'
  });
  res.end(getHtml());
}).listen(process.env.PORT || 10000, '0.0.0.0', () => console.log('Hayeren v6 host ready'));
