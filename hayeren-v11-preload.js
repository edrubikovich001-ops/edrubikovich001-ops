const http=require('http');

const patch=`<script id="hayeren-fast-translate-patch">(function(){
const dict={
 'я люблю тебя':['Ես սիրում եմ քեզ','Ес сирум ем кез','Я люблю тебя'],
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
 'я хочу воды':['Ես ջուր եմ ուզում','Ес джур ем узум','Я хочу воды']
};
const rdict={};Object.values(dict).forEach(v=>rdict[norm(v[0])]=v);
const ruHy={'а':'ա','б':'բ','в':'վ','г':'գ','д':'դ','е':'ե','ё':'յո','ж':'ժ','з':'զ','и':'ի','й':'յ','к':'կ','л':'լ','м':'մ','н':'ն','о':'ո','п':'պ','р':'ր','с':'ս','т':'տ','у':'ու','ф':'ֆ','х':'խ','ц':'ց','ч':'չ','ш':'շ','щ':'շ','ы':'ը','э':'է','ю':'յու','я':'յա','ь':'','ъ':''};
function norm(s){return String(s||'').toLowerCase().replace(/[?!.,;:()«»“”"']/g,'').replace(/[-–—]/g,' ').replace(/\\s+/g,' ').trim()}
function nameHy(s){return String(s||'').trim().split('').map((c,i)=>{const v=ruHy[c.toLowerCase()];if(v==null)return c;return i===0?v.charAt(0).toUpperCase()+v.slice(1):v}).join('')}
function local(text,s,t){const n=norm(text),v=s==='ru'?dict[n]:rdict[n];if(v)return{translated:t==='hy'?v[0]:v[2],ruSound:v[1],provider:'Hayeren · проверено',verified:true,confidence:1};if(s==='ru'&&t==='hy'){const m=String(text).match(/^\\s*меня\\s+зовут\\s+(.+?)\\s*[.!?]*$/i);if(m){const name=m[1].trim();return{translated:'Իմ անունը '+nameHy(name)+' է',ruSound:'Им ануны '+name+' э',provider:'Hayeren · мгновенно',verified:true,confidence:.98}}}return null}
function cacheGet(k){try{return JSON.parse(localStorage.getItem('hayeren-fast-tr:'+k)||'null')}catch{return null}}
function cacheSet(k,v){try{localStorage.setItem('hayeren-fast-tr:'+k,JSON.stringify(v))}catch{}}
function toGoogle(j,q,s){window.__hayerenTranslateMeta=j;return new Response(JSON.stringify([[[j.translated,q,null,null,10]],null,s]),{status:200,headers:{'Content-Type':'application/json'}})}
function toMemory(j){window.__hayerenTranslateMeta=j;return new Response(JSON.stringify({responseData:{translatedText:j.translated,match:j.verified?1:.9},matches:[]}),{status:200,headers:{'Content-Type':'application/json'}})}
function toApi(j){window.__hayerenTranslateMeta=j;return new Response(JSON.stringify(j),{status:200,headers:{'Content-Type':'application/json'}})}
function failResponse(isG,isM,msg){msg=msg||'Перевод временно недоступен. Нажмите ещё раз.';if(isG)return new Response(JSON.stringify({error:msg}),{status:503,headers:{'Content-Type':'application/json'}});if(isM)return new Response(JSON.stringify({responseData:{translatedText:''},responseStatus:503,error:msg}),{status:503,headers:{'Content-Type':'application/json'}});return new Response(JSON.stringify({error:msg}),{status:503,headers:{'Content-Type':'application/json'}})}
const previous=window.fetch.bind(window),inflight=new Map();
async function serverTranslate(q,s,t){const ctrl=new AbortController(),tm=setTimeout(()=>ctrl.abort(),2800);try{const r=await previous('/api/translate',{method:'POST',signal:ctrl.signal,headers:{'Content-Type':'application/json'},body:JSON.stringify({text:q,source:s,target:t})});let j={};try{j=await r.json()}catch{}if(!r.ok||!j||!j.translated)throw new Error((j&&j.error)||'translation failed');return j}finally{clearTimeout(tm)}}
function getTranslatorButton(){const h=[...document.querySelectorAll('h1,h2')].find(e=>(e.textContent||'').includes('Скажи это по-армянски'));if(!h)return null;let root=h.parentElement;for(let i=0;i<6&&root;i++,root=root.parentElement){const b=[...root.querySelectorAll('button')].find(x=>/перев/i.test(x.textContent||''));if(b)return b}return null}
function watchdog(){const b=getTranslatorButton();if(!b)return;if(b.disabled){if(!b.dataset.disabledSince)b.dataset.disabledSince=String(Date.now());else if(Date.now()-Number(b.dataset.disabledSince)>3400){b.disabled=false;b.removeAttribute('disabled');delete b.dataset.disabledSince}}else delete b.dataset.disabledSince}
window.fetch=async function(input,init){const raw=typeof input==='string'?input:(input&&input.url)||'',isG=/translate\\.googleapis\\.com\\/translate_a\\/single/.test(raw)||/translate\\.google\\.[^/]+\\/translate_a\\/single/.test(raw),isM=/api\\.mymemory\\.translated\\.net\\/get/.test(raw),isApi=/\\/api\\/translate(?:\\?|$)/.test(raw);if(!isG&&!isM&&!isApi)return previous(input,init);let q='',s='ru',t='hy';try{if(isApi&&init&&String(init.method||'GET').toUpperCase()==='POST'){const b=JSON.parse(init.body||'{}');q=String(b.text||'');s=b.source==='hy'?'hy':'ru';t=b.target==='ru'?'ru':'hy'}else{const u=new URL(raw,location.href);q=u.searchParams.get('text')||u.searchParams.get('q')||'';if(isM){const p=(u.searchParams.get('langpair')||'ru|hy').split('|');s=p[0]==='hy'?'hy':'ru';t=p[1]==='ru'?'ru':'hy'}else{s=(u.searchParams.get('sl')||u.searchParams.get('source')||'ru').slice(0,2)==='hy'?'hy':'ru';t=(u.searchParams.get('tl')||u.searchParams.get('target')||'hy').slice(0,2)==='ru'?'ru':'hy'}}q=String(q||'').trim();if(!q)return failResponse(isG,isM,'Введите текст');const key=s+'|'+t+'|'+norm(q),fast=local(q,s,t)||cacheGet(key);if(fast)return isG?toGoogle(fast,q,s):isM?toMemory(fast):toApi(fast);let p=inflight.get(key);if(!p){p=serverTranslate(q,s,t).then(j=>{cacheSet(key,j);return j}).finally(()=>inflight.delete(key));inflight.set(key,p)}const j=await p;return isG?toGoogle(j,q,s):isM?toMemory(j):toApi(j)}catch(e){return failResponse(isG,isM,e&&e.name==='AbortError'?'Перевод занял слишком долго. Нажмите ещё раз.':'Перевод временно недоступен. Нажмите ещё раз.')}finally{setTimeout(watchdog,0);setTimeout(watchdog,150);setTimeout(watchdog,3500)}};
function meta(){const box=document.querySelector('.translation-result'),m=window.__hayerenTranslateMeta;if(box&&m){const s=box.querySelector('.translation-sound');if(s&&m.ruSound)s.textContent=m.ruSound;let d=box.querySelector('.hayeren-fast-provider');if(m.provider){if(!d){d=document.createElement('div');d.className='hayeren-fast-provider';d.style='margin-top:10px;font-size:11px;font-weight:800;color:#755348';box.appendChild(d)}d.textContent=(m.verified?'✓ ':'')+m.provider}}}
function go(){meta();watchdog()}new MutationObserver(()=>setTimeout(go,0)).observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['disabled']});document.addEventListener('DOMContentLoaded',go);setInterval(watchdog,700);setTimeout(go,200);setTimeout(go,800);window.__HAYEREN_FAST_TRANSLATOR__='12.0';
})();</script>`;

const originalEnd=http.ServerResponse.prototype.end;
http.ServerResponse.prototype.end=function(chunk,encoding,cb){try{const ct=String(this.getHeader('content-type')||'').toLowerCase();if(chunk&&ct.includes('text/html')){let text=Buffer.isBuffer(chunk)?chunk.toString('utf8'):String(chunk);if(!text.includes('hayeren-fast-translate-patch')&&text.includes('</body>')){text=text.replace('</body>',patch+'</body>');this.removeHeader('content-length');chunk=text;encoding='utf8'}}}catch(e){console.error('FAST_TRANSLATOR_INJECT',e&&e.message)}return originalEnd.call(this,chunk,encoding,cb)};
console.log('HAYEREN_FAST_TRANSLATOR_PRELOAD 12.0');
