// Loaded before hayeren-v9-assets.js.
// Translation order for arbitrary text: self-hosted Hayeren offline model first,
// then Google JSON / Supabase Edge / Google mobile / Lingva as safety fallbacks.
const nativeFetch = globalThis.fetch.bind(globalThis);
const OFFLINE_URL = process.env.HAYEREN_OFFLINE_URL || '';
const OFFLINE_SECRET = process.env.HAYEREN_OFFLINE_SECRET || '';
const EDGE_URL = process.env.HAYEREN_TRANSLATE_EDGE_URL || '';
const EDGE_SECRET = process.env.HAYEREN_TRANSLATE_EDGE_SECRET || '';
const INSTANCES = ['https://lingva.lunar.icu','https://translate.plausibility.cloud'];
const UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Mobile/15E148 Safari/604.1';

function validTranslation(text,target){text=String(text||'').trim();if(!text)return false;if(target==='hy')return /[Ա-Ֆա-ֆև]/.test(text);if(target==='ru')return /[А-Яа-яЁё]/.test(text);return true}
function decodeHtml(value){const named={amp:'&',lt:'<',gt:'>',quot:'"',apos:"'",nbsp:' '};return String(value||'').replace(/<br\s*\/?>/gi,'\n').replace(/<[^>]*>/g,'').replace(/&#(\d+);/g,(_,n)=>String.fromCodePoint(Number(n))).replace(/&#x([0-9a-f]+);/gi,(_,n)=>String.fromCodePoint(parseInt(n,16))).replace(/&([a-z]+);/gi,(m,n)=>named[n.toLowerCase()]??m).replace(/\s+/g,' ').trim()}

async function offlineTranslate(source,target,query){
  if(!OFFLINE_URL||!OFFLINE_SECRET)throw new Error('offline translator not configured');
  const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),22000);
  try{
    const response=await nativeFetch(OFFLINE_URL,{method:'POST',signal:controller.signal,headers:{'Content-Type':'application/json','Accept':'application/json','x-hayeren-secret':OFFLINE_SECRET,'User-Agent':'Hayeren/10 Render'},body:JSON.stringify({text:query,source,target})});
    if(!response.ok)throw new Error(`offline HTTP ${response.status}`);
    const data=await response.json();const translated=String(data&&data.translated||'').trim();
    if(!validTranslation(translated,target))throw new Error('offline invalid translation');
    console.warn(`TRANSLATOR_OFFLINE_OK provider=${String(data.provider||'Hayeren Offline')} pair=${source}|${target} ms=${Number(data.elapsedMs||0)}`);
    return translated;
  }finally{clearTimeout(timer)}
}

async function edgeTranslate(source,target,query){
  if(!EDGE_URL||!EDGE_SECRET)throw new Error('edge fallback not configured');
  const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),9000);
  try{
    const response=await nativeFetch(EDGE_URL,{method:'POST',signal:controller.signal,headers:{'Content-Type':'application/json','Accept':'application/json','x-hayeren-secret':EDGE_SECRET,'User-Agent':'Hayeren/10 Render'},body:JSON.stringify({text:query,source,target})});
    if(!response.ok)throw new Error(`edge HTTP ${response.status}`);
    const data=await response.json();const translated=String(data&&data.translated||'').trim();
    if(!validTranslation(translated,target))throw new Error('edge invalid translation');
    console.warn(`TRANSLATOR_EDGE_OK provider=${String(data.provider||'edge')} pair=${source}|${target}`);
    return translated;
  }finally{clearTimeout(timer)}
}

async function googleMobileTranslate(source,target,query){const url=new URL('https://translate.google.com/m');url.searchParams.set('sl',source);url.searchParams.set('tl',target);url.searchParams.set('q',query);const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),7000);try{const response=await nativeFetch(url,{redirect:'follow',signal:controller.signal,headers:{'Accept':'text/html,application/xhtml+xml','Accept-Language':'ru-RU,ru;q=0.9,en;q=0.7','User-Agent':UA}});if(!response.ok)throw new Error(`mobile HTTP ${response.status}`);const html=await response.text();const match=html.match(/<div[^>]*class=["'][^"']*result-container[^"']*["'][^>]*>([\s\S]*?)<\/div>/i);const translated=decodeHtml(match&&match[1]);if(!validTranslation(translated,target))throw new Error('mobile invalid translation');console.warn(`TRANSLATOR_MOBILE_OK pair=${source}|${target}`);return translated}finally{clearTimeout(timer)}}

async function lingvaTranslate(source,target,query){let lastError;for(const base of INSTANCES){const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),5000);try{const url=`${base}/api/v1/${encodeURIComponent(source)}/${encodeURIComponent(target)}/${encodeURIComponent(query)}`;const response=await nativeFetch(url,{signal:controller.signal,headers:{'Accept':'application/json','User-Agent':UA}});if(!response.ok)throw new Error(`${base} HTTP ${response.status}`);const data=await response.json();const translated=String(data&&data.translation||'').trim();if(!validTranslation(translated,target))throw new Error(`${base} invalid translation`);console.warn(`TRANSLATOR_LINGVA_OK host=${new URL(base).host} pair=${source}|${target}`);return translated}catch(error){lastError=error;console.warn(`TRANSLATOR_LINGVA_RETRY host=${new URL(base).host} reason=${error&&error.message}`)}finally{clearTimeout(timer)}}throw lastError||new Error('Lingva unavailable')}

function googleShape(translated,query,source,provider){return new Response(JSON.stringify([[[translated,query,null,null,10]],null,source]),{status:200,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Hayeren-Translator':provider}})}

// Free Render services can sleep. As soon as the main app wakes, wake the
// translator too so it is normally ready before the user opens the translator UI.
if(OFFLINE_URL){
  setTimeout(async()=>{try{const health=new URL('/health',OFFLINE_URL);const c=new AbortController();const t=setTimeout(()=>c.abort(),25000);try{const r=await nativeFetch(health,{signal:c.signal,headers:{'User-Agent':'Hayeren/10 warmup'}});console.warn(`TRANSLATOR_OFFLINE_WARMUP status=${r.status}`)}finally{clearTimeout(t)}}catch(e){console.warn(`TRANSLATOR_OFFLINE_WARMUP_RETRY reason=${e&&e.message}`)}},250);
}

globalThis.fetch=async function hayerenTranslatorFallback(input,init){
  const raw=typeof input==='string'?input:input instanceof URL?input.href:(input&&input.url)||'';
  if(!/translate\.googleapis\.com\/translate_a\/single/.test(raw))return nativeFetch(input,init);
  const url=new URL(raw),query=url.searchParams.get('q')||'',source=(url.searchParams.get('sl')||'ru').slice(0,2),target=(url.searchParams.get('tl')||'hy').slice(0,2);

  // Our own model is the stable path and has no third-party quota. Keep it first.
  try{return googleShape(await offlineTranslate(source,target,query),query,source,'hayeren-offline')}catch(offlineError){
    console.warn(`TRANSLATOR_OFFLINE_RETRY reason=${offlineError&&offlineError.message}`);
    let primary,primaryError;
    try{primary=await nativeFetch(input,init);if(primary.ok)return primary;if(![403,429,500,502,503,504].includes(primary.status))return primary}catch(error){primaryError=error}
    try{return googleShape(await edgeTranslate(source,target,query),query,source,'supabase-edge-fallback')}catch(edgeError){
      console.warn(`TRANSLATOR_EDGE_RETRY reason=${edgeError&&edgeError.message}`);
      try{return googleShape(await googleMobileTranslate(source,target,query),query,source,'google-mobile-fallback')}catch(mobileError){
        console.warn(`TRANSLATOR_MOBILE_RETRY reason=${mobileError&&mobileError.message}`);
        try{return googleShape(await lingvaTranslate(source,target,query),query,source,'lingva-fallback')}catch(lingvaError){
          console.error(`TRANSLATOR_FALLBACK_EXHAUSTED offline=${offlineError&&offlineError.message} primary=${primary?primary.status:(primaryError&&primaryError.message)||'network'} edge=${edgeError&&edgeError.message} mobile=${mobileError&&mobileError.message} lingva=${lingvaError&&lingvaError.message}`);
          if(primary)return primary;throw primaryError||offlineError||edgeError||mobileError||lingvaError;
        }
      }
    }
  }
};
