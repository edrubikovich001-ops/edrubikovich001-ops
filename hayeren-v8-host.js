const http = require('http');

const VERSION = '9.2';
const UPSTREAM = 'https://hayeren-v6-live.onrender.com';
const APP_URL = process.env.APP_URL || 'https://hayeren-v8-live.onrender.com';
let html = '';
let lastLoad = null;
let selfTest = { ok: false, at: null, details: [] };
const cache = new Map();

function norm(s) {
  return String(s || '')
    .toLowerCase()
    .replace(/[?!.,;:()«»“”"'`]/g, '')
    .replace(/[-–—]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

const curated = {
  'я люблю тебя': ['Ես սիրում եմ քեզ', 'Ес сирум ем кез', 'Я люблю тебя'],
  'люблю тебя': ['Ես սիրում եմ քեզ', 'Ес сирум ем кез', 'Я люблю тебя'],
  'я тебя люблю': ['Ես քեզ սիրում եմ', 'Ес кез сирум ем', 'Я тебя люблю'],
  'я очень тебя люблю': ['Ես քեզ շատ եմ սիրում', 'Ес кез шат ем сирум', 'Я очень тебя люблю'],
  'привет': ['Բարև', 'Барев', 'Привет'],
  'здравствуйте': ['Բարև ձեզ', 'Барев дзез', 'Здравствуйте'],
  'доброе утро': ['Բարի լույս', 'Бари луйс', 'Доброе утро'],
  'добрый вечер': ['Բարի երեկո', 'Бари ерэко', 'Добрый вечер'],
  'спокойной ночи': ['Բարի գիշեր', 'Бари гишер', 'Спокойной ночи'],
  'до свидания': ['Ցտեսություն', 'Цтесутюн', 'До свидания'],
  'спасибо': ['Շնորհակալություն', 'Шноракалуцюн', 'Спасибо'],
  'большое спасибо': ['Շատ շնորհակալություն', 'Шат шноракалуцюн', 'Большое спасибо'],
  'пожалуйста': ['Խնդրեմ', 'Хндрем', 'Пожалуйста'],
  'извините': ['Ներեցեք', 'Нерецек', 'Извините'],
  'простите': ['Ներեցեք', 'Нерецек', 'Простите'],
  'да': ['Այո', 'Айо', 'Да'],
  'нет': ['Ոչ', 'Воч', 'Нет'],
  'как дела': ['Ինչպե՞ս ես', 'Инчпес ес?', 'Как дела?'],
  'как вы': ['Ինչպե՞ս եք', 'Инчпес эк?', 'Как вы?'],
  'как ты': ['Ինչպե՞ս ես', 'Инчпес ес?', 'Как ты?'],
  'хорошо': ['Լավ', 'Лав', 'Хорошо'],
  'у меня все хорошо': ['Լավ եմ', 'Лав эм', 'У меня всё хорошо'],
  'я понимаю': ['Ես հասկանում եմ', 'Ес хасканум эм', 'Я понимаю'],
  'я не понимаю': ['Ես չեմ հասկանում', 'Ес чем хасканум', 'Я не понимаю'],
  'повторите пожалуйста': ['Կրկնեք, խնդրում եմ', 'Кркнек, хндрум эм', 'Повторите, пожалуйста'],
  'говорите медленнее пожалуйста': ['Ավելի դանդաղ խոսեք, խնդրում եմ', 'Авели дандал хосек, хндрум эм', 'Говорите медленнее, пожалуйста'],
  'как вас зовут': ['Ի՞նչ է ձեր անունը', 'Инч э дзер ануны?', 'Как вас зовут?'],
  'как тебя зовут': ['Ի՞նչ է քո անունը', 'Инч э ко ануны?', 'Как тебя зовут?'],
  'меня зовут эдгар': ['Իմ անունը Էդգար է', 'Им ануны Эдгар э', 'Меня зовут Эдгар'],
  'где туалет': ['Որտե՞ղ է զուգարանը', 'Вортех э зугараны?', 'Где туалет?'],
  'где находится центр': ['Որտե՞ղ է կենտրոնը', 'Вортех э кентроны?', 'Где находится центр?'],
  'сколько стоит': ['Որքա՞ն արժե', 'Воркан арже?', 'Сколько стоит?'],
  'мне нужно такси': ['Ինձ տաքսի է պետք', 'Индз такси э петк', 'Мне нужно такси'],
  'мне нужен врач': ['Ինձ բժիշկ է պետք', 'Индз бжишк э петк', 'Мне нужен врач'],
  'помогите пожалуйста': ['Օգնեք, խնդրում եմ', 'Огнек, хндрум эм', 'Помогите, пожалуйста'],
  'вы говорите по русски': ['Դուք ռուսերեն խոսո՞ւմ եք', 'Дук русерен хосум эк?', 'Вы говорите по-русски?'],
  'я говорю по русски': ['Ես ռուսերեն եմ խոսում', 'Ес русерен эм хосум', 'Я говорю по-русски'],
  'я из казахстана': ['Ես Ղազախստանից եմ', 'Ес Газахстаниц эм', 'Я из Казахстана'],
  'я из россии': ['Ես Ռուսաստանից եմ', 'Ес Русастаниц эм', 'Я из России'],
  'я хочу кофе': ['Ես սուրճ եմ ուզում', 'Ес сурч эм узум', 'Я хочу кофе'],
  'я хочу воды': ['Ես ջուր եմ ուզում', 'Ес джур эм узум', 'Я хочу воды'],
  'где гостиница': ['Որտե՞ղ է հյուրանոցը', 'Вортех э хюраноцы?', 'Где гостиница?'],
  'где аэропорт': ['Որտե՞ղ է օդանավակայանը', 'Вортех э оданавакаяны?', 'Где аэропорт?'],
  'где метро': ['Որտե՞ղ է մետրոն', 'Вортех э метроны?', 'Где метро?'],
  'армения': ['Հայաստան', 'Айастан', 'Армения'],
  'ереван': ['Երևան', 'Ереван', 'Ереван']
};

const reverse = {};
for (const v of Object.values(curated)) reverse[norm(v[0])] = v;

const charMap = {
  'Ա':'А','ա':'а','Բ':'Б','բ':'б','Գ':'Г','գ':'г','Դ':'Д','դ':'д','Ե':'Е','ե':'е','Զ':'З','զ':'з','Է':'Э','է':'э','Ը':'Ы','ը':'ы',
  'Թ':'Т','թ':'т','Ժ':'Ж','ժ':'ж','Ի':'И','ի':'и','Լ':'Л','լ':'л','Խ':'Х','խ':'х','Ծ':'Ц','ծ':'ц','Կ':'К','կ':'к','Հ':'Х','հ':'х',
  'Ձ':'Дз','ձ':'дз','Ղ':'Гх','ղ':'гх','Ճ':'Ч','ճ':'ч','Մ':'М','մ':'м','Յ':'Й','յ':'й','Ն':'Н','ն':'н','Շ':'Ш','շ':'ш',
  'Ո':'Во','ո':'о','Չ':'Ч','չ':'ч','Պ':'П','պ':'п','Ջ':'Дж','ջ':'дж','Ռ':'Р','ռ':'р','Ս':'С','ս':'с','Վ':'В','վ':'в','Տ':'Т','տ':'т',
  'Ր':'Р','ր':'р','Ց':'Ц','ց':'ц','Ւ':'В','ւ':'в','Փ':'П','փ':'п','Ք':'К','ք':'к','Օ':'О','օ':'о','Ֆ':'Ф','ֆ':'ф'
};

function sound(x) {
  let s = String(x || '')
    .replace(/Ու/g,'У').replace(/ու/g,'у')
    .replace(/Եվ/g,'Ев').replace(/և/g,'ев')
    .replace(/ՈՒ/g,'У');
  s = [...s].map(c => charMap[c] ?? c).join('');
  s = s.replace(/^Во(?=[а-я])/,'Во').replace(/\s+/g,' ').trim();
  return s;
}

function suspicious(out, source, target) {
  const n = norm(out);
  if (!out || out.length > 1600) return true;
  if (['չատլախ','чатлах','undefined','null'].some(x => n.includes(x))) return true;
  if (source === 'ru' && target === 'hy') {
    if (!/[Ա-Ֆա-ֆև]/.test(out)) return true;
    if ((out.match(/[А-Яа-яЁё]/g) || []).length > 3) return true;
  }
  if (source === 'hy' && target === 'ru') {
    if (!/[А-Яа-яЁё]/.test(out)) return true;
    if ((out.match(/[Ա-Ֆա-ֆև]/g) || []).length > 3) return true;
  }
  return false;
}

async function google(text, source, target) {
  const u = new URL('https://translate.googleapis.com/translate_a/single');
  u.searchParams.set('client','gtx');
  u.searchParams.set('sl',source);
  u.searchParams.set('tl',target);
  u.searchParams.set('dt','t');
  u.searchParams.set('q',text);
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 7000);
  try {
    const r = await fetch(u, {
      signal: ctrl.signal,
      headers: {'Accept':'application/json','User-Agent':`Hayeren/${VERSION}`}
    });
    if (!r.ok) throw new Error('translator ' + r.status);
    const d = await r.json();
    const out = Array.isArray(d?.[0]) ? d[0].map(x => x?.[0] || '').join('').trim() : '';
    if (!out) throw new Error('translator empty');
    return out;
  } finally {
    clearTimeout(timer);
  }
}

async function translate(text, source, target) {
  text = String(text || '').trim();
  const exact = source === 'ru' ? curated[norm(text)] : reverse[norm(text)];
  if (exact) {
    return {
      translated: target === 'hy' ? exact[0] : exact[2],
      ruSound: exact[1],
      provider: 'Проверено Hayeren',
      verified: true,
      confidence: 1
    };
  }
  const key = `${source}|${target}|${norm(text)}`;
  if (cache.has(key)) return cache.get(key);
  const out = await google(text, source, target);
  if (suspicious(out, source, target)) throw new Error('Перевод не прошёл проверку качества');
  const result = {
    translated: out,
    ruSound: target === 'hy' ? sound(out) : sound(text),
    provider: 'Google Translate',
    verified: false,
    confidence: 0.9
  };
  cache.set(key, result);
  if (cache.size > 500) cache.delete(cache.keys().next().value);
  return result;
}

const bridge = `<script id="hayeren-translator-bridge">(function(){
  window.__HAYEREN_VERSION__='${VERSION}';
  if('caches' in window){caches.keys().then(function(keys){keys.filter(function(k){return /hayeren/i.test(k)}).forEach(function(k){caches.delete(k)})}).catch(function(){})}
  var nativeFetch=window.fetch.bind(window),meta={};
  function isTranslationUrl(url){return /translate\\.googleapis\\.com\\/translate_a\\/single/.test(url)||/api\\.mymemory\\.translated\\.net\\/get/.test(url)}
  window.fetch=async function(input,init){
    var url=typeof input==='string'?input:(input&&input.url)||'';
    if(isTranslationUrl(url)){
      try{
        var u=new URL(url,location.href),q=u.searchParams.get('q')||'',s='ru',t='hy';
        if(/translate\\.googleapis/.test(url)){s=(u.searchParams.get('sl')||'ru').slice(0,2);t=(u.searchParams.get('tl')||'hy').slice(0,2)}
        else{var pair=(u.searchParams.get('langpair')||'ru|hy').split('|');s=(pair[0]||'ru').slice(0,2);t=(pair[1]||'hy').slice(0,2)}
        s=s==='hy'?'hy':'ru'; t=t==='ru'?'ru':'hy';
        var r=await nativeFetch('/api/translate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:q,source:s,target:t})});
        var j=await r.json();
        if(!r.ok) throw new Error(j.error||'Не удалось получить надёжный перевод');
        meta=j; window.__hayerenTranslateMeta=j;
        if(/translate\\.googleapis/.test(url)) return new Response(JSON.stringify([[[j.translated,q,null,null,10]],null,s]),{status:200,headers:{'Content-Type':'application/json'}});
        return new Response(JSON.stringify({responseData:{translatedText:j.translated,match:j.verified?1:.9},matches:[]}),{status:200,headers:{'Content-Type':'application/json'}});
      }catch(e){
        return new Response(JSON.stringify({responseData:{translatedText:''},responseStatus:503,error:String(e&&e.message||e)}),{status:503,headers:{'Content-Type':'application/json'}})
      }
    }
    return nativeFetch(input,init)
  };
  function polish(){
    var box=document.querySelector('.translation-result'); if(!box)return;
    var m=window.__hayerenTranslateMeta||meta;
    if(m.ruSound){var snd=box.querySelector('.translation-sound');if(snd)snd.textContent=m.ruSound}
    var old=box.querySelector('.hayeren-source');if(old)old.remove();
    if(m.provider){
      var b=document.createElement('div');b.className='hayeren-source';
      b.textContent=(m.verified?'✓ Проверено · ': 'Автоперевод · ')+m.provider;
      b.style.cssText='margin-top:10px;display:inline-flex;padding:7px 11px;border-radius:999px;background:#f2e8df;color:#74483d;font-size:11px;font-weight:800';
      box.appendChild(b)
    }
    if(m.verified){var s=box.querySelector('small');if(s)s.textContent='Проверенная фраза Hayeren.'}
  }
  new MutationObserver(function(){setTimeout(polish,0)}).observe(document.documentElement,{childList:true,subtree:true});
  document.addEventListener('DOMContentLoaded',function(){setTimeout(polish,100)});
})();</script>`;

async function loadUpstream() {
  const r = await fetch(UPSTREAM + '/?source=final-' + VERSION, {headers:{'User-Agent':`Hayeren/${VERSION}`}});
  if (!r.ok) throw new Error('upstream ' + r.status);
  let next = await r.text();
  if (!next.toLowerCase().includes('<!doctype html')) throw new Error('bad upstream html');
  next = next.replace('</head>', bridge + '</head>');
  html = next;
  lastLoad = new Date().toISOString();
  console.log('UPSTREAM_OK bytes=' + Buffer.byteLength(html));
}

async function proxyUpstream(req,res) {
  try {
    const r = await fetch(UPSTREAM + req.url, {headers:{'User-Agent':`Hayeren/${VERSION}`},redirect:'follow'});
    const body = Buffer.from(await r.arrayBuffer());
    const headers = {
      'Content-Type': r.headers.get('content-type') || 'application/octet-stream',
      'Cache-Control': 'public,max-age=21600',
      'Access-Control-Allow-Origin': '*'
    };
    res.writeHead(r.ok ? 200 : r.status, headers);
    res.end(body);
  } catch(e) {
    res.writeHead(502, {'Content-Type':'text/plain; charset=utf-8','Cache-Control':'no-store'});
    res.end('Resource temporarily unavailable');
  }
}

async function runSelfTest(){
  const details=[];
  const check=(name,got,want)=>details.push({name,ok:got===want,value:got});
  try{
    let a=await translate('Я люблю тебя','ru','hy'); check('love',a.translated,'Ես սիրում եմ քեզ');
    a=await translate('Привет','ru','hy'); check('hello',a.translated,'Բարև');
    a=await translate('Где находится центр?','ru','hy'); check('center',a.translated,'Որտե՞ղ է կենտրոնը');
    a=await translate('Ես սիրում եմ քեզ','hy','ru');
    details.push({name:'reverse',ok:/люблю/i.test(a.translated),value:a.translated});
    selfTest={ok:details.every(x=>x.ok),at:new Date().toISOString(),details};
  }catch(e){selfTest={ok:false,at:new Date().toISOString(),details:[...details,{name:'exception',ok:false,value:e.message}]}}
  console.log('HAYEREN_SELFTEST '+JSON.stringify(selfTest));
}

async function syncTelegramMenu(){
  const token = String(process.env.BOT_TOKEN || '').trim();
  if(!token){ console.warn('TELEGRAM_MENU_SKIP no token'); return false; }
  try{
    const me = await fetch(`https://api.telegram.org/bot${token}/getMe`);
    const meJson = await me.json();
    if(!me.ok || !meJson.ok) throw new Error('getMe failed');
    const r = await fetch(`https://api.telegram.org/bot${token}/setChatMenuButton`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({menu_button:{type:'web_app',text:'Открыть Hayeren',web_app:{url:APP_URL}}})
    });
    const j = await r.json();
    if(!r.ok || !j.ok) throw new Error(j.description || ('telegram '+r.status));
    console.log('TELEGRAM_MENU_OK bot=@'+meJson.result.username+' url='+APP_URL);
    return true;
  }catch(e){ console.error('TELEGRAM_MENU_ERROR', e.message); return false; }
}

const manifest = JSON.stringify({name:'Hayeren — Армянский с нуля',short_name:'Hayeren',start_url:'/',display:'standalone',background_color:'#f7f4ee',theme_color:'#f7f4ee',lang:'ru'});
const sw = `self.addEventListener('install',()=>self.skipWaiting());self.addEventListener('activate',e=>e.waitUntil((async()=>{for(const k of await caches.keys())if(/hayeren/i.test(k))await caches.delete(k);await self.clients.claim()})()));`;

const server=http.createServer(async(req,res)=>{
  const u=new URL(req.url,'http://localhost');
  res.setHeader('X-Hayeren-Version',VERSION);
  res.setHeader('Access-Control-Allow-Origin','*');
  if(req.method==='OPTIONS') {res.writeHead(204,{'Access-Control-Allow-Methods':'GET,POST,OPTIONS','Access-Control-Allow-Headers':'Content-Type'});return res.end()}
  if(u.pathname==='/health'){
    res.writeHead(selfTest.ok && html.length>10000 ? 200 : 503,{'Content-Type':'application/json','Cache-Control':'no-store'});
    return res.end(JSON.stringify({ok:selfTest.ok&&html.length>10000,version:VERSION,upstreamLoaded:html.length>10000,lastLoad,htmlBytes:Buffer.byteLength(html),translatorSelfTest:selfTest}));
  }
  if(u.pathname==='/manifest.webmanifest'){res.writeHead(200,{'Content-Type':'application/manifest+json','Cache-Control':'no-store'});return res.end(manifest)}
  if(u.pathname==='/sw.js'){res.writeHead(200,{'Content-Type':'application/javascript; charset=utf-8','Cache-Control':'no-store'});return res.end(sw)}
  if(u.pathname.startsWith('/media/') || u.pathname.startsWith('/_next/') || u.pathname.startsWith('/images/')) return proxyUpstream(req,res);
  if(u.pathname==='/api/translate'){
    const handle=async j=>{
      const text=String(j.text||j.q||'').trim();
      if(!text || text.length>1200) throw new Error('Некорректный текст');
      const source=j.source==='hy'?'hy':'ru',target=j.target==='ru'?'ru':'hy';
      if(source===target) throw new Error('Языки должны отличаться');
      return translate(text,source,target);
    };
    try{
      let j={};
      if(req.method==='GET') j={text:u.searchParams.get('text')||u.searchParams.get('q')||'',source:u.searchParams.get('source')||'ru',target:u.searchParams.get('target')||'hy'};
      else if(req.method==='POST') j=await new Promise((resolve,reject)=>{let body='';req.on('data',c=>{body+=c;if(body.length>12000)reject(new Error('too large'))});req.on('end',()=>{try{resolve(JSON.parse(body||'{}'))}catch(e){reject(e)}})});
      else {res.writeHead(405,{'Content-Type':'application/json'});return res.end(JSON.stringify({error:'method not allowed'}))}
      const out=await handle(j);
      res.writeHead(200,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'});
      return res.end(JSON.stringify(out));
    }catch(e){
      res.writeHead(422,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'});
      return res.end(JSON.stringify({error:e.message||'Не удалось получить надёжный перевод'}));
    }
  }
  res.writeHead(200,{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store,no-cache,must-revalidate,max-age=0','Pragma':'no-cache','Expires':'0','X-Content-Type-Options':'nosniff'});
  res.end(html || '<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><body style="font-family:-apple-system;padding:32px;background:#f7f4ee"><h1>Hayeren запускается…</h1><p>Обновите страницу через несколько секунд.</p></body></html>');
});

(async()=>{
  try{await loadUpstream()}catch(e){console.error('LOAD_UPSTREAM_ERROR',e)}
  server.listen(process.env.PORT||10000,'0.0.0.0',()=>console.log('Hayeren final '+VERSION+' ready'));
  await runSelfTest();
  await syncTelegramMenu();
  setInterval(()=>loadUpstream().catch(e=>console.warn('UPSTREAM_REFRESH',e.message)),5*60*1000).unref();
  setInterval(()=>runSelfTest().catch(()=>{}),15*60*1000).unref();
})();
