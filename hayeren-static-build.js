const fs=require('fs');
const path=require('path');
const zlib=require('zlib');

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
     const r=await fetch(SOURCE+'?static-build='+Date.now(),{redirect:'follow',headers:{'user-agent':'Hayeren-Static-Builder/18'}});
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
 html=html.replace(/<script[^>]*id=["']hayeren-fastboot-head["'][^>]*>[\s\S]*?<\/script>/gi,'');
 html=html.replace(/<script[^>]*id=["']hayeren-origin-cleanup["'][^>]*>[\s\S]*?<\/script>/gi,'');

 for(const [key,file] of Object.entries(mediaFiles)) html=html.split('/media/'+key).join(commons(file));

 const boot=`<style id="hayeren-no-answer-leak-css">.hayeren-hide-answer-hint{display:none!important}</style>
 <script id="hayeren-static-edge-16">(()=>{
   window.__HAYEREN_ENTRY__='static-stable-20';
   try{if('serviceWorker' in navigator){navigator.serviceWorker.getRegistrations().then(rs=>rs.forEach(r=>r.unregister())).catch(()=>{})}}catch{}
   const edge='${EDGE_TRANSLATE}',nativeFetch=window.fetch.bind(window);
   const sameTranslate=u=>{try{const x=new URL(u,location.href);return x.pathname==='/api/translate'||x.pathname.endsWith('/api/translate')}catch{return false}};
   window.fetch=async function(input,init={}){
     const raw=typeof input==='string'?input:(input&&input.url)||'';
     if(sameTranslate(raw)){
       try{
         const u=new URL(raw,location.href);let body={};
         if(String(init.method||'GET').toUpperCase()==='GET') body={text:u.searchParams.get('text')||u.searchParams.get('q')||'',source:u.searchParams.get('source')||'ru',target:u.searchParams.get('target')||'hy'};
         else{try{body=JSON.parse(typeof init.body==='string'?init.body:'{}')}catch{body={}}}
         body.initData=(window.Telegram&&window.Telegram.WebApp&&window.Telegram.WebApp.initData)||'';
         const c=new AbortController(),tm=setTimeout(()=>c.abort(),5000);
         try{return await nativeFetch(edge,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body),signal:c.signal,cache:'no-store'})}finally{clearTimeout(tm)}
       }catch(e){return new Response(JSON.stringify({error:'Перевод временно недоступен'}),{status:503,headers:{'content-type':'application/json; charset=utf-8'}})}
     }
     return nativeFetch(input,init);
   };

   const ARM=/[Ա-Ֆա-ֆև]/,CYR=/[А-Яа-яЁё]/;
   const clean=s=>String(s||'').replace(/\s+/g,' ').trim();
   function isTranscriptionChoiceScreen(){
     const t=clean(document.body&&document.body.innerText).toLowerCase();
     return t.includes('что написано по-армянски')||t.includes('какое армянское выражение звучит так')||t.includes('выбери армянское написание');
   }
   function hideLeakingHints(){
     document.querySelectorAll('.hayeren-hide-answer-hint').forEach(el=>el.classList.remove('hayeren-hide-answer-hint'));
     if(!isTranscriptionChoiceScreen())return;
     const choices=[...document.querySelectorAll('button,[role="button"]')].filter(el=>{const t=clean(el.innerText||el.textContent);return t.length>1&&t.length<180&&ARM.test(t)&&CYR.test(t)});
     for(const choice of choices){
       const descendants=[...choice.querySelectorAll('*')];
       let hidden=0;
       for(const el of descendants){
         const t=clean(el.innerText||el.textContent);
         if(!t||t.length>90||ARM.test(t)||!CYR.test(t))continue;
         const childHasSame=[...el.children].some(ch=>{const x=clean(ch.innerText||ch.textContent);return x&&CYR.test(x)&&!ARM.test(x)});
         if(!childHasSame){el.classList.add('hayeren-hide-answer-hint');hidden++}
       }
       choice.dataset.hayerenNoLeak=hidden?'1':'0';
     }
   }
   const meaningMap={
     'Բարև':'Привет','Բարև ձեզ':'Здравствуйте','Բարի լույս':'Доброе утро','Բարի երեկո':'Добрый вечер',
     'Ինչպե՞ս եք':'Как вы?','Ինչպե՞ս ես':'Как ты?','Ո՞նց ես':'Как дела?','Լավ եմ':'У меня всё хорошо',
     'Լավ':'Хорошо','Շատ լավ':'Очень хорошо','Վատ չէ':'Неплохо','Հիանալի':'Отлично','Իսկ դու':'А ты?',
     'Շնորհակալություն':'Спасибо','Շատ շնորհակալություն':'Большое спасибо','Խնդրեմ':'Пожалуйста',
     'Ներեցեք':'Извините','Կներեք':'Извините','Ցտեսություն':'До свидания','Այո':'Да','Ոչ':'Нет',
     'Ի՞նչ է ձեր անունը':'Как вас зовут?','Ի՞նչ է քո անունը':'Как тебя зовут?','Քո անունն ի՞նչ է':'Как тебя зовут?',
     'Իմ անունն է':'Меня зовут…','Որտեղի՞ց եք':'Откуда вы?','Որտեղի՞ց ես':'Откуда ты?',
     'Ուրախ եմ ծանոթանալու':'Приятно познакомиться','Ես էլ':'Я тоже','Բարի գալուստ':'Добро пожаловать'
   };
   const normArm=s=>clean(s).replace(/[։՞՜՛.,!?;:()«»“”"']/g,'').toLowerCase();
   const normCyr=s=>clean(s).replace(/[.,!?;:()«»“”"']/g,'').toLowerCase();
   const mapMeaning=hy=>{
     if(meaningMap[clean(hy)])return meaningMap[clean(hy)];
     const k=normArm(hy);for(const [a,r] of Object.entries(meaningMap))if(normArm(a)===k)return r;
     return '';
   };
   function beginnerMeaningQuiz(){
     const page=clean(document.body&&document.body.innerText);
     const lm=page.match(/Урок\s+(\d+)/i),lesson=lm?Number(lm[1]):99;
     if(lesson>4)return;
     const heads=[...document.querySelectorAll('h1,h2,h3,h4,p,div,span')].filter(el=>{
       const t=clean(el.textContent);
       return t==='Что написано по-армянски?'||t==='Какое армянское выражение звучит так?'||t==='Выбери армянское написание';
     });
     for(const head of heads){
       let card=head;
       for(let i=0;i<8&&card;i++,card=card.parentElement){
         const buttons=[...card.querySelectorAll('button')].filter(b=>ARM.test(b.textContent||''));
         if(buttons.length<2)continue;
         if(card.dataset.hayerenBeginnerMeaning==='1')break;
         const txt=clean(card.innerText||card.textContent);
         const m=txt.match(/ЗВУЧИТ РУССКИМИ БУКВАМИ:\s*([^\n]{2,70})/i);
         if(!m)break;
         const prompt=clean(m[1]);
         const rows=buttons.map(b=>{
           const raw=String(b.textContent||'').split(/\n+/).map(clean).filter(Boolean);
           const hy=raw.find(x=>ARM.test(x))||'';
           const tr=raw.find(x=>CYR.test(x)&&!ARM.test(x))||'';
           return {b,hy,tr,meaning:mapMeaning(hy)};
         });
         if(rows.some(x=>!x.hy||!x.meaning))break;
         card.dataset.hayerenBeginnerMeaning='1';
         head.textContent='Что значит «'+prompt+'»?';
         [...card.querySelectorAll('*')].forEach(el=>{
           if(clean(el.textContent)==='ЗВУЧИТ РУССКИМИ БУКВАМИ:')el.textContent='ФРАЗА:';
         });
         rows.forEach(({b,meaning})=>{
           b.innerHTML='<span style="display:block;font-size:20px;font-weight:750;line-height:1.25;text-align:left">'+meaning+'</span>';
           b.dataset.hayerenMeaningChoice='1';
         });
         break;
       }
     }
   }
   let scanTimer=0;
   const runFixes=()=>{hideLeakingHints();beginnerMeaningQuiz()};
   const schedule=()=>{clearTimeout(scanTimer);scanTimer=setTimeout(()=>requestAnimationFrame(runFixes),30)};
   new MutationObserver(schedule).observe(document.documentElement,{childList:true,subtree:true,characterData:true});
   document.addEventListener('DOMContentLoaded',schedule);
   setTimeout(schedule,80);setTimeout(schedule,400);setTimeout(schedule,1000);
 })();</script>`;


 const beginnerV18=`<script id="hayeren-beginner-v18">(()=>{
 const ARM=/[Ա-Ֆա-ֆև]/,CYR=/[А-Яа-яЁё]/;
 const M={
 'Բարև':'Привет','Բարև ձեզ':'Здравствуйте','Բարի լույս':'Доброе утро','Բարի երեկո':'Добрый вечер',
 'Ինչպե՞ս եք':'Как вы?','Ինչպե՞ս ես':'Как ты?','Ո՞նց ես':'Как дела?','Լավ եմ':'У меня всё хорошо',
 'Լավ':'Хорошо','Շատ լավ':'Очень хорошо','Վատ չէ':'Неплохо','Հիանալի':'Отлично','Իսկ դու':'А ты?',
 'Շնորհակալություն':'Спасибо','Շատ շնորհակալություն':'Большое спасибо','Խնդրեմ':'Пожалуйста',
 'Ներեցեք':'Извините','Կներեք':'Извините','Ցտեսություն':'До свидания','Այո':'Да','Ոչ':'Нет',
 'Ի՞նչ է ձեր անունը':'Как вас зовут?','Ի՞նչ է քո անունը':'Как тебя зовут?','Քո անունն ի՞նչ է':'Как тебя зовут?',
 'Իմ անունն է':'Меня зовут…','Որտեղի՞ց եք':'Откуда вы?','Որտեղի՞ց ես':'Откуда ты?',
 'Ուրախ եմ ծանոթանալու':'Приятно познакомиться','Ես էլ':'Я тоже','Բարի գալուստ':'Добро пожаловать'
 };
 const c=s=>String(s||'').replace(/\\s+/g,' ').trim();
 const nk=s=>c(s).replace(/[։՞՜՛.,!?;:()«»“”"']/g,'').toLowerCase();
 const meaning=hy=>{if(M[c(hy)])return M[c(hy)];const k=nk(hy);for(const a in M)if(nk(a)===k)return M[a];return''};
 function lesson(){const m=c(document.body&&document.body.innerText).match(/Урок\\s+(\\d+)/i);return m?Number(m[1]):99}
 function leafExact(txt){return [...document.querySelectorAll('h1,h2,h3,h4,p,span,div')].find(e=>e.children.length===0&&c(e.textContent)===txt)}
 function fix(){
   if(lesson()>4)return;
   const head=leafExact('Что написано по-армянски?')||leafExact('Какое армянское выражение звучит так?')||leafExact('Выбери армянское написание');
   if(!head)return;
   let card=head,opts=[];
   for(let d=0;card&&d<10;d++,card=card.parentElement){
     opts=[...card.querySelectorAll('button,[role="button"]')].filter(b=>ARM.test(c(b.innerText||b.textContent)));
     if(opts.length>=2)break;
   }
   if(!card||opts.length<2)return;
   const rows=opts.slice(0,4).map(b=>{
      const lines=String(b.innerText||b.textContent||'').split(/\\n+/).map(c).filter(Boolean);
      const hy=lines.find(x=>ARM.test(x))||c(b.textContent).match(/[Ա-Ֆա-ֆև][Ա-Ֆա-ֆև\\s՞՜՛]+/)?.[0]||'';
      const tr=lines.find(x=>CYR.test(x)&&!ARM.test(x))||'';
      return {b,hy:c(hy),tr:c(tr),ru:meaning(hy)};
   });
   if(rows.length<2||rows.some(x=>!x.hy||!x.ru))return;
   let prompt='';
   const walker=document.createTreeWalker(card,NodeFilter.SHOW_TEXT);
   let n;while(n=walker.nextNode()){
      const p=n.parentElement;if(!p||p.closest('button,[role="button"]'))continue;
      const t=c(n.nodeValue);if(!t||!CYR.test(t))continue;
      const hit=rows.find(x=>x.tr&&nk(x.tr)===nk(t));if(hit){prompt=hit.tr;break}
   }
   if(!prompt){
      const all=c(card.innerText||card.textContent);
      const hit=rows.find(x=>x.tr&&all.includes(x.tr));if(hit)prompt=hit.tr;
   }
   if(!prompt)return;
   if(c(head.textContent)!=='Что значит «'+prompt+'»?')head.textContent='Что значит «'+prompt+'»?';
   [...card.querySelectorAll('*')].forEach(el=>{if(c(el.textContent)==='ЗВУЧИТ РУССКИМИ БУКВАМИ:')el.textContent='ФРАЗА:'});
   rows.forEach(x=>{
      const now=c(x.b.innerText||x.b.textContent);
      if(now!==x.ru){
        x.b.innerHTML='<span class="hayeren-v18-meaning" style="display:block;font-size:20px;font-weight:760;line-height:1.25;text-align:left">'+x.ru+'</span>';
      }
   });
   card.dataset.hayerenV18='meaning';
 }
 setInterval(fix,150);document.addEventListener('DOMContentLoaded',fix);setTimeout(fix,30);setTimeout(fix,300);
 window.__HAYEREN_BEGINNER_FIX__='18.0';
 })();<\/script>`;


 const beginnerSafeV20="<script id=\"hayeren-beginner-safe-v20\">(()=>{\nconst CYR=/[А-Яа-яЁё]/;\nconst clean=s=>String(s||'').replace(/\\s+/g,' ').trim();\nconst norm=s=>clean(s).toLowerCase().replace(/[?!.,;:()«»“”\"'։՞՜՛]/g,'').replace(/ё/g,'е');\nconst MEAN={\n 'барев':'Привет','барев дзез':'Здравствуйте','бари луйс':'Доброе утро','бари ереко':'Добрый вечер','бари гишер':'Спокойной ночи',\n 'инчпес ек':'Как вы?','инчпес эк':'Как вы?','инчпес ес':'Как ты?','вонц ес':'Как дела?','лав ем':'У меня всё хорошо','лав эм':'У меня всё хорошо',\n 'лав':'Хорошо','шат лав':'Очень хорошо','ват че':'Неплохо','шноракалутюн':'Спасибо','шноракалуцюн':'Спасибо','шат шноракалутюн':'Большое спасибо',\n 'хндрем':'Пожалуйста','нерецек':'Извините','кнерек':'Извините','цтесутюн':'До свидания','айо':'Да','воч':'Нет',\n 'инч э дзер ануны':'Как вас зовут?','инч э ко ануны':'Как тебя зовут?','ко анунн инч э':'Как тебя зовут?','им анунн э':'Меня зовут…','им ануны':'Меня зовут…',\n 'вортехиц ек':'Откуда вы?','вортехиц ес':'Откуда ты?','урах ем цанотанал':'Приятно познакомиться','ес эл':'Я тоже','бари галуст':'Добро пожаловать'\n};\nconst BANK=['Привет','Здравствуйте','Доброе утро','Добрый вечер','Как дела?','Как вы?','Как тебя зовут?','Спасибо','Пожалуйста','До свидания','Хорошо'];\nfunction lesson(){const m=clean(document.body&&document.body.innerText).match(/Урок\\s+(\\d+)/i);return m?Number(m[1]):99}\nfunction textNodeExact(v){const w=document.createTreeWalker(document.body||document.documentElement,NodeFilter.SHOW_TEXT);let n;while(n=w.nextNode())if(clean(n.nodeValue)===v)return n.parentElement;return null}\nfunction promptFrom(card){\n const lines=String(card.innerText||card.textContent||'').split(/\\n+/).map(clean).filter(Boolean);\n const i=lines.findIndex(x=>/ЗВУЧИТ РУССКИМИ БУКВАМИ/i.test(x));if(i>=0&&lines[i+1]&&MEAN[norm(lines[i+1])])return lines[i+1];\n for(const x of lines)if(MEAN[norm(x)])return x;\n return '';\n}\nfunction distract(correct,prompt,count){let h=0;for(const c of prompt)h=(h*33+c.charCodeAt(0))>>>0;const src=BANK.filter(x=>x!==correct),out=[];for(let i=0;out.length<count&&i<src.length*2;i++){const x=src[(h+i*5)%src.length];if(!out.includes(x))out.push(x)}return out}\nfunction fix(){\n if(lesson()>4)return;\n const head=textNodeExact('Что написано по-армянски?')||textNodeExact('Какое армянское выражение звучит так?')||textNodeExact('Выбери армянское написание');if(!head)return;\n let card=head,buttons=[];\n for(let d=0;card&&d<12;d++,card=card.parentElement){buttons=[...card.querySelectorAll('button,[role=\"button\"]')].filter(b=>clean(b.innerText||b.textContent).length>0);if(buttons.length>=3)break}\n if(!card||buttons.length<2)return;\n const prompt=promptFrom(card),correct=MEAN[norm(prompt)];if(!prompt||!correct)return;\n let correctIndex=-1;\n const infos=buttons.slice(0,4).map((b,i)=>{const lines=String(b.innerText||b.textContent||'').split(/\\n+/).map(clean).filter(Boolean);const tr=lines.find(x=>CYR.test(x)&&MEAN[norm(x)])||'';if(tr&&norm(tr)===norm(prompt))correctIndex=i;return{b,tr}});\n if(correctIndex<0)return;\n const wrong=distract(correct,prompt,infos.length-1);let wi=0;\n infos.forEach((x,i)=>{const label=i===correctIndex?correct:wrong[wi++];if(clean(x.b.textContent)!==label){x.b.textContent=label;x.b.setAttribute('aria-label',label)}});\n head.textContent='Что значит «'+prompt+'»?';\n [...card.querySelectorAll('*')].forEach(el=>{if(el.children.length===0&&/ЗВУЧИТ РУССКИМИ БУКВАМИ/i.test(clean(el.textContent)))el.textContent='ФРАЗА:'});\n card.dataset.beginnerMeaning='20';\n}\nlet pending=false;const schedule=()=>{if(pending)return;pending=true;setTimeout(()=>{pending=false;try{fix()}catch{}},25)};\nnew MutationObserver(schedule).observe(document.documentElement,{childList:true,subtree:true,characterData:true});\ndocument.addEventListener('DOMContentLoaded',schedule);setInterval(fix,300);setTimeout(fix,50);setTimeout(fix,500);\nwindow.__HAYEREN_BEGINNER_SAFE__='20.0';\n})();</script>";
 if(html.includes('<head>')) html=html.replace('<head>','<head>'+boot+beginnerV18+beginnerSafeV20); else html=boot+beginnerSafeV20+html;
 html=html.replace('</head>','<meta name="hayeren-entry" content="static-cdn-18"></head>');
 return html;
}

(async()=>{


 const rawApp=await fetchRealApp();
 try{
   const payloads=[...rawApp.matchAll(/await ungzip\('([^']+)'\)/g)].map(m=>m[1]);
   console.log('ENGINE_PAYLOADS',payloads.length,payloads.map(x=>x.length).join(','));
   payloads.forEach((p,idx)=>{
     try{
       const dec=zlib.gunzipSync(Buffer.from(p,'base64')).toString('utf8');
       console.log('ENGINE_DECODED',idx,'bytes='+Buffer.byteLength(dec));
       for(const q of ['activeSession','buildLessonQuestions(','setActiveSession','questionsRef','lessonQuestions','completedSteps','currentIndex']){
         const i=dec.indexOf(q); console.log('ENGINE_Q',idx,q,'idx='+i);
         if(i>=0) console.log('ENGINE_SNIP',idx,q,dec.slice(Math.max(0,i-2500),i+6500).replace(/\n/g,' '));
       }
     }catch(e){console.log('ENGINE_DECODE_ERR',idx,String(e))}
   });
 }catch(e){console.log('ENGINE_SCAN_ERR',String(e))}
 const html=patch(rawApp);
 const probes=['До свидания','восемь','Метро','Соедини пары','Небольшая проверка','Что написано по-армянски?','lesson_1','Приветствия'];
 for(const q of probes){
   const i=html.indexOf(q);
   console.log('DEBUG_PROBE',q,'idx='+i);
   if(i>=0) console.log('DEBUG_SNIP',q,html.slice(Math.max(0,i-1800),i+4200).replace(/\n/g,' '));
 }

 if(!html.includes('lesson_48_final')||!html.includes('MASTERY LEAGUE')||!html.includes('static-cdn-18')||!html.includes('hayeren-no-answer-leak-css')||!html.includes('beginnerMeaningQuiz')||!html.includes('hayeren-beginner-v18')||!html.includes('hayeren-beginner-safe-v20'))throw new Error('Static validation failed');
 fs.rmSync(OUT,{recursive:true,force:true});fs.mkdirSync(OUT,{recursive:true});
 fs.writeFileSync(path.join(OUT,'index.html'),html,'utf8');
 fs.writeFileSync(path.join(OUT,'health.json'),JSON.stringify({ok:true,entry:'static-cdn-18',lesson48:true,mastery:true,noAnswerLeak:true,beginnerMeaningQuiz:true,beginnerV18:true,beginnerSafeV20:true,generatedAt:new Date().toISOString()}));
 console.log('HAYEREN_STATIC_READY bytes='+Buffer.byteLength(html));
})().catch(e=>{console.error(e);process.exit(1)});
