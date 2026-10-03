const fs=require('fs');
const path=require('path');

const SOURCE='https://hayeren-v9-live.onrender.com/';
const OUT=path.join(__dirname,'hayeren-static');
const EDGE_TRANSLATE='https://wxurfzmcghwvrcadnvjl.supabase.co/functions/v1/hayeren-translate';
const sleep=ms=>new Promise(r=>setTimeout(r,ms));

const mediaFiles={
 ararat:'View of Mount Ararat from Yerevan.jpg',
 yerevan:'Yerevan, Republic Square, Armenia.jpg',
 geghard:'Geghard Monastery, Armenia.jpg',
 sevan:'Lake Sevan with Sevanavank.jpg',
 erebuni:'Erebuni fortress in Armenia.jpg',
 alphabet:'Armenian Alphabet Monument.JPG',
 duduk:'ArmenianDuduk-image.jpg',
 lavash:'Lavash in a tonir oven Armenia 2026.jpg',
 khachkar:'Armenian Khatchkar.jpg',
 kochari:'Kochari - Armenian folk dance.png'
};

function commons(name){return `https://commons.wikimedia.org/wiki/Special:Redirect/file/${encodeURIComponent(name)}?width=1280`}

async function fetchRealApp(){
 let last='';
 for(let i=0;i<24;i++){
   try{
     const r=await fetch(SOURCE+'?static-build='+Date.now(),{redirect:'follow',headers:{'user-agent':'Hayeren-Static-Builder/15'}});
     const text=await r.text(); last=text;
     const type=r.headers.get('content-type')||'';
     const real=r.status===200&&type.includes('text/html')&&text.includes('lesson_48_final')&&text.includes('MASTERY LEAGUE')&&!/APPLICATION LOADING|START BUILDING ON RENDER TODAY|INCOMING HTTP REQUEST DETECTED/i.test(text);
     if(real){console.log('STATIC_CAPTURE_OK bytes='+Buffer.byteLength(text));return text}
     console.log('STATIC_CAPTURE_WAIT status='+r.status+' type='+type+' bytes='+text.length);
   }catch(e){console.log('STATIC_CAPTURE_RETRY '+e.message)}
   await sleep(Math.min(1200,350+i*75));
 }
 throw new Error('Could not capture real Hayeren app. lastBytes='+last.length);
}

function patch(html){
 // Do not register the old dynamic-origin boot service worker in the static shell.
 html=html.replace(/<script[^>]*id=["']hayeren-fastboot-head["'][^>]*>[\s\S]*?<\/script>/gi,'');
 html=html.replace(/<script[^>]*id=["']hayeren-origin-cleanup["'][^>]*>[\s\S]*?<\/script>/gi,'');

 // Images are loaded directly from Wikimedia CDN; no sleeping backend in the visual path.
 for(const [key,file] of Object.entries(mediaFiles)){
   html=html.split('/media/'+key).join(commons(file));
 }

 const boot=`<script id="hayeren-static-edge-15">(()=>{
   window.__HAYEREN_ENTRY__='static-cdn-15';
   try{if('serviceWorker' in navigator){navigator.serviceWorker.getRegistrations().then(rs=>rs.forEach(r=>r.unregister())).catch(()=>{})}}catch{}
   const edge='${EDGE_TRANSLATE}',nativeFetch=window.fetch.bind(window);
   const sameTranslate=u=>{try{const x=new URL(u,location.href);return x.pathname==='/api/translate'||x.pathname.endsWith('/api/translate')}catch{return false}};
   window.fetch=async function(input,init={}){
     const raw=typeof input==='string'?input:(input&&input.url)||'';
     if(sameTranslate(raw)){
       try{
         const u=new URL(raw,location.href);let body={};
         if(String(init.method||'GET').toUpperCase()==='GET'){
           body={text:u.searchParams.get('text')||u.searchParams.get('q')||'',source:u.searchParams.get('source')||'ru',target:u.searchParams.get('target')||'hy'};
         }else{
           try{body=JSON.parse(typeof init.body==='string'?init.body:'{}')}catch{body={}}
         }
         body.initData=(window.Telegram&&window.Telegram.WebApp&&window.Telegram.WebApp.initData)||'';
         const c=new AbortController(),tm=setTimeout(()=>c.abort(),5000);
         try{return await nativeFetch(edge,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body),signal:c.signal,cache:'no-store'})}finally{clearTimeout(tm)}
       }catch(e){return new Response(JSON.stringify({error:'Перевод временно недоступен'}),{status:503,headers:{'content-type':'application/json; charset=utf-8'}})}
     }
     return nativeFetch(input,init);
   };
 })();</script>`;

 if(html.includes('<head>')) html=html.replace('<head>','<head>'+boot);
 else html=boot+html;
 // Explicit version marker used by QA.
 html=html.replace('</head>','<meta name="hayeren-entry" content="static-cdn-15"></head>');
 return html;
}

(async()=>{
 const html=patch(await fetchRealApp());
 if(!html.includes('lesson_48_final')||!html.includes('MASTERY LEAGUE')||!html.includes('static-cdn-15'))throw new Error('Static validation failed');
 fs.rmSync(OUT,{recursive:true,force:true});fs.mkdirSync(OUT,{recursive:true});
 fs.writeFileSync(path.join(OUT,'index.html'),html,'utf8');
 fs.writeFileSync(path.join(OUT,'health.json'),JSON.stringify({ok:true,entry:'static-cdn-15',lesson48:true,mastery:true,generatedAt:new Date().toISOString()}));
 console.log('HAYEREN_STATIC_READY bytes='+Buffer.byteLength(html));
})().catch(e=>{console.error(e);process.exit(1)});
