// Hayeren 10 performance bootstrap.
// Adds an app-shell service worker so repeat Telegram opens can render immediately
// from the last successful Hayeren page while Render wakes in the background.
const http=require('http');
const previousCreateServer=http.createServer.bind(http);
const CACHE_VERSION='hayeren-shell-v4-20260930';

const head=`<script id="hayeren-fastboot-head">(()=>{
try{
  if('serviceWorker' in navigator){
    const native=navigator.serviceWorker.register.bind(navigator.serviceWorker);
    navigator.serviceWorker.register=(url,opts)=>native('/sw-fast.js',Object.assign({},opts||{},{scope:'/'}));
    native('/sw-fast.js',{scope:'/'}).catch(()=>{});
  }
}catch(e){}
})();</script>`;

const sw=`const CACHE='${CACHE_VERSION}',KEY='/__hayeren_cached_app__';
self.addEventListener('install',e=>{self.skipWaiting()});
self.addEventListener('activate',e=>e.waitUntil((async()=>{
  for(const k of await caches.keys()) if(k.startsWith('hayeren-shell-')&&k!==CACHE) await caches.delete(k);
  await self.clients.claim();
  try{const r=await fetch('/?precache=1',{cache:'reload'});if(r.ok){const c=await caches.open(CACHE);await c.put(KEY,r.clone())}}catch{}
})()));
self.addEventListener('fetch',e=>{
  const req=e.request,u=new URL(req.url);
  if(req.mode==='navigate'&&u.origin===self.location.origin){
    e.respondWith((async()=>{
      const c=await caches.open(CACHE),hit=await c.match(KEY);
      if(hit){
        e.waitUntil(fetch(req).then(async r=>{if(r.ok)await c.put(KEY,r.clone())}).catch(()=>{}));
        return hit;
      }
      const r=await fetch(req);if(r.ok)await c.put(KEY,r.clone());return r;
    })());
    return;
  }
  if(req.method==='GET'&&u.origin===self.location.origin&&u.pathname.startsWith('/media/')){
    e.respondWith((async()=>{const c=await caches.open(CACHE),hit=await c.match(req);if(hit)return hit;const r=await fetch(req);if(r.ok)await c.put(req,r.clone());return r})());
  }
});`;

function inject(chunk,res){
  try{
    const type=String(res.getHeader('content-type')||'').toLowerCase();
    if(!type.includes('text/html')||chunk==null)return chunk;
    const isBuffer=Buffer.isBuffer(chunk);let text=isBuffer?chunk.toString('utf8'):String(chunk);
    if(!text.includes('hayeren-fastboot-head')) text=text.includes('<head>')?text.replace('<head>','<head>'+head):head+text;
    res.removeHeader('content-length');
    return isBuffer?Buffer.from(text):text;
  }catch{return chunk}
}
function wrap(listener){
  if(typeof listener!=='function')return listener;
  return function performanceRouter(req,res){
    try{
      const u=new URL(req.url||'/','http://localhost');
      if(u.pathname==='/sw-fast.js'){
        res.writeHead(200,{'Content-Type':'application/javascript; charset=utf-8','Cache-Control':'no-cache','Service-Worker-Allowed':'/'});
        return res.end(sw);
      }
      if(req.method==='GET'&&!u.pathname.startsWith('/api/')&&!u.pathname.startsWith('/health')&&!u.pathname.startsWith('/media/')&&!u.pathname.startsWith('/sw')&&!u.pathname.startsWith('/manifest')){
        const end=res.end.bind(res);res.end=function(chunk,encoding,callback){return end(inject(chunk,res),encoding,callback)};
      }
    }catch{}
    return listener.call(this,req,res);
  }
}
http.createServer=function patched(options,listener){if(typeof options==='function'||options==null)return previousCreateServer(wrap(options));return previousCreateServer(options,wrap(listener))};
console.log('HAYEREN_PERFORMANCE_READY cache='+CACHE_VERSION);
