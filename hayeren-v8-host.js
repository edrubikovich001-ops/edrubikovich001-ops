const http=require('http');

const UPSTREAM='https://hayeren-v6-live.onrender.com/';
function norm(s){return String(s||'').toLowerCase().replace(/[?!.,;:()«»“”"']/g,'').replace(/\s+/g,' ').trim()}
const curated={
 'я люблю тебя':['Ես սիրում եմ քեզ','Ес сирум ем кез','Я люблю тебя'],
 'люблю тебя':['Ես սիրում եմ քեզ','Ес сирум ем кез','Я люблю тебя'],
 'я тебя люблю':['Ես քեզ սիրում եմ','Ес кез сирум ем','Я тебя люблю'],
 'привет':['Բարև','Барев','Привет'],
 'здравствуйте':['Բարև ձեզ','Барев дзез','Здравствуйте'],
 'спасибо':['Շնորհակալություն','Шноракалутюн','Спасибо'],
 'большое спасибо':['Շատ շնորհակալություն','Шат шноракалутюн','Большое спасибо'],
 'пожалуйста':['Խնդրեմ','Хндрем','Пожалуйста'],
 'извините':['Ներեցեք','Нерецек','Извините'],
 'как дела':['Ինչպե՞ս ես','Инчпес ес','Как дела?'],
 'доброе утро':['Բարի լույս','Бари луйс','Доброе утро'],
 'добрый вечер':['Բարի երեկո','Бари ереко','Добрый вечер'],
 'спокойной ночи':['Բարի գիշեր','Бари гишер','Спокойной ночи'],
 'до свидания':['Ցտեսություն','Цтесутюн','До свидания'],
 'да':['Այո','Айо','Да'],'нет':['Ոչ','Воч','Нет'],
 'я не понимаю':['Ես չեմ հասկանում','Ес чем хасканум','Я не понимаю'],
 'повторите пожалуйста':['Կրկնեք, խնդրում եմ','Кркнек, хндрум ем','Повторите, пожалуйста'],
 'говорите медленнее пожалуйста':['Ավելի դանդաղ խոսեք, խնդրում եմ','Авели дандал хосек, хндрум ем','Говорите медленнее, пожалуйста'],
 'как вас зовут':['Ի՞նչ է ձեր անունը','Инч э дзер ануны','Как вас зовут?'],
 'где туалет':['Որտե՞ղ է զուգարանը','Вортех э зугараны','Где туалет?'],
 'сколько стоит':['Որքա՞ն արժե','Воркан арже','Сколько стоит?'],
 'мне нужно такси':['Ինձ տաքսի է պետք','Индз такси э петк','Мне нужно такси'],
 'мне нужен врач':['Ինձ բժիշկ է պետք','Индз бжишк э петк','Мне нужен врач'],
 'помогите пожалуйста':['Օգնեք, խնդրում եմ','Огнек, хндрум ем','Помогите, пожалуйста'],
 'где находится центр':['Որտե՞ղ է կենտրոնը','Вортех э кентроны','Где находится центр?'],
 'я из казахстана':['Ես Ղազախստանից եմ','Ес Газахстаниц ем','Я из Казахстана'],
 'я из россии':['Ես Ռուսաստանից եմ','Ес Русастаниц ем','Я из России'],
 'вы говорите по русски':['Դուք ռուսերեն խոսո՞ւմ եք','Дук русерен хосум ек','Вы говорите по-русски?'],
 'армения':['Հայաստան','Айастан','Армения'],'ереван':['Երևան','Ереван','Ереван']
};
const reverse={};for(const v of Object.values(curated))reverse[norm(v[0])]=v;
const map={'Ա':'А','ա':'а','Բ':'Б','բ':'б','Գ':'Г','գ':'г','Դ':'Д','դ':'д','Ե':'Е','ե':'е','Զ':'З','զ':'з','Է':'Э','է':'э','Ը':'Ы','ը':'ы','Թ':'Т','թ':'т','Ժ':'Ж','ժ':'ж','Ի':'И','ի':'и','Լ':'Л','լ':'л','Խ':'Х','խ':'х','Ծ':'Ц','ծ':'ц','Կ':'К','կ':'к','Հ':'Х','հ':'х','Ձ':'Дз','ձ':'дз','Ղ':'Х','ղ':'х','Ճ':'Ч','ճ':'ч','Մ':'М','մ':'м','Յ':'Й','յ':'й','Ն':'Н','ն':'н','Շ':'Ш','շ':'ш','Ո':'О','ո':'о','Չ':'Ч','չ':'ч','Պ':'П','պ':'п','Ջ':'Дж','ջ':'дж','Ռ':'Р','ռ':'р','Ս':'С','ս':'с','Վ':'В','վ':'в','Տ':'Т','տ':'т','Ր':'Р','ր':'р','Ց':'Ц','ց':'ц','Ւ':'В','ւ':'в','Փ':'П','փ':'п','Ք':'К','ք':'к','Օ':'О','օ':'о','Ֆ':'Ф','ֆ':'ф'};
function sound(x){let s=String(x).replace(/Ու/g,'У').replace(/ու/g,'у').replace(/Եվ/g,'Ев').replace(/և/g,'ев');return [...s].map(c=>map[c]??c).join('').replace(/\s+/g,' ').trim()}
function suspicious(out,source,target){const n=norm(out);if(!out||out.length>800)return true;if(source==='ru'&&target==='hy'&&!/[Ա-Ֆա-ֆև]/.test(out))return true;if(['չատլախ','чатлах'].some(x=>n.includes(x)))return true;return false}
async function google(text,source,target){const u=new URL('https://translate.googleapis.com/translate_a/single');u.searchParams.set('client','gtx');u.searchParams.set('sl',source);u.searchParams.set('tl',target);u.searchParams.set('dt','t');u.searchParams.set('q',text);const r=await fetch(u,{headers:{'Accept':'application/json','User-Agent':'Hayeren/8.1'}});if(!r.ok)throw new Error('google '+r.status);const d=await r.json();const out=Array.isArray(d?.[0])?d[0].map(x=>x?.[0]||'').join('').trim():'';if(!out)throw new Error('empty');return out}
async function memory(text,source,target){const u=new URL('https://api.mymemory.translated.net/get');u.searchParams.set('q',text);u.searchParams.set('langpair',`${source}|${target}`);const r=await fetch(u,{headers:{'Accept':'application/json','User-Agent':'Hayeren/8.1'}});if(!r.ok)throw new Error('memory '+r.status);const d=await r.json();const out=String(d?.responseData?.translatedText||'').trim();if(!out)throw new Error('empty');return out}
async function translate(text,source,target){const exact=source==='ru'?curated[norm(text)]:reverse[norm(text)];if(exact)return {translated:target==='hy'?exact[0]:exact[2],ruSound:exact[1],provider:'Проверено Hayeren',verified:true};let out='',provider='Google Translate';try{out=await google(text,source,target)}catch(e){console.error('google',e);out=await memory(text,source,target);provider='Резервный перевод'}if(suspicious(out,source,target))throw new Error('suspicious translation');return {translated:out,ruSound:target==='hy'?sound(out):sound(text),provider,verified:false}}
const bridge=`<script id="hayeren-v8-translate-bridge">(function(){var nativeFetch=window.fetch.bind(window);window.fetch=async function(input,init){var url=typeof input==='string'?input:(input&&input.url)||'';if(url.indexOf('api.mymemory.translated.net/get')!==-1){try{var u=new URL(url,location.href),q=u.searchParams.get('q')||'',pair=(u.searchParams.get('langpair')||'ru|hy').split('|'),s=(pair[0]||'ru').slice(0,2)==='hy'?'hy':'ru',t=(pair[1]||'hy').slice(0,2)==='ru'?'ru':'hy';var r=await nativeFetch('/api/translate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:q,source:s,target:t})});var j=await r.json();if(!r.ok)throw new Error(j.error||'translation failed');window.__hayerenTranslateProvider=j.provider||'';window.__hayerenTranslateVerified=!!j.verified;return new Response(JSON.stringify({responseData:{translatedText:j.translated,match:j.verified?1:.95},matches:[]}),{status:200,headers:{'Content-Type':'application/json'}})}catch(e){return new Response(JSON.stringify({responseData:{translatedText:''},responseStatus:500}),{status:500,headers:{'Content-Type':'application/json'}})}}return nativeFetch(input,init)};function polish(){var box=document.querySelector('.translation-result');if(!box)return;var old=box.querySelector('.h8-source');if(old)old.remove();if(window.__hayerenTranslateProvider){var b=document.createElement('div');b.className='h8-source';b.textContent=(window.__hayerenTranslateVerified?'✓ ':'')+window.__hayerenTranslateProvider;b.style.cssText='margin-top:10px;display:inline-flex;padding:6px 9px;border-radius:999px;background:#efe8df;color:#7a5144;font-size:10px;font-weight:800';box.appendChild(b)}var s=box.querySelector('small');if(s&&window.__hayerenTranslateVerified)s.textContent='Проверенная фраза Hayeren.'}new MutationObserver(function(){setTimeout(polish,0)}).observe(document.documentElement,{childList:true,subtree:true});})();</script>`;
let html='';async function load(){const r=await fetch(UPSTREAM,{headers:{'User-Agent':'Hayeren-v8-proxy'}});if(!r.ok)throw new Error('upstream '+r.status);html=await r.text();if(!html.toLowerCase().includes('<!doctype html'))throw new Error('bad upstream html');html=html.replace('</head>',bridge+'</head>')}
function svg(kind){const data={ararat:['#d58b65','#704136','Արարատ'],yerevan:['#d9a27f','#914d42','Երևան'],geghard:['#a69078','#665247','Գեղարդ'],sevan:['#83b6c8','#315d77','Սևան']}[kind]||['#c88361','#714139','Հայաստան'];return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 520"><defs><linearGradient id="g" x2="1" y2="1"><stop stop-color="${data[0]}"/><stop offset="1" stop-color="${data[1]}"/></linearGradient></defs><rect width="900" height="520" fill="url(#g)"/><circle cx="735" cy="92" r="52" fill="#f4c47d" opacity=".9"/><path d="M0 520 260 150l120 150 92-110 280 330z" fill="rgba(70,40,34,.55)"/><path d="m188 252 72-102 42 54-28 12-17-22-38 59z" fill="#fff0df"/><text x="48" y="455" fill="white" font-size="54" font-family="system-ui" font-weight="700">${data[2]}</text><text x="50" y="493" fill="rgba(255,255,255,.78)" font-size="22" font-family="system-ui">Hayeren · Armenia</text></svg>`}
const server=http.createServer((req,res)=>{
 if(req.url==='/health'){res.writeHead(200,{'Content-Type':'application/json','Cache-Control':'no-store'});return res.end(JSON.stringify({ok:true,v:'8.1',translator:'server-proxy',upstreamLoaded:html.length>10000,htmlBytes:Buffer.byteLength(html)}))}
 if(req.url&&req.url.startsWith('/media/')){res.writeHead(200,{'Content-Type':'image/svg+xml','Cache-Control':'public,max-age=86400'});return res.end(svg(req.url.split('/').pop()))}
 if(req.url==='/api/translate'&&req.method==='POST'){let body='';req.on('data',c=>{if(body.length<8192)body+=c});req.on('end',async()=>{try{const j=JSON.parse(body||'{}'),text=String(j.text||'').trim(),source=j.source==='hy'?'hy':'ru',target=j.target==='ru'?'ru':'hy';if(!text||text.length>500||source===target)throw new Error('bad request');const out=await translate(text,source,target);res.writeHead(200,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'});res.end(JSON.stringify(out))}catch(e){console.error('translate',e);res.writeHead(422,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'});res.end(JSON.stringify({error:'Не уверен в переводе. Переформулируйте фразу.'}))}});return}
 if(req.url==='/sw.js'){res.writeHead(200,{'Content-Type':'application/javascript','Cache-Control':'no-store'});return res.end("self.addEventListener('install',()=>self.skipWaiting());self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));")}
 if(req.url==='/manifest.webmanifest'){res.writeHead(200,{'Content-Type':'application/manifest+json','Cache-Control':'no-store'});return res.end(JSON.stringify({name:'Hayeren — Армянский с нуля',short_name:'Hayeren',start_url:'/',display:'standalone',background_color:'#f7f4ee',theme_color:'#f7f4ee',lang:'ru'}))}
 res.writeHead(200,{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store,max-age=0'});res.end(html||'<!doctype html><meta charset=utf-8><h1>Hayeren запускается…</h1>')
});
load().then(()=>server.listen(process.env.PORT||10000,'0.0.0.0',()=>console.log('Hayeren v8.1 translator proxy ready'))).catch(e=>{console.error('load upstream',e);server.listen(process.env.PORT||10000,'0.0.0.0',()=>console.log('Hayeren v8.1 fallback ready'))});
