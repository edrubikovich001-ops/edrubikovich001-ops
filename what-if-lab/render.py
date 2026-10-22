import requests,subprocess,os,json,concurrent.futures,random,pathlib,time
from urllib.parse import urlparse
P=pathlib.Path("."); D=P/"sources"; T=P/"parts"; O=P/"output"
for x in (D,T,O):x.mkdir(exist_ok=True)
R=[("coast","33776188","ocean"),("ocean","26562909","ocean"),("skyline","25397823","city"),("earth","30683870","space"),("snow","31018227","climate"),("traffic","13567267","city"),("desert","20028844","climate"),("storm","32581958","storm"),("coast2","34494297","ocean"),("wilderness","35837647","climate"),("rocks","6031873","ocean"),("evening","6606212","city"),("sunrise","30209132","sun"),("waves","32348481","storm"),("clouds","34754920","climate"),("forest","4216162","storm"),("mountain","8025555","sun"),("turbines","9320544","city")]
N=[("spin","https://svs.gsfc.nasa.gov/vis/a000000/a001300/a001375/a001375.mp4","planet"),("stop","https://svs.gsfc.nasa.gov/vis/a000000/a001300/a001376/a001376.mp4","planet"),("winds","https://svs.gsfc.nasa.gov/vis/a000000/a003900/a003935/windsst_comp_1080p.mp4","atmosphere"),("pace","https://svs.gsfc.nasa.gov/vis/a000000/a005200/a005259/PACE_EarthDay2024_1080p60.mp4","planet"),("gulf","https://svs.gsfc.nasa.gov/vis/a000000/a004800/a004802/gulf_stream_to_fleet_final01_1080p60.webm","ocean"),("ice","https://svs.gsfc.nasa.gov/vis/a000000/a004800/a004871/SeaLevelRise_PineIsland_ECCO_flows_fast.mp4","ocean"),("day","https://svs.gsfc.nasa.gov/vis/a000000/a002700/a002782/a002782a_720x480.mp4","sun"),("night","https://svs.gsfc.nasa.gov/vis/a030000/a031100/a031120/haifa_swipe_1080p30_2.mp4","sun")]
TOP=[("space","planet"),("city","planet"),("city","planet"),("city","planet"),("storm","atmosphere"),("storm","atmosphere"),("climate","planet"),("ocean","ocean"),("city","ocean"),("climate","planet"),("ocean","ocean"),("sun","sun"),("sun","sun"),("sun","sun"),("climate","planet"),("storm","atmosphere"),("ocean","ocean"),("climate","planet"),("city","planet"),("city","sun"),("climate","planet"),("climate","planet"),("sun","planet"),("space","planet"),("climate","planet"),("city","planet"),("sun","sun"),("space","planet"),("city","planet"),("space","planet")]
def cmd(*args): 
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 if p.returncode:raise RuntimeError(p.stderr[-900:])
 return p.stdout
def info(p):
 try:
  m=json.loads(cmd("ffprobe","-v","error","-show_entries","format=duration:stream=codec_type,width,height","-of","json",str(p)))
  v=next(x for x in m["streams"] if x["codec_type"]=="video")
  return float(m["format"]["duration"]) if v["width"]>=400 and v["height"]>=270 else 0
 except Exception:return 0
def get(x):
 kind,name,url,tag=x
 p=D/(name+(".webm" if ".webm" in url else ".mp4"))
 if p.exists() and info(p)>5:return(kind,name,p,tag,info(p),0,url)
 try:
  for retry in range(3):
   try:
    with requests.get(url,stream=True,timeout=(25,100),headers={"User-Agent":"Mozilla/5.0"},allow_redirects=True) as r:
     r.raise_for_status()
     if "html" in r.headers.get("Content-Type",""):raise ValueError("HTML not video")
     with open(p,"wb") as f:
      size=0
      for block in r.iter_content(1024*1024):
       if block:f.write(block);size+=len(block)
       if size>750_000_000:raise ValueError("Video too large")
    break
   except Exception:
    if retry==2:raise
    time.sleep(3)
  dur=info(p)
  if dur<5:raise ValueError("Invalid media")
  print("Source ready",name,round(dur),flush=True)
  return(kind,name,p,tag,dur,0,url)
 except Exception as e:
  print("SKIPPED",name,str(e)[:100],flush=True);p.unlink(missing_ok=True)
  return None
jobs=[("R",n,"https://www.pexels.com/download/video/"+id+"/",tag) for n,id,tag in R]+[("N",n,url,tag) for n,url,tag in N]
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:src=[s for s in pool.map(get,jobs) if s]
if sum(s[0]=="R" for s in src)<10 or sum(s[0]=="N" for s in src)<6:raise SystemExit("Too few licensed videos; no slideshow fallback.")
S=[list(x) for x in src];last=None;shots=[];map_=[]
for chapter,(rtag,ntag) in enumerate(TOP):
 for step in range(4):
  k="R" if step%2==0 else "N";tag=rtag if k=="R" else ntag
  good=[s for s in S if s[0]==k and s[3]==tag and s[1]!=last and s[5]+5.1<s[4]]
  if not good:good=[s for s in S if s[0]==k and s[1]!=last and s[5]+5.1<s[4]]
  if not good:good=[s for s in S if s[0]==k and s[1]!=last]
  best=min(good,key=lambda s:(max(0,s[5]+5-s[4])*5,s[5]/max(s[4],1)))
  start=min(best[5],max(0,best[4]-5.03))
  best[5]+=5;last=best[1]
  shots.append((best[2],start))
  map_.append({"at":len(shots)*5-5,"kind":k,"source":best[1],"source_url":best[6],"source_start":start})
(O/"EDIT_MAP.json").write_text(json.dumps(map_,indent=2))
def segment(task):
 idx,(path,start)=task;out=T/("%03d.mp4"%idx)
 if out.exists() and abs(info(out)-5)<.15:return out
 cmd("ffmpeg","-hide_banner","-loglevel","error","-y","-ss",str(start),"-i",str(path),"-t","5","-vf","scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=24,setsar=1,format=yuv420p","-an","-c:v","libx264","-preset","veryfast","-crf","24","-g","48","-sc_threshold","0","-video_track_timescale","12288",str(out))
 return out
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for i,f in enumerate(pool.map(segment,enumerate(shots))):
  if (i+1)%20==0:print("Rendered",i+1,"/120",flush=True)
concat=O/"concat.txt";concat.write_text("".join("file '"+str((T/('%03d.mp4'%i)).resolve())+"'\n" for i in range(len(shots))))
dst=O/"WHAT_IF_LAB_10MIN_1080P_NO_VOICE.mp4"
cmd("ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat","-safe","0","-i",str(concat),"-c","copy","-movflags","+faststart",str(dst))
duration=info(dst)
if not (599.7<duration<600.3):raise SystemExit("Unexpected duration: "+str(duration))
print("SUCCESS",duration,round(dst.stat().st_size/1e6),"MB",flush=True)
