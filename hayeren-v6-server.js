const http=require('http');
const fs=require('fs');
const zlib=require('zlib');
const path=require('path');

function loadHtml(){
  const dir=path.join(__dirname,'hayeren-v6-payload');
  const parts=['1.txt','2.txt','3.txt','4.txt'];
  for(const name of parts){
    if(!fs.existsSync(path.join(dir,name))) throw new Error(`Missing payload ${name}`);
  }
  const b64=parts.map(n=>fs.readFileSync(path.join(dir,n),'utf8').trim()).join('');
  const html=zlib.gunzipSync(Buffer.from(b64,'base64')).toString('utf8');
  if(!html.toLowerCase().startsWith('<!doctype html>')) throw new Error('Invalid Hayeren HTML payload');
  return html;
}

let html;
try { html=loadHtml(); }
catch(e){ console.error('Payload error:',e); html='<!doctype html><html lang="ru"><meta charset="utf-8"><body><h1>Hayeren обновляется</h1><p>Попробуйте открыть приложение ещё раз через минуту.</p></body></html>'; }

const manifest=JSON.stringify({
  name:'Hayeren — Армянский с нуля',
  short_name:'Hayeren',
  start_url:'/',
  display:'standalone',
  background_color:'#f7f1e9',
  theme_color:'#f7f1e9',
  lang:'ru'
});

const server=http.createServer((req,res)=>{
  if(req.url==='/health'){
    res.writeHead(200,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'});
    return res.end(JSON.stringify({ok:true,htmlBytes:Buffer.byteLength(html),v:'6',fallback:html.includes('Hayeren обновляется')}));
  }
  if(req.url==='/manifest.webmanifest'){
    res.writeHead(200,{'Content-Type':'application/manifest+json; charset=utf-8','Cache-Control':'public, max-age=3600'});
    return res.end(manifest);
  }
  res.writeHead(200,{
    'Content-Type':'text/html; charset=utf-8',
    'Cache-Control':'no-store, max-age=0',
    'X-Content-Type-Options':'nosniff',
    'Referrer-Policy':'strict-origin-when-cross-origin'
  });
  res.end(html);
});
server.listen(process.env.PORT||10000,'0.0.0.0',()=>console.log('Hayeren v6 server ready'));
