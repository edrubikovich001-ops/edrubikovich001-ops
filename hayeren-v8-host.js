const http = require('http');

const VERSION = '9.0';
const UPSTREAM = 'https://hayeren-v6-live.onrender.com';
let html = '';
let lastLoad = null;
let selfTest = { ok: false, at: null, details: [] };

function norm(s) {
  return String(s || '').toLowerCase().replace(/[?!.,;:()«»“”"']/g, '').replace(/\s+/g, ' ').trim();
}

const curated = {
  'я люблю тебя': ['Ես սիրում եմ քեզ', 'Ес сирум ем кез', 'Я люблю тебя'],
  'люблю тебя': ['Ես սիրում եմ քեզ', 'Ес сирум ем кез', 'Я люблю тебя'],
  'я тебя люблю': ['Ես քեզ սիրում եմ', 'Ес кез сирум ем', 'Я тебя люблю'],
  'привет': ['Բարև', 'Барев', 'Привет'],
  'здравствуйте': ['Բարև ձեզ', 'Барев дзез', 'Здравствуйте'],
  'спасибо': ['Շնորհակալություն', 'Шноракалутюн', 'Спасибо'],
  'большое спасибо': ['Շատ շնորհակալություն', 'Шат шноракалутюн', 'Большое спасибо'],
  'пожалуйста': ['Խնդրեմ', 'Хндрем', 'Пожалуйста'],
  'извините': ['Ներեցեք', 'Нерецек', 'Извините'],
  'как дела': ['Ինչպե՞ս ես', 'Инчпес ес', 'Как дела?'],
  'как ты': ['Ինչպե՞ս ես', 'Инчпес ес', 'Как ты?'],
  'доброе утро': ['Բարի լույս', 'Бари луйс', 'Доброе утро'],
  'добрый вечер': ['Բարի երեկո', 'Бари ереко', 'Добрый вечер'],
  'спокойной ночи': ['Բարի գիշեր', 'Бари гишер', 'Спокойной ночи'],
  'до свидания': ['Ցտեսություն', 'Цтесутюн', 'До свидания'],
  'да': ['Այո', 'Айо', 'Да'],
  'нет': ['Ոչ', 'Воч', 'Нет'],
  'я не понимаю': ['Ես չեմ հասկանում', 'Ес чем хасканум', 'Я не понимаю'],
  'я понимаю': ['Ես հասկանում եմ', 'Ес хасканум ем', 'Я понимаю'],
  'повторите пожалуйста': ['Կրկնեք, խնդրում եմ', 'Кркнек, хндрум ем', 'Повторите, пожалуйста'],
  'говорите медленнее пожалуйста': ['Ավելի դանդաղ խոսեք, խնդրում եմ', 'Авели дандал хосек, хндрум ем', 'Говорите медленнее, пожалуйста'],
  'как вас зовут': ['Ի՞նչ է ձեր անունը', 'Инч э дзер ануны', 'Как вас зовут?'],
  'меня зовут эдгар': ['Իմ անունը Էդգար է', 'Им ануны Эдгар э', 'Меня зовут Эдгар'],
  'где туалет': ['Որտե՞ղ է զուգարանը', 'Вортех э зугараны', 'Где туалет?'],
  'сколько стоит': ['Որքա՞ն արժե', 'Воркан арже', 'Сколько стоит?'],
  'мне нужно такси': ['Ինձ տաքսի է պետք', 'Индз такси э петк', 'Мне нужно такси'],
  'мне нужен врач': ['Ինձ բժիշկ է պետք', 'Индз бжишк э петк', 'Мне нужен врач'],
  'помогите пожалуйста': ['Օգնեք, խնդրում եմ', 'Огнек, хндрум ем', 'Помогите, пожалуйста'],
  'где находится центр': ['Որտե՞ղ է կենտրոնը', 'Вортех э кентроны', 'Где находится центр?'],
  'я из казахстана': ['Ես Ղազախստանից եմ', 'Ес Газахстаниц ем', 'Я из Казахстана'],
  'я из россии': ['Ես Ռուսաստանից եմ', 'Ес Русастаниц ем', 'Я из России'],
  'вы говорите по русски': ['Դուք ռուսերեն խոսո՞ւմ եք', 'Дук русерен хосум ек', 'Вы говорите по-русски?'],
  'я хочу кофе': ['Ես սուրճ եմ ուզում', 'Ес сурч ем узум', 'Я хочу кофе'],
  'я хочу воды': ['Ես ջուր եմ ուզում', 'Ес джур ем узум', 'Я хочу воды'],
  'где гостиница': ['Որտե՞ղ է հյուրանոցը', 'Вортех э хюраноцы', 'Где гостиница?'],
  'армения': ['Հայաստան', 'Айастан', 'Армения'],
  'ереван': ['Երևան', 'Ереван', 'Ереван']
};
const reverse = {};
for (const v of Object.values(curated)) reverse[norm(v[0])] = v;

const map = {'Ա':'А','ա':'а','Բ':'Б','բ':'б','Գ':'Г','գ':'г','Դ':'Д','դ':'д','Ե':'Е','ե':'е','Զ':'З','զ':'з','Է':'Э','է':'э','Ը':'Ы','ը':'ы','Թ':'Т','թ':'т','Ժ':'Ж','ժ':'ж','Ի':'И','ի':'и','Լ':'Л','լ':'л','Խ':'Х','խ':'х','Ծ':'Ц','ծ':'ц','Կ':'К','կ':'к','Հ':'Х','հ':'х','Ձ':'Дз','ձ':'дз','Ղ':'Х','ղ':'х','Ճ':'Ч','ճ':'ч','Մ':'М','մ':'м','Յ':'Й','յ':'й','Ն':'Н','ն':'н','Շ':'Ш','շ':'ш','Ո':'О','ո':'о','Չ':'Ч','չ':'ч','Պ':'П','պ':'п','Ջ':'Дж','ջ':'дж','Ռ':'Р','ռ':'р','Ս':'С','ս':'с','Վ':'В','վ':'в','Տ':'Т','տ':'т','Ր':'Р','ր':'р','Ց':'Ц','ց':'ц','Ւ':'В','ւ':'в','Փ':'П','փ':'п','Ք':'К','ք':'к','Օ':'О','օ':'о','Ֆ':'Ф','ֆ':'ф'};
function sound(x) {
  let s = String(x).replace(/Ու/g,'У').replace(/ու/g,'у').replace(/Եվ/g,'Ев').replace(/և/g,'ев');
  return [...s].map(c => map[c] ?? c).join('').replace(/\s+/g,' ').trim();
}
function suspicious(out, source, target) {
  const n = norm(out);
  if (!out || out.length > 1000) return true;
  if (source === 'ru' && target === 'hy' && !/[Ա-Ֆա-ֆև]/.test(out)) return true;
  if (source === 'hy' && target === 'ru' && /[Ա-Ֆա-ֆև]/.test(out) && !/[А-Яа-яЁё]/.test(out)) return true;
  if (['չատլախ','чатлах'].some(x => n.includes(x))) return true;
  return false;
}
async function google(text, source, target) {
  const u = new URL('https://translate.googleapis.com/translate_a/single');
  u.searchParams.set('client','gtx'); u.searchParams.set('sl',source); u.searchParams.set('tl',target); u.searchParams.set('dt','t'); u.searchParams.set('q',text);
  const r = await fetch(u, { headers: { 'Accept':'application/json', 'User-Agent':`Hayeren/${VERSION}` } });
  if (!r.ok) throw new Error('google ' + r.status);
  const d = await r.json();
  const out = Array.isArray(d?.[0]) ? d[0].map(x => x?.[0] || '').join('').trim() : '';
  if (!out) throw new Error('google empty');
  return out;
}
async function memory(text, source, target) {
  const u = new URL('https://api.mymemory.translated.net/get');
  u.searchParams.set('q',text); u.searchParams.set('langpair',`${source}|${target}`);
  const r = await fetch(u, { headers: { 'Accept':'application/json', 'User-Agent':`Hayeren/${VERSION}` } });
  if (!r.ok) throw new Error('memory ' + r.status);
  const d = await r.json();
  const out = String(d?.responseData?.translatedText || '').trim();
  if (!out) throw new Error('memory empty');
  return out;
}
async function translate(text, source, target) {
  const exact = source === 'ru' ? curated[norm(text)] : reverse[norm(text)];
  if (exact) return { translated: target === 'hy' ? exact[0] : exact[2], ruSound: exact[1], provider:'Проверено Hayeren', verified:true };
  let out = '', provider = 'Google Translate';
  try { out = await google(text,source,target); }
  catch (g) {
    console.warn('google translator fallback:', g.message);
    out = await memory(text,source,target); provider = 'Резервный перевод';
  }
  if (suspicious(out,source,target)) throw new Error('Сомнительный результат перевода отклонён');
  return { translated:out, ruSound: target === 'hy' ? sound(out) : sound(text), provider, verified:false };
}

const bridge = `<script id="hayeren-final-bridge">(function(){
  window.__HAYEREN_VERSION__='${VERSION}';
  if('caches' in window){caches.keys().then(function(keys){keys.filter(function(k){return /hayeren/i.test(k)}).forEach(function(k){caches.delete(k)})}).catch(function(){})}
  if('serviceWorker' in navigator){navigator.serviceWorker.getRegistrations().then(function(rs){rs.forEach(function(r){r.update().catch(function(){})})}).catch(function(){})}
  var nativeFetch=window.fetch.bind(window);
  var meta={};
  function endpoint(url){return /translate\.googleapis\.com\/translate_a\/single/.test(url)?'google':(/api\.mymemory\.translated\.net\/get/.test(url)?'memory':'')}
  window.fetch=async function(input,init){
    var url=typeof input==='string'?input:(input&&input.url)||'', kind=endpoint(url);
    if(kind){
      try{
        var u=new URL(url,location.href),q=u.searchParams.get('q')||'',s='ru',t='hy';
        if(kind==='google'){s=(u.searchParams.get('sl')||'ru').slice(0,2);t=(u.searchParams.get('tl')||'hy').slice(0,2)}
        else{var pair=(u.searchParams.get('langpair')||'ru|hy').split('|');s=(pair[0]||'ru').slice(0,2);t=(pair[1]||'hy').slice(0,2)}
        s=s==='hy'?'hy':'ru'; t=t==='ru'?'ru':'hy';
        var r=await nativeFetch('/api/translate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:q,source:s,target:t})});
        var j=await r.json(); if(!r.ok) throw new Error(j.error||'translation failed'); meta=j; window.__hayerenTranslateMeta=j;
        if(kind==='google') return new Response(JSON.stringify([[[j.translated,q,null,null,10]],null,s]),{status:200,headers:{'Content-Type':'application/json'}});
        return new Response(JSON.stringify({responseData:{translatedText:j.translated,match:j.verified?1:.95},matches:[]}),{status:200,headers:{'Content-Type':'application/json'}});
      }catch(e){return new Response(JSON.stringify(kind==='google'?[]:{responseData:{translatedText:''},responseStatus:500}),{status:500,headers:{'Content-Type':'application/json'}})}
    }
    return nativeFetch(input,init)
  };
  function polish(){
    var box=document.querySelector('.translation-result'); if(!box)return;
    var m=window.__hayerenTranslateMeta||meta;
    if(m.ruSound){var snd=box.querySelector('.translation-sound'); if(snd)snd.textContent=m.ruSound}
    var old=box.querySelector('.hayeren-source'); if(old)old.remove();
    if(m.provider){var b=document.createElement('div');b.className='hayeren-source';b.textContent=(m.verified?'✓ ':'')+m.provider;b.style.cssText='margin-top:10px;display:inline-flex;padding:6px 10px;border-radius:999px;background:#f2e8df;color:#74483d;font-size:10px;font-weight:800';box.appendChild(b)}
    if(m.verified){var s=box.querySelector('small');if(s)s.textContent='Проверенная фраза Hayeren.'}
  }
  new MutationObserver(function(){setTimeout(polish,0)}).observe(document.documentElement,{childList:true,subtree:true});
  document.addEventListener('DOMContentLoaded',function(){setTimeout(polish,100)});
})();</script>`;

async function loadUpstream() {
  const r = await fetch(UPSTREAM + '/?source=final-' + VERSION, { headers:{'User-Agent':`Hayeren/${VERSION}`} });
  if (!r.ok) throw new Error('upstream ' + r.status);
  let next = await r.text();
  if (!next.toLowerCase().includes('<!doctype html')) throw new Error('bad upstream html');
  next = next.replace('</head>', bridge + '</head>');
  html = next;
  lastLoad = new Date().toISOString();
  console.log('UPSTREAM_OK bytes=' + Buffer.byteLength(html));
}

async function proxyMedia(req,res) {
  try {
    const r = await fetch(UPSTREAM + req.url, { headers:{'User-Agent':`Hayeren/${VERSION}`}, redirect:'follow' });
    if(!r.ok) throw new Error('media ' + r.status);
    const body = Buffer.from(await r.arrayBuffer());
    res.writeHead(200, {'Content-Type':r.headers.get('content-type')||'image/jpeg','Cache-Control':'public,max-age=21600','Access-Control-Allow-Origin':'*'});
    res.end(body);
  } catch(e) {
    const svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450"><defs><linearGradient id="g"><stop stop-color="#c77959"/><stop offset="1" stop-color="#6f4037"/></linearGradient></defs><rect width="800" height="450" fill="url(#g)"/><circle cx="650" cy="90" r="45" fill="#efb56f"/><path d="M0 450 250 125l110 135 80-95 230 285z" fill="#7d4639"/><text x="42" y="405" fill="#fff" font-size="34" font-family="system-ui">Հայաստան · Armenia</text></svg>';
    res.writeHead(200, {'Content-Type':'image/svg+xml; charset=utf-8','Cache-Control':'public,max-age=600'}); res.end(svg);
  }
}

async function runSelfTest(){
  const details=[];
  try{
    const a=await translate('Я люблю тебя','ru','hy');
    details.push({name:'love',ok:a.translated==='Ես սիրում եմ քեզ',value:a.translated});
    const b=await translate('Привет','ru','hy');
    details.push({name:'hello',ok:b.translated==='Բարև',value:b.translated});
    const c=await translate('Ես սիրում եմ քեզ','hy','ru');
    details.push({name:'reverse',ok:/люблю/i.test(c.translated),value:c.translated});
    selfTest={ok:details.every(x=>x.ok),at:new Date().toISOString(),details};
  }catch(e){selfTest={ok:false,at:new Date().toISOString(),details:[...details,{name:'exception',ok:false,value:e.message}]}}
  console.log('HAYEREN_SELFTEST '+JSON.stringify(selfTest));
}

const manifest = JSON.stringify({name:'Hayeren — Армянский с нуля',short_name:'Hayeren',start_url:'/',display:'standalone',background_color:'#f7f4ee',theme_color:'#f7f4ee',lang:'ru'});
const sw = `self.addEventListener('install',()=>self.skipWaiting());self.addEventListener('activate',e=>e.waitUntil((async()=>{for(const k of await caches.keys())if(/hayeren/i.test(k))await caches.delete(k);await self.clients.claim()})()));`;

const server=http.createServer(async(req,res)=>{
  const u=new URL(req.url,'http://localhost');
  res.setHeader('X-Hayeren-Version',VERSION);
  if(u.pathname==='/health'){
    res.writeHead(200,{'Content-Type':'application/json','Cache-Control':'no-store'});
    return res.end(JSON.stringify({ok:html.length>10000,version:VERSION,upstreamLoaded:html.length>10000,lastLoad,htmlBytes:Buffer.byteLength(html),translatorSelfTest:selfTest}));
  }
  if(u.pathname==='/manifest.webmanifest'){res.writeHead(200,{'Content-Type':'application/manifest+json','Cache-Control':'no-store'});return res.end(manifest)}
  if(u.pathname==='/sw.js'){res.writeHead(200,{'Content-Type':'application/javascript; charset=utf-8','Cache-Control':'no-store'});return res.end(sw)}
  if(u.pathname.startsWith('/media/')) return proxyMedia(req,res);
  if(u.pathname==='/api/translate'){
    const handle=async j=>{
      const text=String(j.text||j.q||'').trim(); if(!text||text.length>1200) throw new Error('Некорректный текст');
      const source=j.source==='hy'?'hy':'ru',target=j.target==='ru'?'ru':'hy';
      if(source===target) throw new Error('Языки должны отличаться');
      return translate(text,source,target);
    };
    try{
      let j={};
      if(req.method==='GET') j={text:u.searchParams.get('text')||u.searchParams.get('q')||'',source:u.searchParams.get('source')||'ru',target:u.searchParams.get('target')||'hy'};
      else if(req.method==='POST') j=await new Promise((resolve,reject)=>{let body='';req.on('data',c=>{body+=c;if(body.length>12000)reject(new Error('too large'))});req.on('end',()=>{try{resolve(JSON.parse(body||'{}'))}catch(e){reject(e)}})});
      else {res.writeHead(405,{'Content-Type':'application/json'});return res.end(JSON.stringify({error:'method not allowed'}))}
      const out=await handle(j); res.writeHead(200,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','Access-Control-Allow-Origin':'*'});return res.end(JSON.stringify(out));
    }catch(e){res.writeHead(422,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'});return res.end(JSON.stringify({error:e.message||'Не удалось получить надёжный перевод'}))}
  }
  res.writeHead(200,{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store,no-cache,must-revalidate,max-age=0','Pragma':'no-cache','Expires':'0','X-Content-Type-Options':'nosniff'});
  res.end(html || '<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><body style="font-family:-apple-system;padding:32px;background:#f7f4ee"><h1>Hayeren запускается…</h1><p>Обновите страницу через несколько секунд.</p></body></html>');
});

(async()=>{
  try{await loadUpstream()}catch(e){console.error('LOAD_UPSTREAM_ERROR',e)}
  server.listen(process.env.PORT||10000,'0.0.0.0',()=>console.log('Hayeren final '+VERSION+' ready'));
  await runSelfTest();
  setInterval(()=>loadUpstream().catch(e=>console.warn('UPSTREAM_REFRESH',e.message)),5*60*1000).unref();
})();
