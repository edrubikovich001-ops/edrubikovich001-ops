const http=require('http');
const {URL}=require('url');

const VERSION='9.0';
const UPSTREAM=process.env.UPSTREAM||'https://hayeren-v8-live.onrender.com';
const PUBLIC_URL=process.env.PUBLIC_URL||'';
const BOT_TOKEN=process.env.BOT_TOKEN||'';
const cache=new Map();

const media={
  ararat:'https://commons.wikimedia.org/wiki/Special:Redirect/file/Mount%20Ararat%20from%20Yerevan.JPG?width=1200',
  yerevan:'https://commons.wikimedia.org/wiki/Special:Redirect/file/Republic%20Square%20Yerevan.jpg?width=1200',
  geghard:'https://commons.wikimedia.org/wiki/Special:Redirect/file/Geghard%20Monastery%2C%20Armenia.jpg?width=1200',
  sevan:'https://commons.wikimedia.org/wiki/Special:Redirect/file/Lake%20Sevan%2C%20Armenia.jpg?width=1200',
  erebuni:'https://commons.wikimedia.org/wiki/Special:Redirect/file/Erebuni%20fortress%20in%20Armenia.jpg?width=1200',
  alphabet:'https://commons.wikimedia.org/wiki/Special:Redirect/file/Armenian%20Alphabet%20Monument.JPG?width=1200',
  duduk:'https://commons.wikimedia.org/wiki/Special:Redirect/file/ArmenianDuduk-image.jpg?width=1200',
  lavash:'https://commons.wikimedia.org/wiki/Special:Redirect/file/Lavash%20arm%C3%A9nien.jpg?width=1200',
  khachkar:'https://commons.wikimedia.org/wiki/Special:Redirect/file/Armenian%20Khatchkar.jpg?width=1200'
};

const fallback=Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 675"><defs><linearGradient id="g" x1="0" x2="1"><stop stop-color="#6f4037"/><stop offset="1" stop-color="#bd684e"/></linearGradient></defs><rect width="1200" height="675" fill="url(#g)"/><circle cx="1010" cy="130" r="78" fill="#efb56f" opacity=".9"/><path d="M0 675 330 205l155 190 118-139 352 419z" fill="#4c2d28"/><text x="64" y="590" fill="white" font-size="54" font-family="system-ui">Հայաստան · Armenia</text></svg>`);

function chooseImage(text){
  const t=String(text||'').toLowerCase();
  if(/эребун|эрибун|урарт/.test(t))return'/media/erebuni';
  if(/алфавит|маштоц|письмен/.test(t))return'/media/alphabet';
  if(/дудук/.test(t))return'/media/duduk';
  if(/лаваш|хлеб|тонир/.test(t))return'/media/lavash';
  if(/хачкар|крест-кам|крест кам/.test(t))return'/media/khachkar';
  if(/севан|озер|природ/.test(t))return'/media/sevan';
  if(/гегард|монастыр|эчмиадзин|звартноц|архитект/.test(t))return'/media/geghard';
  if(/ереван|столиц|площад/.test(t))return'/media/yerevan';
  return'/media/ararat';
}

const inject=`<style id="hayeren-v9-media">
.armenia-hero:before{background-image:linear-gradient(90deg,rgba(28,20,17,.76),rgba(28,20,17,.42) 55%,rgba(28,20,17,.08)),url('/media/ararat')!important;background-size:cover!important;background-position:center!important}
.article-card .v7-photo,.article-detail-photo{background:#e9ded4!important}
.v9-photo-note{font-size:9px;color:#8b7c70;margin:7px 14px 13px;line-height:1.25}
</style><script id="hayeren-v9-media-runtime">(()=>{const pick=${chooseImage.toString()};function apply(){document.querySelectorAll('.article-card').forEach(c=>{const i=c.querySelector('.v7-photo');if(i){const src=pick(c.textContent);if(i.getAttribute('src')!==src)i.setAttribute('src',src);i.onerror=()=>{i.onerror=null;i.src='/media/ararat'}}});const d=document.querySelector('.article-screen');if(d){const i=d.querySelector('.article-detail-photo');if(i){const src=pick(d.textContent);if(i.getAttribute('src')!==src)i.setAttribute('src',src);i.onerror=()=>{i.onerror=null;i.src='/media/ararat'}}}document.querySelectorAll('.article-card').forEach(c=>{if(c.dataset.v9credit)return;c.dataset.v9credit='1';const n=document.createElement('div');n.className='v9-photo-note';n.textContent='Фото: Wikimedia Commons · свободные лицензии';const img=c.querySelector('.v7-photo');if(img)img.insertAdjacentElement('afterend',n)})}new MutationObserver(apply).observe(document.documentElement,{subtree:true,childList:true});document.addEventListener('DOMContentLoaded',apply);setTimeout(apply,250);setTimeout(apply,900);window.__HAYEREN_MEDIA_VERSION__='9.0'})();</script>`;

async function serveMedia(name,res){
  if(cache.has(name)){const c=cache.get(name);res.writeHead(200,{'Content-Type':c.type,'Cache-Control':'public,max-age=86400','Access-Control-Allow-Origin':'*'});return res.end(c.body)}
  const url=media[name];
  if(!url){res.writeHead(404);return res.end('not found')}
  try{
    const r=await fetch(url,{redirect:'follow',headers:{'User-Agent':'Hayeren/9.0 educational app','Accept':'image/avif,image/webp,image/apng,image/*,*/*;q=0.8'}});
    if(!r.ok)throw new Error('image '+r.status);
    const type=r.headers.get('content-type')||'image/jpeg';
    if(!type.startsWith('image/'))throw new Error('bad type '+type);
    const body=Buffer.from(await r.arrayBuffer());
    if(body.length<5000)throw new Error('image too small');
    cache.set(name,{type,body});
    res.writeHead(200,{'Content-Type':type,'Content-Length':body.length,'Cache-Control':'public,max-age=86400','Access-Control-Allow-Origin':'*','X-Hayeren-Image':name});
    return res.end(body);
  }catch(e){
    console.error('media',name,e.message);
    res.writeHead(200,{'Content-Type':'image/svg+xml; charset=utf-8','Content-Length':fallback.length,'Cache-Control':'no-store','X-Hayeren-Image-Fallback':'1'});
    return res.end(fallback);
  }
}

async function forward(req,res){
  const target=new URL(req.url,UPSTREAM);
  const headers={...req.headers};
  delete headers.host;delete headers['content-length'];delete headers.connection;
  const chunks=[];for await(const c of req)chunks.push(c);
  const body=chunks.length?Buffer.concat(chunks):undefined;
  const r=await fetch(target,{method:req.method,headers,body:(req.method==='GET'||req.method==='HEAD')?undefined:body,redirect:'manual'});
  const outHeaders={};
  r.headers.forEach((v,k)=>{if(!['content-encoding','content-length','transfer-encoding','connection'].includes(k.toLowerCase()))outHeaders[k]=v});
  let data=Buffer.from(await r.arrayBuffer());
  const type=r.headers.get('content-type')||'';
  if(req.method==='GET'&&type.includes('text/html')){
    let text=data.toString('utf8');
    text=text.includes('</body>')?text.replace('</body>',inject+'</body>'):text+inject;
    data=Buffer.from(text);
    outHeaders['content-type']='text/html; charset=utf-8';
    outHeaders['cache-control']='no-store,max-age=0';
    outHeaders['x-hayeren-version']=VERSION;
  }
  res.writeHead(r.status,outHeaders);res.end(data);
}

async function setTelegramMenu(){
  if(!BOT_TOKEN||!PUBLIC_URL)return;
  try{
    const r=await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/setChatMenuButton`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({menu_button:{type:'web_app',text:'Открыть приложение',web_app:{url:PUBLIC_URL}}})});
    const j=await r.json();console.log('Telegram menu',j.ok?'updated':'failed',j.description||'');
  }catch(e){console.error('Telegram menu update',e.message)}
}

const server=http.createServer(async(req,res)=>{
  try{
    const u=new URL(req.url,'http://localhost');
    if(u.pathname==='/health'){res.writeHead(200,{'Content-Type':'application/json','Cache-Control':'no-store'});return res.end(JSON.stringify({ok:true,version:VERSION,upstream:UPSTREAM,media:Object.keys(media)}))}
    if(u.pathname.startsWith('/media/'))return serveMedia(u.pathname.split('/').pop(),res);
    return await forward(req,res);
  }catch(e){console.error(e);res.writeHead(502,{'Content-Type':'text/plain; charset=utf-8'});res.end('Hayeren proxy error')}
});
server.listen(process.env.PORT||10000,'0.0.0.0',()=>{console.log('Hayeren v9 production proxy ready');setTelegramMenu()});
