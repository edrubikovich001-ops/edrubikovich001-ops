// Preloaded before hayeren-v9-proxy.js.
// Hardens Armenia media, makes article images topic-specific and adds a clear
// pronunciation label to the translator without changing course/progress data.
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
  khachkar: 'Armenian Khatchkar.jpg',
  kochari: 'Kochari - Armenian folk dance.png'
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
        'User-Agent': 'Hayeren/10 educational Telegram Mini App',
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

const clientPolish = `<style id="hayeren-v10-polish">
.hayeren-sound-label{font-size:10px;font-weight:800;color:#7a7068;margin:9px 0 4px;letter-spacing:.01em}
.hayeren-photo-credit{font-size:9px;color:#8b7c70;margin:5px 14px 12px;line-height:1.25}
</style><script id="hayeren-v10-polish-runtime">(()=>{
 const pick=t=>{t=String(t||'').toLowerCase();if(/эребун|эрибун|урарт/.test(t))return'/media/erebuni';if(/алфавит|маштоц|письмен/.test(t))return'/media/alphabet';if(/дудук/.test(t))return'/media/duduk';if(/лаваш|хлеб|тонир/.test(t))return'/media/lavash';if(/хачкар|крест-кам|крест кам/.test(t))return'/media/khachkar';if(/кочари|танец|танц/.test(t))return'/media/kochari';if(/севан|озер|природ/.test(t))return'/media/sevan';if(/гегард|монастыр|эчмиадзин|звартноц|архитект/.test(t))return'/media/geghard';if(/ереван|столиц|площад/.test(t))return'/media/yerevan';return'/media/ararat'};
 function fixImage(img,text){if(!img)return;const src=pick(text);if(img.getAttribute('src')!==src)img.setAttribute('src',src);img.onerror=()=>{img.onerror=null;img.src='/media/ararat'}}
 function apply(){
   document.querySelectorAll('.article-card').forEach(card=>{const img=card.querySelector('.v10-photo,.v7-photo');fixImage(img,card.textContent);if(img&&!card.querySelector('.hayeren-photo-credit')){const n=document.createElement('div');n.className='hayeren-photo-credit';n.textContent='Фото: Wikimedia Commons';img.insertAdjacentElement('afterend',n)}});
   const detail=document.querySelector('.article-screen');if(detail)fixImage(detail.querySelector('.article-detail-photo'),detail.textContent);
   const box=document.querySelector('.translation-result');if(box){const snd=box.querySelector('.translation-sound');if(snd&&String(snd.textContent||'').trim()&&!box.querySelector('.hayeren-sound-label')){const l=document.createElement('div');l.className='hayeren-sound-label';l.textContent='Произношение русскими буквами';snd.parentNode&&snd.parentNode.insertBefore(l,snd)}}
 }
 new MutationObserver(()=>setTimeout(apply,0)).observe(document.documentElement,{subtree:true,childList:true});document.addEventListener('DOMContentLoaded',apply);setTimeout(apply,250);setTimeout(apply,1000);
})();</script>`;

function injectHtml(chunk, res) {
  try {
    const type = String(res.getHeader('content-type') || '').toLowerCase();
    if (!type.includes('text/html') || chunk == null) return chunk;
    const isBuffer = Buffer.isBuffer(chunk);
    let text = isBuffer ? chunk.toString('utf8') : String(chunk);
    if (text.includes('hayeren-v10-polish-runtime')) return chunk;
    text = text.includes('</body>') ? text.replace('</body>', clientPolish + '</body>') : text + clientPolish;
    res.removeHeader('content-length');
    return isBuffer ? Buffer.from(text) : text;
  } catch {
    return chunk;
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
      if (req.method === 'GET' && !url.pathname.startsWith('/api/') && !url.pathname.startsWith('/health') && !url.pathname.startsWith('/sw.js') && !url.pathname.startsWith('/manifest')) {
        const nativeEnd = res.end.bind(res);
        res.end = function patchedEnd(chunk, encoding, callback) {
          const next = injectHtml(chunk, res);
          return nativeEnd(next, encoding, callback);
        };
      }
    } catch (error) {
      console.error('HAYEREN_POLISH_ROUTER', error && error.message);
    }
    return listener.call(this, req, res);
  };
}

http.createServer = function patchedCreateServer(options, listener) {
  if (typeof options === 'function' || options == null) return nativeCreateServer(wrapListener(options));
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
  console.log('ARMENIA_MEDIA_SELFTEST ' + JSON.stringify({ ok: results.every((item) => item.ok), results }));
}

async function probeTranslatorProvider() {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 8000);
  try {
    const url = new URL('https://translate.googleapis.com/translate_a/single');
    url.searchParams.set('client', 'gtx');
    url.searchParams.set('sl', 'ru');
    url.searchParams.set('tl', 'hy');
    url.searchParams.set('dt', 't');
    url.searchParams.set('q', 'добрый день');
    const response = await fetch(url, { signal: controller.signal, headers: { 'User-Agent': 'Hayeren/10 provider self-test' } });
    const data = response.ok ? await response.json() : null;
    const translated = Array.isArray(data?.[0]) ? data[0].map((x) => x?.[0] || '').join('').trim() : '';
    const ok = response.ok && /[Ա-Ֆա-ֆև]/.test(translated);
    console.log('TRANSLATOR_PROVIDER_SELFTEST ' + JSON.stringify({ ok, status: response.status, sample: translated.slice(0, 80) }));
  } catch (error) {
    console.error('TRANSLATOR_PROVIDER_SELFTEST ' + JSON.stringify({ ok: false, error: error && error.message }));
  } finally {
    clearTimeout(timer);
  }
}

setTimeout(() => probeMedia().catch((error) => console.error('ARMENIA_MEDIA_SELFTEST_ERROR', error && error.message)), 800).unref();
setTimeout(() => probeTranslatorProvider().catch(() => {}), 1200).unref();
