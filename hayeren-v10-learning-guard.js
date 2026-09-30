// Hayeren 10 learning-order guard v3.
// Teaches unseen vocabulary before pair-matching tasks without doing heavy DOM work on every mutation.
const http = require('http');
const previousCreateServer = http.createServer.bind(http);

const guardUi = `<style id="hayeren-learning-guard-css">
.hlg-overlay{position:fixed;inset:0;z-index:2147483000;background:#f7f4ee;color:#241f1a;overflow:auto;-webkit-overflow-scrolling:touch;padding:max(24px,env(safe-area-inset-top)) 18px max(30px,env(safe-area-inset-bottom));font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.hlg-wrap{max-width:480px;margin:0 auto}.hlg-kicker{font-size:11px;font-weight:900;letter-spacing:.15em;color:#b75d45;text-transform:uppercase}.hlg-title{font-size:30px;line-height:1.08;margin:8px 0 8px;font-weight:850}.hlg-sub{font-size:15px;line-height:1.45;color:#7a7068;margin:0 0 18px}.hlg-list{display:grid;gap:10px;margin-bottom:18px}.hlg-card{background:#fffefa;border:1px solid #e8e0d6;border-radius:21px;padding:15px 16px;box-shadow:0 5px 18px rgba(70,48,34,.045)}.hlg-hy{font-size:24px;line-height:1.25;font-weight:760}.hlg-sound{font-size:14px;color:#b75d45;margin-top:5px}.hlg-ru{font-size:17px;font-weight:720;margin-top:8px}.hlg-loading{font-size:13px;color:#8b8077;margin-top:7px}.hlg-go{position:sticky;bottom:max(12px,env(safe-area-inset-bottom));width:100%;border:0;border-radius:18px;padding:16px;background:linear-gradient(135deg,#bd684e,#d69a52);color:white;font-size:17px;font-weight:850;box-shadow:0 10px 28px rgba(117,63,45,.22)}
</style><script id="hayeren-learning-guard-runtime">(()=>{
const ARM=/[Ա-Ֆա-ֆև]/, CYR=/[А-Яа-яЁё]/;
const STORE='hayeren-known-vocab-v2';
let busy=false,lastSig='',timer=0,lastBody='';
const clean=s=>String(s||'').replace(/\s+/g,' ').trim();
const key=s=>clean(s).toLowerCase().replace(/[։՞՜՛.,!?;:\\-–—()«»“”"']/g,'').replace(/\s+/g,' ');
function known(){try{return new Set(JSON.parse(localStorage.getItem(STORE)||'[]').map(key))}catch{return new Set()}}
function saveKnown(items){const s=known();items.forEach(x=>s.add(key(x)));try{localStorage.setItem(STORE,JSON.stringify([...s].slice(-1200)))}catch{}}
function matchingScreen(){
  const body=clean(document.body&&document.body.innerText);
  if(body===lastBody && !body.includes('СОЕДИНИ')) return false;
  lastBody=body;
  const t=body.toUpperCase();
  return t.includes('СОЕДИНИ ПАРЫ') && (t.includes('АРМЯНСКИЙ И ПЕРЕВОД')||t.includes('АРМЯНСКИЙ'));
}
function parseCard(el){
  const raw=String(el&&el.innerText||'').trim();
  if(!raw||raw.length>180||!ARM.test(raw)) return null;
  const lines=raw.split(/\n+/).map(clean).filter(Boolean);
  const hy=clean(lines.filter(x=>ARM.test(x)).join(' '));
  if(!hy||hy.length>90) return null;
  const sound=clean(lines.filter(x=>!ARM.test(x)&&CYR.test(x)).join(' '));
  return {hy,sound};
}
function extract(){
  const out=[],seen=new Set();
  if(!document.body) return out;
  const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
  let node,count=0;
  while((node=walker.nextNode()) && count<1500){
    count++;
    if(!ARM.test(node.nodeValue||'')) continue;
    let el=node.parentElement,card=null;
    for(let depth=0;el&&depth<6;depth++,el=el.parentElement){
      const parsed=parseCard(el);
      if(parsed){card=parsed;break}
    }
    if(!card) continue;
    const k=key(card.hy);
    if(!seen.has(k)){seen.add(k);out.push(card)}
    if(out.length>=10) break;
  }
  return out;
}
async function tr(text){
  const ctrl=new AbortController(),tm=setTimeout(()=>ctrl.abort(),9000);
  try{const r=await fetch('/api/translate',{method:'POST',signal:ctrl.signal,headers:{'Content-Type':'application/json'},body:JSON.stringify({text,source:'hy',target:'ru'})});const j=await r.json();if(!r.ok||!j.translated)throw new Error('translate');return clean(j.translated)}finally{clearTimeout(tm)}
}
function signature(items){let h=2166136261;const s=items.map(x=>key(x.hy)).sort().join('|');for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619)}return String(h>>>0)}
async function show(items){
  busy=true;const sig=signature(items);lastSig=sig;
  const overlay=document.createElement('div');overlay.className='hlg-overlay';
  overlay.innerHTML='<div class="hlg-wrap"><div class="hlg-kicker">Сначала изучи</div><div class="hlg-title">Новые слова перед заданием</div><p class="hlg-sub">Сначала посмотри значение и произношение. После этого можно будет соединять пары.</p><div class="hlg-list"></div><button class="hlg-go" disabled>Готовлю слова…</button></div>';
  document.body.appendChild(overlay);const list=overlay.querySelector('.hlg-list'),go=overlay.querySelector('.hlg-go');
  items.forEach((x,i)=>{const c=document.createElement('div');c.className='hlg-card';c.dataset.i=String(i);c.innerHTML='<div class="hlg-hy"></div><div class="hlg-sound"></div><div class="hlg-loading">Загружаю перевод…</div>';c.querySelector('.hlg-hy').textContent=x.hy;c.querySelector('.hlg-sound').textContent=x.sound||'';list.appendChild(c)});
  await Promise.all(items.map(async(x,i)=>{let ru='';try{ru=await tr(x.hy)}catch{}const c=list.querySelector('[data-i="'+i+'"]');if(!c)return;const m=c.querySelector('.hlg-loading');if(ru){m.className='hlg-ru';m.textContent=ru}else m.textContent='Перевод появится в задании'}));
  go.disabled=false;go.textContent='Изучил — перейти к заданию';go.addEventListener('click',()=>{saveKnown(items.map(x=>x.hy));try{localStorage.setItem('hayeren-match-intro-'+sig,'1')}catch{}overlay.remove();busy=false;schedule(250)},{once:true});
}
function scan(){
  if(busy||document.querySelector('.hlg-overlay')||!matchingScreen()) return;
  const items=extract();if(items.length<2) return;
  const sig=signature(items);if(sig===lastSig&&localStorage.getItem('hayeren-match-intro-'+sig)==='1') return;
  const k=known(),unseen=items.filter(x=>!k.has(key(x.hy)));
  if(!unseen.length){try{localStorage.setItem('hayeren-match-intro-'+sig,'1')}catch{}return}
  show(unseen).catch(()=>{busy=false});
}
function schedule(delay=140){clearTimeout(timer);timer=setTimeout(()=>requestAnimationFrame(scan),delay)}
new MutationObserver(()=>schedule()).observe(document.documentElement,{childList:true,subtree:true});
document.addEventListener('DOMContentLoaded',()=>schedule(60));setTimeout(()=>schedule(0),500);setTimeout(()=>schedule(0),1500);
})();</script>`;

function inject(chunk,res){
  try{const type=String(res.getHeader('content-type')||'').toLowerCase();if(!type.includes('text/html')||chunk==null)return chunk;const isBuffer=Buffer.isBuffer(chunk);let text=isBuffer?chunk.toString('utf8'):String(chunk);if(text.includes('hayeren-learning-guard-runtime'))return chunk;text=text.includes('</body>')?text.replace('</body>',guardUi+'</body>'):text+guardUi;res.removeHeader('content-length');return isBuffer?Buffer.from(text):text}catch{return chunk}
}
function wrap(listener){if(typeof listener!=='function')return listener;return function learningGuard(req,res){try{const u=new URL(req.url||'/','http://localhost');if(req.method==='GET'&&!u.pathname.startsWith('/api/')&&!u.pathname.startsWith('/health')&&!u.pathname.startsWith('/media/')&&!u.pathname.startsWith('/sw')&&!u.pathname.startsWith('/manifest')){const end=res.end.bind(res);res.end=function(chunk,encoding,callback){return end(inject(chunk,res),encoding,callback)}}}catch{}return listener.call(this,req,res)}}
http.createServer=function patched(options,listener){if(typeof options==='function'||options==null)return previousCreateServer(wrap(options));return previousCreateServer(options,wrap(listener))};
console.log('LEARNING_GUARD_READY mode=teach-before-match-v3-throttled');
