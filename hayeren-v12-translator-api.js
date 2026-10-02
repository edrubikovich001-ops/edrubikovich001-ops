// Hayeren v12.2 translator API override.
// Accuracy-first: verified local phrases -> private offline RU<->HY model -> clear fast error.
// Never returns a dubious public-provider result just to fill the screen.
const http = require('http');
const { URL } = require('url');
const previousCreateServer = http.createServer.bind(http);
const OFFLINE = 'https://hayeren-offline-translator.onrender.com';
const SECRET = process.env.HAYEREN_OFFLINE_SECRET || '';
const cache = new Map();

function norm(s){return String(s||'').toLowerCase().replace(/[?!.,;:()«»“”"']/g,'').replace(/[-–—]/g,' ').replace(/\s+/g,' ').trim()}
const dict={
 'я люблю тебя':['Ես սիրում եմ քեզ','Ес сирум ем кез','Я люблю тебя'],
 'я тебя люблю':['Ես քեզ սիրում եմ','Ес кез сирум ем','Я тебя люблю'],
 'привет':['Բարև','Барев','Привет'],
 'здравствуйте':['Բարև ձեզ','Барев дзез','Здравствуйте'],
 'спасибо':['Շնորհակալություն','Шноракалуцюн','Спасибо'],
 'пожалуйста':['Խնդրեմ','Хндрем','Пожалуйста'],
 'как дела':['Ինչպե՞ս ես','Инчпес ес?','Как дела?'],
 'как тебя зовут':['Ի՞նչ է քո անունը','Инч э ко ануны?','Как тебя зовут?'],
 'как вас зовут':['Ի՞նչ է ձեր անունը','Инч э дзер ануны?','Как вас зовут?'],
 'меня зовут марк':['Իմ անունը Մարկ է','Им ануны Марк э','Меня зовут Марк'],
 'меня зовут эдгар':['Իմ անունը Էդգար է','Им ануны Эдгар э','Меня зовут Эдгар'],
 'где туалет':['Որտե՞ղ է զուգարանը','Вортех э зугараны?','Где туалет?'],
 'сколько стоит':['Որքա՞ն արժե','Воркан арже?','Сколько стоит?'],
 'мне нужно такси':['Ինձ տաքսի է պետք','Индз такси э петк','Мне нужно такси'],
 'я хочу кофе':['Ես սուրճ եմ ուզում','Ес сурч ем узум','Я хочу кофе'],
 'я хочу воды':['Ես ջուր եմ ուզում','Ес джур ем узум','Я хочу воды'],
 'сегодня прекрасная погода':['Այսօր հիանալի եղանակ է','Айсор хианали еганак э','Сегодня прекрасная погода'],
 'я хочу купить билет на поезд':['Ես ուզում եմ գնացքի տոմս գնել','Ес узум ем гнацки томс гнел','Я хочу купить билет на поезд']
};
const reverse={};for(const v of Object.values(dict))reverse[norm(v[0])]=v;
const ruHy={'а':'ա','б':'բ','в':'վ','г':'գ','д':'դ','е':'ե','ё':'յո','ж':'ժ','з':'զ','и':'ի','й':'յ','к':'կ','л':'լ','м':'մ','н':'ն','о':'ո','п':'պ','р':'ր','с':'ս','т':'տ','у':'ու','ф':'ֆ','х':'խ','ц':'ց','ч':'չ','ш':'շ','щ':'շ','ы':'ը','э':'է','ю':'յու','я':'յա','ь':'','ъ':''};
const hyRu={'Ա':'А','ա':'а','Բ':'Б','բ':'б','Գ':'Г','գ':'г','Դ':'Д','դ':'д','Ե':'Е','ե':'е','Զ':'З','զ':'з','Է':'Э','է':'э','Ը':'Ы','ը':'ы','Թ':'Т','թ':'т','Ժ':'Ж','ժ':'ж','Ի':'И','ի':'и','Լ':'Л','լ':'л','Խ':'Х','խ':'х','Ծ':'Ц','ծ':'ц','Կ':'К','կ':'к','Հ':'Х','հ':'х','Ձ':'Дз','ձ':'дз','Ղ':'Г','ղ':'г','Ճ':'Ч','ճ':'ч','Մ':'М','մ':'м','Յ':'Й','յ':'й','Ն':'Н','ն':'н','Շ':'Ш','շ':'ш','Ո':'О','ո':'о','Չ':'Ч','չ':'ч','Պ':'П','պ':'п','Ջ':'Дж','ջ':'дж','Ռ':'Р','ռ':'р','Ս':'С','ս':'с','Վ':'В','վ':'в','Տ':'Т','տ':'т','Ր':'Р','ր':'р','Ց':'Ц','ց':'ц','Ւ':'В','ւ':'в','Փ':'П','փ':'п','Ք':'К','ք':'к','Օ':'О','օ':'о','Ֆ':'Ф','ֆ':'ф'};
function nameHy(s){return String(s||'').trim().split('').map((c,i)=>{const v=ruHy[c.toLowerCase()];if(v==null)return c;return i===0?v.charAt(0).toUpperCase()+v.slice(1):v}).join('')}
function sound(x){let s=String(x||'').replace(/Ու/g,'У').replace(/ու/g,'у').replace(/Եվ/g,'Ев').replace(/և/g,'ев');return [...s].map(c=>hyRu[c]??c).join('').replace(/\s+/g,' ').trim()}
function local(text,source,target){const n=norm(text),v=source==='ru'?dict[n]:reverse[n];if(v)return{translated:target==='hy'?v[0]:v[2],ruSound:v[1],provider:'Hayeren · проверено',verified:true,confidence:1};if(source==='ru'&&target==='hy'){const m=String(text).match(/^\s*меня\s+зовут\s+(.+?)\s*[.!?]*$/i);if(m){const name=m[1].trim(),hy=nameHy(name);return{translated:`Իմ անունը ${hy} է`,ruSound:`Им ануны ${name} э`,provider:'Hayeren · мгновенно',verified:true,confidence:.99}}}return null}
function valid(out,target){if(!out||out.length>1600)return false;if(target==='hy'&&!/[Ա-Ֆա-ֆև]/.test(out))return false;if(target==='ru'&&!/[А-Яа-яЁё]/.test(out))return false;return !/չատլախ|чатлах|undefined|null/i.test(out)}
async function offlineOnce(text,source,target,timeout=1700){const ctrl=new AbortController(),tm=setTimeout(()=>ctrl.abort(),timeout);try{const r=await fetch(OFFLINE+'/translate',{method:'POST',signal:ctrl.signal,headers:{'content-type':'application/json','x-hayeren-secret':SECRET},body:JSON.stringify({text,source,target})});let j={};try{j=await r.json()}catch{}if(!r.ok||!j.translated||!valid(j.translated,target))throw new Error('offline '+r.status);return{translated:j.translated,ruSound:target==='hy'?sound(j.translated):sound(text),provider:'Hayeren Offline · Helsinki-NLP',verified:false,confidence:.9,elapsedMs:j.elapsedMs||0}}finally{clearTimeout(tm)}}
async function translate(text,source,target){text=String(text||'').trim();const fast=local(text,source,target);if(fast)return fast;const key=source+'|'+target+'|'+norm(text);if(cache.has(key))return cache.get(key);let lastErr=null;for(const wait of [0,450,900]){if(wait)await new Promise(r=>setTimeout(r,wait));try{const r=await offlineOnce(text,source,target,1700);cache.set(key,r);if(cache.size>400)cache.delete(cache.keys().next().value);return r}catch(e){lastErr=e}}throw new Error('Переводчик прогревается. Нажмите ещё раз через секунду.')}
async function readBody(req){return await new Promise((resolve,reject)=>{let b='';req.on('data',c=>{b+=c;if(b.length>12000)reject(new Error('too large'))});req.on('end',()=>{try{resolve(JSON.parse(b||'{}'))}catch(e){reject(e)}})})}
async function handle(req,res,u){try{let j=req.method==='GET'?{text:u.searchParams.get('text')||u.searchParams.get('q')||'',source:u.searchParams.get('source')||'ru',target:u.searchParams.get('target')||'hy'}:await readBody(req);const text=String(j.text||'').trim(),source=j.source==='hy'?'hy':'ru',target=j.target==='ru'?'ru':'hy';if(!text||text.length>1200||source===target)throw new Error('Некорректный текст');const out=await translate(text,source,target);res.writeHead(200,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','Access-Control-Allow-Origin':'*'});return res.end(JSON.stringify(out))}catch(e){res.writeHead(503,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','Access-Control-Allow-Origin':'*'});return res.end(JSON.stringify({error:e.message||'Перевод временно недоступен'}))}}
function wrap(listener){if(typeof listener!=='function')return listener;return function translatorApi(req,res){try{const u=new URL(req.url||'/','http://localhost');if(u.pathname==='/api/translate'&&(req.method==='GET'||req.method==='POST'))return handle(req,res,u)}catch{}return listener.call(this,req,res)}}
http.createServer=function patched(options,listener){if(typeof options==='function'||options==null)return previousCreateServer(wrap(options));return previousCreateServer(options,wrap(listener))};
async function warm(){try{const ctrl=new AbortController(),tm=setTimeout(()=>ctrl.abort(),2200);try{await fetch(OFFLINE+'/health',{signal:ctrl.signal,cache:'no-store'})}finally{clearTimeout(tm)}}catch{}}
setTimeout(warm,250);setTimeout(warm,2500);setInterval(warm,4*60*1000).unref();
console.log('HAYEREN_TRANSLATOR_API_READY 12.2');
