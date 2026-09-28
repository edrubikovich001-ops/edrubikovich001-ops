// Preloaded before hayeren-v9-proxy.js.
// Serves Armenia article images through the app itself using Wikimedia Commons
// sources, with timeout, memory cache and an always-visible local SVG fallback.
const http = require('http');
const nativeCreateServer = http.createServer.bind(http);

const FILES = {
  ararat: 'View of Mount Ararat from Yerevan.jpg',
  yerevan: 'Yerevan, Republic Square, Armenia.jpg',
  geghard: 'Geghard Monastery, Armenia.jpg',
  sevan: 'Lake Sevan with Sevanavank.jpg',
  erebuni: 'Erebuni fortress in Armenia.jpg',
  alphabet: 'Armenian Alphabet Monument.JPG',
  duduk: 'ArmenianDuduk-image.jpg',
  lavash: 'Lavash in a tonir oven Armenia 2026.jpg',
  khachkar: 'Armenian Khatchkar.jpg'
};

const cache = new Map();
const fallback = Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 675"><defs><linearGradient id="g" x1="0" x2="1"><stop stop-color="#6f4037"/><stop offset="1" stop-color="#bd684e"/></linearGradient></defs><rect width="1200" height="675" fill="url(#g)"/><circle cx="1010" cy="130" r="78" fill="#efb56f" opacity=".9"/><path d="M0 675 330 205l155 190 118-139 352 419z" fill="#4c2d28"/><text x="64" y="590" fill="white" font-size="54" font-family="system-ui">Հայաստան · Armenia</text></svg>`);

function commonsUrl(name) {
  return `https://commons.wikimedia.org/wiki/Special:Redirect/file/${encodeURIComponent(name)}?width=1280`;
}

async function fetchImage(name) {
  const filename = FILES[name];
  if (!filename) throw new Error('unknown media');
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 9000);
  try {
    const response = await fetch(commonsUrl(filename), {
      redirect: 'follow',
      signal: controller.signal,
      headers: {
        'User-Agent': 'Hayeren/9.3 educational Telegram Mini App',
        'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8'
      }
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const type = response.headers.get('content-type') || '';
    if (!type.startsWith('image/')) throw new Error(`bad content-type ${type}`);
    const body = Buffer.from(await response.arrayBuffer());
    if (body.length < 4000) throw new Error(`image too small ${body.length}`);
    return { body, type, filename };
  } finally {
    clearTimeout(timer);
  }
}

async function serveMedia(name, res) {
  if (cache.has(name)) {
    const item = cache.get(name);
    res.writeHead(200, {
      'Content-Type': item.type,
      'Content-Length': item.body.length,
      'Cache-Control': 'public,max-age=86400',
      'Access-Control-Allow-Origin': '*',
      'X-Hayeren-Asset': name,
      'X-Hayeren-Asset-Source': 'wikimedia-cache'
    });
    return res.end(item.body);
  }
  try {
    const item = await fetchImage(name);
    cache.set(name, item);
    res.writeHead(200, {
      'Content-Type': item.type,
      'Content-Length': item.body.length,
      'Cache-Control': 'public,max-age=86400',
      'Access-Control-Allow-Origin': '*',
      'X-Hayeren-Asset': name,
      'X-Hayeren-Asset-Source': 'wikimedia-commons'
    });
    return res.end(item.body);
  } catch (error) {
    console.error(`ARMENIA_MEDIA_FALLBACK name=${name} reason=${error && error.message}`);
    res.writeHead(200, {
      'Content-Type': 'image/svg+xml; charset=utf-8',
      'Content-Length': fallback.length,
      'Cache-Control': 'no-store',
      'Access-Control-Allow-Origin': '*',
      'X-Hayeren-Asset': name,
      'X-Hayeren-Asset-Fallback': '1'
    });
    return res.end(fallback);
  }
}

function wrapListener(listener) {
  if (typeof listener !== 'function') return listener;
  return async function hayerenAssetsListener(req, res) {
    try {
      const url = new URL(req.url || '/', 'http://localhost');
      if ((req.method === 'GET' || req.method === 'HEAD') && url.pathname.startsWith('/media/')) {
        const name = decodeURIComponent(url.pathname.slice('/media/'.length)).split('/')[0];
        return await serveMedia(name, res);
      }
    } catch (error) {
      console.error('ARMENIA_MEDIA_ROUTER', error && error.message);
    }
    return listener.call(this, req, res);
  };
}

http.createServer = function patchedCreateServer(options, listener) {
  if (typeof options === 'function' || options == null) {
    return nativeCreateServer(wrapListener(options));
  }
  return nativeCreateServer(options, wrapListener(listener));
};

async function probeMedia() {
  const results = [];
  for (const name of Object.keys(FILES)) {
    try {
      const item = await fetchImage(name);
      results.push({ name, ok: true, bytes: item.body.length, type: item.type });
      if (!cache.has(name)) cache.set(name, item);
    } catch (error) {
      results.push({ name, ok: false, error: error && error.message });
    }
  }
  const ok = results.every((item) => item.ok);
  console.log('ARMENIA_MEDIA_SELFTEST ' + JSON.stringify({ ok, results }));
}

setTimeout(() => probeMedia().catch((error) => console.error('ARMENIA_MEDIA_SELFTEST_ERROR', error && error.message)), 800).unref();
