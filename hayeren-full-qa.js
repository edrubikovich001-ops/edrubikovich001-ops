const http=require('http');
const APP='https://hayeren-v21-live.onrender.com/';
const BOOT='https://wxurfzmcghwvrcadnvjl.supabase.co/functions/v1/hayeren-app/';
const TR='https://hayeren-offline-translator.onrender.com';
const SECRET=process.env.HAYEREN_OFFLINE_SECRET||'';

async function get(url,opt={},timeout=15000){
  const c=new AbortController(),t=setTimeout(()=>c.abort(),timeout),ts=Date.now();
  try{
    const r=await fetch(url,{...opt,signal:c.signal,redirect:'follow'});
    const body=await r.text();
    return {status:r.status,type:r.headers.get('content-type')||'',ms:Date.now()-ts,body,url:r.url};
  }finally{clearTimeout(t)}
}
async function translate(text,source,target){
  const r=await get(TR+'/translate',{
    method:'POST',
    headers:{'content-type':'application/json','x-hayeren-secret':SECRET},
    body:JSON.stringify({text,source,target})
  },12000);
  let j={};try{j=JSON.parse(r.body)}catch{}
  return {text,source,target,status:r.status,ms:r.ms,...j};
}
const ARM=/[Ա-Ֆա-ֆև]/,CYR=/[А-Яа-яЁё]/;
function okScript(x){return x.target==='hy'?ARM.test(x.translated||''):CYR.test(x.translated||'')}
function norm(s){return String(s||'').toLowerCase().replace(/[\s.,!?;:()«»“”"']/g,'')}

async function run(){
  const out={at:new Date().toISOString(),checks:{},translations:[]};
  try{
    const root=await get(APP);
    out.checks.root={ok:root.status===200&&/text\/html/.test(root.type)&&/^\s*<!doctype html/i.test(root.body),status:root.status,type:root.type,ms:root.ms,bytes:Buffer.byteLength(root.body)};
    const required=['lesson_48_final','MASTERY LEAGUE','TranslatorScreen','ArmeniaScreen','WordsScreen','ReviewScreen','ProfileScreen','GuideScreen','hayeren-engine'];
    out.checks.bundle={ok:required.every(x=>root.body.includes(x)),missing:required.filter(x=>!root.body.includes(x)),static21:root.body.includes('static-cdn-21.2'),noRenderLoading:!/APPLICATION LOADING|START BUILDING ON RENDER TODAY/.test(root.body),noRawEscaped:!/&lt;!doctype html&gt;/i.test(root.body)};
    out.checks.persistence={ok:root.body.includes('localStorage')&&root.body.includes('experienceVersion')&&root.body.includes('lessonProgress')&&root.body.includes('activeSession'),experienceV4:root.body.includes('EXPERIENCE_VERSION = 4')||root.body.includes('experienceVersion:4')||root.body.includes('experienceVersion')};
  }catch(e){out.checks.root={ok:false,error:String(e)}}

  try{
    const h=await get(APP+'health.json');let j={};try{j=JSON.parse(h.body)}catch{}
    out.checks.staticHealth={ok:h.status===200&&j.ok===true,status:h.status,body:j};
  }catch(e){out.checks.staticHealth={ok:false,error:String(e)}}

  try{
    const b=await get(BOOT);out.checks.bootstrap={ok:b.status===200&&/text\/html/.test(b.type)&&/^\s*<!doctype html/i.test(b.body),status:b.status,type:b.type,ms:b.ms,finalUrl:b.url,noRenderLoading:!/APPLICATION LOADING|START BUILDING ON RENDER TODAY/.test(b.body)};
  }catch(e){out.checks.bootstrap={ok:false,error:String(e)}}

  try{
    const h=await get(TR+'/health');let j={};try{j=JSON.parse(h.body)}catch{}
    out.checks.translatorHealth={ok:h.status===200&&j.ok===true&&j.version==='1.6',status:h.status,ms:h.ms,body:j};
  }catch(e){out.checks.translatorHealth={ok:false,error:String(e)}}

  const tests=[
    ['тигр','ru','hy','Վագր'],['тигр','ru','hy','Վագր'],['аптека','ru','hy','Դեղատուն'],
    ['кошка','ru','hy','Կատու'],['собака','ru','hy','Շուն'],['врач','ru','hy','Բժիշկ'],
    ['больница','ru','hy','Հիվանդանոց'],['машина','ru','hy','Մեքենա'],['школа','ru','hy','Դպրոց'],
    ['книга','ru','hy','Գիրք'],['любовь','ru','hy','Սեր'],
    ['Где находится ближайшая аптека?','ru','hy','դեղատ'],
    ['Мне нужен врач','ru','hy','բժիշկ'],
    ['Я хочу поехать в Ереван завтра утром.','ru','hy',null],
    ['Сколько стоит билет до центра?','ru','hy',null],
    ['Сегодня у меня хороший день, а завтра я хочу поехать в центр города.','ru','hy','քաղաք'],
    ['Վագր','hy','ru','Тигр'],['Դեղատուն','hy','ru','Аптека'],['Բժիշկ','hy','ru','Врач'],
    ['Շնորհակալություն','hy','ru','Спасибо'],['Բարի օր','hy','ru','Добрый']
  ];
  for(const [text,source,target,hint] of tests){
    try{
      const x=await translate(text,source,target);
      const semantic=hint?norm(x.translated).includes(norm(hint)):true;
      x.ok=x.status===200&&okScript(x)&&semantic;
      x.semantic=semantic;
      out.translations.push(x);
    }catch(e){out.translations.push({text,source,target,ok:false,error:String(e)})}
  }
  const times=out.translations.filter(x=>x.ok&&Number.isFinite(x.ms)).map(x=>x.ms);
  out.checks.translatorSuite={
    ok:out.translations.every(x=>x.ok),
    passed:out.translations.filter(x=>x.ok).length,
    total:out.translations.length,
    maxMs:times.length?Math.max(...times):null,
    avgMs:times.length?Math.round(times.reduce((a,b)=>a+b,0)/times.length):null
  };

  out.ok=Object.values(out.checks).every(x=>x&&x.ok!==false)&&out.checks.translatorSuite.ok;
  console.log('HAYEREN_FULL_QA '+JSON.stringify(out));
  return out;
}
let last=null;
run().then(x=>last=x).catch(e=>{last={ok:false,error:String(e)};console.error('HAYEREN_FULL_QA_FATAL',e)});
http.createServer((req,res)=>{
  res.setHeader('content-type','application/json; charset=utf-8');
  res.end(JSON.stringify(last||{ok:false,status:'running'}));
}).listen(process.env.PORT||10000,'0.0.0.0');
