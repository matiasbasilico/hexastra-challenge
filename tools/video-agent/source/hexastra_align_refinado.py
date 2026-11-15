from pathlib import Path
import json,subprocess,importlib.util,difflib
import numpy as np
from faster_whisper import WhisperModel
R=Path(__file__).resolve().parent.parent;D=R/'build/elevenlabs/ignacio-pitch-refinado'
spec=importlib.util.spec_from_file_location('align',R/'scripts/hexastra_align_eleven.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
a.NUMBERS[:0]=[('dos mil siete','2007'),('odyssey','odisi'),('odisea','odisi'),('diviner','divainer'),('taci','tasi'),('hex astra','hexastra')]
def pcm(p,rate=48000):return np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(p),'-f','f32le','-ar',str(rate),'-ac','1','-']),np.float32)
def align(src,phrases,tag,end=179.7):
 wd=D/f'{tag}-words.json'
 if not wd.exists():
  model=WhisperModel('small',device='cpu',compute_type='int8',cpu_threads=6)
  segs,_=model.transcribe(pcm(src,16000),language=__import__('os').environ.get('HEXASTRA_VIDEO_LANGUAGE','es'),word_timestamps=True,beam_size=5,initial_prompt='HexAstra, TASI, Arsia Mons, Mars Odyssey, Diviner, MODIS, LOLA, MOLA, Laguna de Antofagasta.')
  words=[]
  for s in segs:
   print(tag,round(s.start,2),s.text,flush=True);words += [{'word':w.word,'start':w.start,'end':w.end} for w in s.words]
  wd.write_text(json.dumps(words,ensure_ascii=False,indent=2))
 words=json.loads(wd.read_text());exp=[];ranges=[]
 for f in phrases:
  start=len(exp);exp+=a.canonical([a.norm(w) for w in f['text'].split() if a.norm(w)])[0];ranges.append((start,len(exp)))
 actual,spans=a.canonical([a.norm(w['word']) for w in words]);sm=difflib.SequenceMatcher(None,exp,actual,autojunk=False);mapping={i+k:j+k for i,j,n in sm.get_matching_blocks() for k in range(n)}
 print(tag,'MATCH',len(mapping),len(exp),flush=True)
 speech=pcm(src);mix=np.zeros(180*48000,np.float32);report=[]
 for i,(f,(lo,hi)) in enumerate(zip(phrases,ranges)):
  matches=[(k,mapping[k]) for k in range(lo,hi) if k in mapping];assert matches,('No match',tag,i,f)
  first=spans[matches[0][1]][0];last=spans[matches[-1][1]][1]
  if matches[0][0]!=lo or matches[-1][0]!=hi-1:print('CHECK EDGE',tag,i+1,matches[0][0]-lo,hi-1-matches[-1][0],flush=True)
  first=max(0,first-(matches[0][0]-lo));last=min(len(words)-1,last+(hi-1-matches[-1][0]))
  st=max(0,words[first]['start']-.05);en=words[last]['end']+.075
  if first:st=max(st,(words[first-1]['end']+words[first]['start'])/2)
  if last+1<len(words):en=min(en,(words[last]['end']+words[last+1]['start'])/2)
  till=phrases[i+1]['t']-.1 if i+1<len(phrases) else end
  clip=speech[int(st*48000):int(en*48000)];speed=max(1,len(clip)/48000/(till-f['t']))
  pr=subprocess.run(['ffmpeg','-v','error','-f','f32le','-ar','48000','-ac','1','-i','-','-af',f'atempo={speed:.8f},afade=t=in:d=0.008,areverse,afade=t=in:d=0.015,areverse','-f','f32le','-ar','48000','-ac','1','-'],input=clip.tobytes(),capture_output=True,check=True)
  fitted=np.frombuffer(pr.stdout,np.float32);j=int(f['t']*48000);mix[j:j+len(fitted)]+=fitted
  report.append({**f,'id':i+1,'target_start':f['t'],'source_start':st,'source_end':en,'speed':speed,'duration':len(fitted)/48000,'matched':len(matches),'tokens':hi-lo})
  print(tag,i+1,f['t'],'speed',round(speed,3),'src',round(st,2),round(en,2),f['text'],flush=True)
 (D/f'{tag}-alignment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 return mix,report
def main():
 f=json.loads((D/'frases.json').read_text());mix,base=align(R/'inputs/audio/base.mp3',f,'base')
 hook=R/'inputs/audio/hook.wav'
 if hook.exists():
  old=pcm(hook);mix[:9*48000]=old[:9*48000]
 # Intro source is generated separately after the user's approved revision.
 intro=R/'inputs/audio/intro.mp3'
 if intro.exists():
  ff=json.loads((D/'intro-frases.json').read_text());patch,report=align(intro,ff,'intro',52.9);mix[9*48000:53*48000]=patch[9*48000:53*48000]
  base=[x for x in base if x['t']<9 or x['t']>=53]+report;base.sort(key=lambda x:x['t'])
 for p,n in zip(base,base[1:]):assert p['t']+p['duration']<=n['t']+.01,('Overlap',p,n)
 subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ar','48000','-ac','1','-i','-','-c:a','pcm_s16le',str(D/'voz-sincronizada.wav')],input=mix.tobytes(),check=True)
 (D/'alignment.json').write_text(json.dumps(base,ensure_ascii=False,indent=2));print('VOICE READY',len(base),flush=True)
if __name__=='__main__':main()
