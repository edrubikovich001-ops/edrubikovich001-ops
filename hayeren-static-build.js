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
     const r=await fetch(SOURCE+'?static-build='+Date.now(),{redirect:'follow',headers:{'user-agent':'Hayeren-Static-Builder/21'}});
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


function patchLessonEngine(html){
  const re=/await ungzip\('([^']+)'\)/g;
  let patched=0;
  html=html.replace(re,(full,b64)=>{
    let dec;
    try{dec=zlib.gunzipSync(Buffer.from(b64,'base64')).toString('utf8')}catch{return full}
    const start=dec.indexOf('define("lib/exercises"');
    const end=dec.indexOf('define("lib/state"',start);
    if(start<0||end<0)return full;
    dec=dec.slice(0,start)+"define(\"lib/exercises\", [\"require\", \"exports\", \"lib/content\", \"lib/review\"], function (require, exports, content_1, review_1) {\n    \"use strict\";\n    Object.defineProperty(exports, \"__esModule\", { value: true });\n    exports.makeQuestion = makeQuestion;\n    exports.buildLessonQuestions = buildLessonQuestions;\n    exports.buildReviewQuestions = buildReviewQuestions;\n    exports.buildDailyPractice = buildDailyPractice;\n    exports.dueCount = dueCount;\n    const ENGINE_VERSION = 'HAYEREN_ENGINE_V21';\n    const shuffle = (a) => { const x = [...a]; for (let i = x.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [x[i], x[j]] = [x[j], x[i]]; } return x; };\n    const sample = (a, n) => shuffle(a).slice(0, n);\n    const scopedPool = (allowedIds) => {\n        if (!allowedIds || !allowedIds.length) return content_1.vocabulary;\n        return [...new Set(allowedIds)].map(id => content_1.vocabById.get(id)).filter(Boolean);\n    };\n    const alternatives = (item, n = 2, allowedIds = null) => {\n        const pool = scopedPool(allowedIds).filter(v => v.id !== item.id);\n        return sample(pool.filter(v => v.category === item.category), n * 2)\n            .concat(sample(pool.filter(v => v.category !== item.category), n * 2));\n    };\n    const uniqueChoices = (correct, candidates, n = 3) => {\n        const others = [...new Set(candidates.filter(x => x !== correct))];\n        return shuffle([correct, ...sample(others, Math.max(0, n - 1))]);\n    };\n    function makeQuestion(vocabularyId, type, seed = '', allowedIds = null) {\n        const item = content_1.vocabById.get(vocabularyId);\n        if (!item) return null;\n        if (type === 'assemble' && !item.hy.includes(' ')) type = 'flashcard';\n        const id = vocabularyId + '-' + type + '-' + seed + '-' + Math.random().toString(36).slice(2, 8);\n        if (type === 'learn') return { id, type, vocabularyId };\n        if (type === 'translation') return { id, type, vocabularyId, options: uniqueChoices(item.ru, alternatives(item, 5, allowedIds).map(v => v.ru)) };\n        if (type === 'armenian-choice') return { id, type, vocabularyId, options: uniqueChoices(item.hy, alternatives(item, 5, allowedIds).map(v => v.hy)), prompt: item.ru };\n        if (type === 'transcription-choice') return { id, type, vocabularyId, options: uniqueChoices(item.hy, alternatives(item, 5, allowedIds).map(v => v.hy)), prompt: item.ruSound };\n        if (type === 'audio') return { id, type, vocabularyId, options: uniqueChoices(item.ru, alternatives(item, 5, allowedIds).map(v => v.ru)) };\n        if (type === 'matching') {\n            const ids = shuffle([item.id, ...alternatives(item, 4, allowedIds).map(v => v.id)]).filter((x, i, a) => a.indexOf(x) === i).slice(0, 4);\n            return { id, type, vocabularyId, pairIds: ids };\n        }\n        if (type === 'dialogue') return { id, type, vocabularyId, options: uniqueChoices(item.hy, alternatives(item, 5, allowedIds).map(v => v.hy)), prompt: dialoguePrompt(item) };\n        return { id, type, vocabularyId };\n    }\n    function dialoguePrompt(item) {\n        if (item.category === 'greetings') return 'Как сказать: «' + item.ru + '»?';\n        if (item.category === 'restaurant') return 'Вы в кафе. Как сказать: «' + item.ru + '»?';\n        if (item.category === 'shopping') return 'Вы в магазине. Как сказать: «' + item.ru + '»?';\n        if (item.category === 'transport') return 'Вы в городе. Как сказать: «' + item.ru + '»?';\n        return 'Как сказать: «' + item.ru + '»?';\n    }\n    const reviewTypes = ['translation', 'dialogue', 'audio', 'flashcard'];\n    const standardLessonTypes = ['translation', 'dialogue'];\n    const isBeginnerLesson = (ids) => {\n        const prefixes = ['greeting_', 'feelings_', 'intro_', 'polite_'];\n        return ids.length > 0 && ids.every(id => prefixes.some(p => id.startsWith(p)));\n    };\n    function buildLessonQuestions(state, newIds) {\n        const beginner = isBeginnerLesson(newIds);\n        const learned = Object.values(state.vocabularyProgress).filter(p => p.correct + p.incorrect > 0 && !newIds.includes(p.vocabularyId));\n        const knownIds = learned.map(p => p.vocabularyId);\n        const due = learned.filter(p => (0, review_1.isDue)(p)).sort((a, b) => (0, review_1.reviewPriority)(b, state.mistakes[b.vocabularyId]?.count || 0) - (0, review_1.reviewPriority)(a, state.mistakes[a.vocabularyId]?.count || 0));\n        const warmCount = Math.min(2, Math.floor(newIds.length / 4), due.length);\n        const warmTypes = beginner ? ['translation'] : reviewTypes;\n        const warm = warmCount ? sample(due, warmCount).map((p, i) => makeQuestion(p.vocabularyId, warmTypes[i % warmTypes.length], 'warm', knownIds)).filter(Boolean) : [];\n        const core = [];\n        const blockSize = 3;\n        const seenIds = [];\n        for (let start = 0; start < newIds.length; start += blockSize) {\n            const block = newIds.slice(start, start + blockSize);\n            block.forEach((vid, i) => core.push(makeQuestion(vid, 'learn', 'learn-' + (start + i), seenIds)));\n            seenIds.push(...block);\n            const types = beginner ? ['translation'] : standardLessonTypes;\n            block.forEach((vid, i) => core.push(makeQuestion(vid, types[(start + i) % types.length], 'practice-' + (start + i), seenIds)));\n        }\n        if (newIds.length >= 4) core.push(makeQuestion(newIds[0], 'matching', 'pairs-final', seenIds));\n        const controlPool = [...newIds];\n        const control = sample(newIds, Math.min(4, newIds.length)).map((vid, i) => makeQuestion(vid, beginner ? 'translation' : standardLessonTypes[i % standardLessonTypes.length], 'control', controlPool)).filter(Boolean);\n        return [...warm, ...core.filter(Boolean), ...control];\n    }\n    function buildReviewQuestions(state, limit = 12) {\n        const allKnown = Object.values(state.vocabularyProgress).filter(p => p.correct + p.incorrect > 0);\n        const knownIds = allKnown.map(p => p.vocabularyId);\n        const due = allKnown.filter(p => (0, review_1.isDue)(p));\n        const weak = allKnown.filter(p => p.mastery < 65);\n        const pool = [...new Map([...due, ...weak].map(p => [p.vocabularyId, p])).values()]\n            .sort((a, b) => (0, review_1.reviewPriority)(b, state.mistakes[b.vocabularyId]?.count || 0) - (0, review_1.reviewPriority)(a, state.mistakes[a.vocabularyId]?.count || 0)).slice(0, limit);\n        return pool.map((p, i) => makeQuestion(p.vocabularyId, reviewTypes[i % reviewTypes.length], 'review', knownIds)).filter(Boolean);\n    }\n    function buildDailyPractice(state) {\n        const all = Object.values(state.vocabularyProgress).filter(p => p.correct + p.incorrect > 0);\n        const knownIds = all.map(p => p.vocabularyId);\n        const problematic = all.filter(p => (state.mistakes[p.vocabularyId]?.resolved === false) || p.mastery < 45).sort((a, b) => a.mastery - b.mastery).slice(0, 2);\n        const due = all.filter(p => (0, review_1.isDue)(p) && !problematic.some(x => x.vocabularyId === p.vocabularyId)).slice(0, 3);\n        const recent = [...all].filter(p => p.lastReviewedAt).sort((a, b) => new Date(b.lastReviewedAt).getTime() - new Date(a.lastReviewedAt).getTime()).filter(p => ![...problematic, ...due].some(x => x.vocabularyId === p.vocabularyId)).slice(0, 2);\n        const old = [...all].filter(p => p.lastReviewedAt).sort((a, b) => new Date(a.lastReviewedAt).getTime() - new Date(b.lastReviewedAt).getTime()).filter(p => ![...problematic, ...due, ...recent].some(x => x.vocabularyId === p.vocabularyId)).slice(0, 1);\n        const pool = [...problematic, ...due, ...recent, ...old];\n        return pool.map((p, i) => makeQuestion(p.vocabularyId, reviewTypes[i % reviewTypes.length], 'daily', knownIds)).filter(Boolean);\n    }\n    function dueCount(state) { return Object.values(state.vocabularyProgress).filter(p => (0, review_1.isDue)(p)).length; }\n});"+' '+dec.slice(end);

    const beforeFlow2=dec;
    dec=dec.replace("next.activeSession?.kind === 'lesson' && next.activeSession.flowVersion !== 2","next.activeSession?.kind === 'lesson' && next.activeSession.flowVersion !== 3");
    dec=dec.replace("flowVersion: 2, totalSteps: questions.length","flowVersion: 3, totalSteps: questions.length");
    if(dec===beforeFlow2) throw new Error('Flow version patch failed');
    const out=zlib.gzipSync(Buffer.from(dec,'utf8'),{level:9}).toString('base64');
    patched++;
    return full.replace(b64,out);
  });
  if(patched!==1)throw new Error('Engine patch failed. patched='+patched);
  console.log('ENGINE_PATCH_OK version=21.2');
  return html;
}

function patch(html){
 html=patchLessonEngine(html);
 // Do not register the old dynamic-origin boot service worker in the static shell.
 html=html.replace(/<script[^>]*id=["']hayeren-fastboot-head["'][^>]*>[\s\S]*?<\/script>/gi,'');
 html=html.replace(/<script[^>]*id=["']hayeren-origin-cleanup["'][^>]*>[\s\S]*?<\/script>/gi,'');
 html=html.replace(/<style[^>]*id=["']hayeren-learning-guard-css["'][^>]*>[\s\S]*?<\/style>/gi,'');
 html=html.replace(/<script[^>]*id=["']hayeren-learning-guard-runtime["'][^>]*>[\s\S]*?<\/script>/gi,'');

 // Images are loaded directly from Wikimedia CDN; no sleeping backend in the visual path.
 for(const [key,file] of Object.entries(mediaFiles)){
   html=html.split('/media/'+key).join(commons(file));
 }

 const boot=`<script id="hayeren-static-edge-15">(()=>{
   window.__HAYEREN_ENTRY__='static-cdn-21.2';
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
 html=html.replace('</head>','<meta name="hayeren-entry" content="static-cdn-21.2"><meta name="hayeren-engine" content="21"></head>');
 return html;
}

(async()=>{
 const html=patch(await fetchRealApp());
 if(!html.includes('lesson_48_final')||!html.includes('MASTERY LEAGUE')||!html.includes('static-cdn-21.2')||!html.includes('hayeren-engine'))throw new Error('Static validation failed');
 fs.rmSync(OUT,{recursive:true,force:true});fs.mkdirSync(OUT,{recursive:true});
 fs.writeFileSync(path.join(OUT,'index.html'),html,'utf8');
 fs.writeFileSync(path.join(OUT,'health.json'),JSON.stringify({ok:true,entry:'static-cdn-21.2',lesson48:true,mastery:true,generatedAt:new Date().toISOString()}));
 console.log('HAYEREN_STATIC_READY bytes='+Buffer.byteLength(html));
})().catch(e=>{console.error(e);process.exit(1)});
