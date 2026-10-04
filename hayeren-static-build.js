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
     const r=await fetch(SOURCE+'?static-build='+Date.now(),{redirect:'follow',headers:{'user-agent':'Hayeren-Static-Builder/19'}});
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
   window.__HAYEREN_ENTRY__='static-cdn-19';
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


 const beginnerV19=`<script id="hayeren-beginner-v19">(()=>{
 const ARM=/[Ա-Ֆա-ֆև]/, CYR=/[А-Яа-яЁё]/;
 const clean=s=>String(s||'').replace(/\\s+/g,' ').trim();
 const norm=s=>clean(s).toLowerCase().replace(/[?!.,;:()«»“”"'։՞՜՛]/g,'').replace(/ё/g,'е');
 const SOUND={
  'барев':'Привет','барев дзез':'Здравствуйте','бари луйс':'Доброе утро','бари ереко':'Добрый вечер',
  'бари гишер':'Спокойной ночи','инчпес ек':'Как вы?','инчпес эк':'Как вы?','инчпес ес':'Как ты?',
  'вонц ес':'Как дела?','вoнц ес':'Как дела?','лав ем':'У меня всё хорошо','лав эм':'У меня всё хорошо',
  'лав':'Хорошо','шат лав':'Очень хорошо','ват че':'Неплохо','шноракалутюн':'Спасибо','шноракалуцюн':'Спасибо',
  'шат шноракалутюн':'Большое спасибо','хндрем':'Пожалуйста','нерецек':'Извините','кнерек':'Извините',
  'цтесутюн':'До свидания','айо':'Да','воч':'Нет','инч э дзер ануны':'Как вас зовут?',
  'инч э ко ануны':'Как тебя зовут?','им анунн э':'Меня зовут…','им ануны':'Меня зовут…',
  'вортехиц ек':'Откуда вы?','вортехиц ес':'Откуда ты?','урах ем цанотанал':'Приятно познакомиться',
  'ес эл':'Я тоже','бари галуст':'Добро пожаловать'
 };
 const HY={
  'Բարև':'Привет','Բարև ձեզ':'Здравствуйте','Բարի լույս':'Доброе утро','Բարի երեկո':'Добрый вечер','Բարի գիշեր':'Спокойной ночи',
  'Ինչպե՞ս եք':'Как вы?','Ինչպե՞ս ես':'Как ты?','Ո՞նց ես':'Как дела?','Լավ եմ':'У меня всё хорошо','Լավ':'Хорошо',
  'Շատ լավ':'Очень хорошо','Վատ չէ':'Неплохо','Շնորհակալություն':'Спасибо','Շատ շնորհակալություն':'Большое спасибо',
  'Խնդրեմ':'Пожалуйста','Ներեցեք':'Извините','Կներեք':'Извините','Ցտեսություն':'До свидания','Այո':'Да','Ոչ':'Нет',
  'Ի՞նչ է ձեր անունը':'Как вас зовут?','Ի՞նչ է քո անունը':'Как тебя зовут?','Քո անունն ի՞նչ է':'Как тебя зовут?',
  'Իմ անունն է':'Меня зовут…','Որտեղի՞ց եք':'Откуда вы?','Որտեղի՞ց ես':'Откуда ты?','Ուրախ եմ ծանոթանալու':'Приятно познакомиться',
  'Ես էլ':'Я тоже','Բարի գալուստ':'Добро пожаловать'
 };
 const BANK=['Привет','Здравствуйте','Доброе утро','Добрый вечер','Как вы?','Как дела?','Спасибо','До свидания','Хорошо','Пожалуйста','Извините'];
 const meaningSound=s=>SOUND[norm(s)]||'';
 const meaningHy=s=>HY[clean(s)]||Object.entries(HY).find(([k])=>norm(k)===norm(s))?.[1]||'';
 const getLesson=()=>{const m=clean(document.body&&document.body.innerText).match(/Урок\\s+(\\d+)/i);return m?Number(m[1]):99};
 function findQuestionText(){
   const w=document.createTreeWalker(document.body||document.documentElement,NodeFilter.SHOW_TEXT);
   let n; while(n=w.nextNode()){
     const t=clean(n.nodeValue);
     if(t==='Что написано по-армянски?'||t==='Какое армянское выражение звучит так?'||t==='Выбери армянское написание')return n.parentElement;
   }
   return null;
 }
 function cardFor(head){
   let el=head;
   for(let i=0;i<12&&el;i++,el=el.parentElement){
     const bs=[...el.querySelectorAll('button,[role="button"]')].filter(b=>ARM.test(clean(b.innerText||b.textContent)));
     if(bs.length>=2)return {card:el,buttons:bs.slice(0,4)};
   }
   return null;
 }
 function chooseDistractors(correct,prompt,count){
   let h=0;for(const ch of prompt)h=(h*31+ch.charCodeAt(0))>>>0;
   const arr=BANK.filter(x=>x!==correct),out=[];
   for(let i=0;i<arr.length&&out.length<count;i++){const x=arr[(h+i*3)%arr.length];if(!out.includes(x))out.push(x)}
   return out;
 }
 function fix(){
   if(getLesson()>4)return;
   const head=findQuestionText(); if(!head)return;
   const found=cardFor(head); if(!found)return;
   const {card,buttons}=found;
   const lines=String(card.innerText||card.textContent||'').split(/\\n+/).map(clean).filter(Boolean);
   let prompt='';
   const labelIndex=lines.findIndex(x=>/ЗВУЧИТ РУССКИМИ БУКВАМИ/i.test(x));
   if(labelIndex>=0&&lines[labelIndex+1])prompt=lines[labelIndex+1];
   if(!prompt){
     for(const line of lines){if(meaningSound(line)){prompt=line;break}}
   }
   if(!prompt)return;
   const correctMeaning=meaningSound(prompt); if(!correctMeaning)return;
   let correctIndex=-1;
   const parsed=buttons.map((b,i)=>{
     const ls=String(b.innerText||b.textContent||'').split(/\\n+/).map(clean).filter(Boolean);
     const hy=ls.find(x=>ARM.test(x))||'';
     const tr=ls.find(x=>CYR.test(x)&&!ARM.test(x))||'';
     if(tr&&norm(tr)===norm(prompt))correctIndex=i;
     if(correctIndex<0&&meaningHy(hy)===correctMeaning)correctIndex=i;
     return {b,hy,tr};
   });
   if(correctIndex<0)return;
   const distractors=chooseDistractors(correctMeaning,prompt,buttons.length-1);
   let di=0;
   parsed.forEach((x,i)=>{
     const label=i===correctIndex?correctMeaning:distractors[di++];
     if(clean(x.b.textContent)!==label){
       x.b.textContent=label;
       x.b.setAttribute('aria-label',label);
       x.b.dataset.hayerenV19='1';
     }
   });
   if(clean(head.textContent)!=='Что значит «'+prompt+'»?')head.textContent='Что значит «'+prompt+'»?';
   const all=[...card.querySelectorAll('*')];
   for(const el of all){
     if(el.children.length===0&&/ЗВУЧИТ РУССКИМИ БУКВАМИ/i.test(clean(el.textContent)))el.textContent='ФРАЗА:';
   }
   card.dataset.hayerenBeginnerV19='1';
 }
 let scheduled=false;
 const run=()=>{scheduled=false;try{fix()}catch(e){}};
 const schedule=()=>{if(scheduled)return;scheduled=true;setTimeout(()=>requestAnimationFrame(run),20)};
 new MutationObserver(schedule).observe(document.documentElement,{childList:true,subtree:true,characterData:true});
 document.addEventListener('DOMContentLoaded',schedule);
 setInterval(fix,250);setTimeout(fix,30);setTimeout(fix,300);setTimeout(fix,1000);
 window.__HAYEREN_BEGINNER_FIX__='19.0';
 })();<\\/script>`;

 if(html.includes('<head>')) html=html.replace('<head>','<head>'+boot+beginnerV18+beginnerV19); else html=boot+html;
 html=html.replace('</head>','<meta name="hayeren-entry" content="static-cdn-19"></head>');
 return html;
}

(async()=>{
 const html=patch(await fetchRealApp());
 if(!html.includes('lesson_48_final')||!html.includes('MASTERY LEAGUE')||!html.includes('static-cdn-19')||!html.includes('hayeren-no-answer-leak-css')||!html.includes('beginnerMeaningQuiz')||!html.includes('hayeren-beginner-v18')||!html.includes('hayeren-beginner-v19'))throw new Error('Static validation failed');
 fs.rmSync(OUT,{recursive:true,force:true});fs.mkdirSync(OUT,{recursive:true});
 fs.writeFileSync(path.join(OUT,'index.html'),html,'utf8');
 fs.writeFileSync(path.join(OUT,'health.json'),JSON.stringify({ok:true,entry:'static-cdn-19',lesson48:true,mastery:true,noAnswerLeak:true,beginnerMeaningQuiz:true,beginnerV18:true,beginnerV19:true,generatedAt:new Date().toISOString()}));
 console.log('HAYEREN_STATIC_READY bytes='+Buffer.byteLength(html));
})().catch(e=>{console.error(e);process.exit(1)});
