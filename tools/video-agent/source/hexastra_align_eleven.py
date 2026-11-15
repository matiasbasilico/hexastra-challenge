import argparse, json, re, unicodedata, difflib, subprocess
from pathlib import Path
import numpy as np
from faster_whisper import WhisperModel

ROOT=Path(__file__).resolve().parent.parent
def norm(s):
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD',s.lower()).encode('ascii','ignore').decode())
NUMBERS=[('probemos yo','probemoslo'),('open street map','openstreetmap'),('openstreet map','openstreetmap'),('exastra','hexastra'),('72 7','727'),('70 9','709'),('setenta y dos coma siete','727'),('sesenta y cinco','65'),('setenta coma nueve','709'),('sesenta','60'),('catorce','14'),('cuatro','4'),('cinco','5'),('cien','100'),('quince','15'),('cero','0'),('dos','2'),('un','1'),('una','1')]
def canonical(seq):
    out=[];spans=[];i=0
    while i<len(seq):
        found=False
        for literal,number in NUMBERS:
            pat=literal.split()
            if seq[i:i+len(pat)]==pat:
                out.append(number);spans.append((i,i+len(pat)-1));i+=len(pat);found=True;break
        if not found:out.append(seq[i]);spans.append((i,i));i+=1
    return out,spans
def run(c): return subprocess.run(c,check=True,capture_output=True)
def main():
    p=argparse.ArgumentParser();p.add_argument('voice');p.add_argument('source');a=p.parse_args()
    out=ROOT/'build'/'elevenlabs'/a.voice;out.mkdir(parents=True,exist_ok=True)
    src=Path(a.source);wpath=out/'words.json'
    if not wpath.exists():
        model=WhisperModel('small',device='cpu',compute_type='int8',cpu_threads=6)
        decoded=run(['ffmpeg','-v','error','-i',str(src),'-f','f32le','-ar','16000','-ac','1','-']).stdout
        segs,info=model.transcribe(np.frombuffer(decoded,dtype=np.float32),language=__import__('os').environ.get('HEXASTRA_VIDEO_LANGUAGE','es'),word_timestamps=True,beam_size=5,vad_filter=False,initial_prompt='HexAstra, Arsia Mons, Laguna de Antofagasta, OpenStreetMap, MODIS, LOLA, MOLA, Diviner, TASI.')
        words=[]
        for s in segs:
            print(f'{s.start:.1f} {s.text}',flush=True)
            words += [dict(word=w.word,start=w.start,end=w.end) for w in s.words]
        wpath.write_text(json.dumps(words,ensure_ascii=False,indent=2))
    words=json.loads(wpath.read_text())
    g=json.loads((ROOT/'scripts/guion_quieta.json').read_text())
    phrases=[];t=0
    for shot in g['planos']:
        for f in shot['frases']:
            txt=f['texto']
            for k,v in g['pronunciacion'].items():txt=txt.replace(k,v)
            phrases.append(dict(text=txt,t=round(t+f['at'],3)))
        t+=shot['dur']
    expected=[];ranges=[]
    for f in phrases:
        start=len(expected);expected += canonical([norm(w) for w in f['text'].split() if norm(w)])[0]
        ranges.append((start,len(expected)))
    actual,actual_spans=canonical([norm(w['word']) for w in words])
    matcher=difflib.SequenceMatcher(None,expected,actual,autojunk=False)
    mapping={i+k:j+k for i,j,n in matcher.get_matching_blocks() for k in range(n)}
    print('Token match',len(mapping),'/',len(expected),flush=True)
    report=[]
    pcm=run(['ffmpeg','-v','error','-i',str(src),'-f','f32le','-ar','48000','-ac','1','-']).stdout
    audio=np.frombuffer(pcm,dtype=np.float32);mix=np.zeros(180*48000,dtype=np.float32)
    for idx,(f,(lo,hi)) in enumerate(zip(phrases,ranges)):
        matched=[(k,mapping[k]) for k in range(lo,hi) if k in mapping]
        if not matched:raise RuntimeError('Unmatched phrase '+str(idx))
        first,last=actual_spans[matched[0][1]][0],actual_spans[matched[-1][1]][1]
        if matched[0][0]!=lo or matched[-1][0]!=hi-1:
            print('CHECK boundary',idx+1,matched[0][0]-lo,hi-1-matched[-1][0],flush=True)
        # Extend unmatched edge words conservatively using neighboring matches.
        first=max(0,first-(matched[0][0]-lo));last=min(len(words)-1,last+(hi-1-matched[-1][0]))
        st=max(0,words[first]['start']-.045);en=words[last]['end']+.065
        if first:st=max(st,(words[first-1]['end']+words[first]['start'])/2)
        if last+1<len(words):en=min(en,(words[last]['end']+words[last+1]['start'])/2)
        clip=audio[int(st*48000):int(en*48000)]
        window=(phrases[idx+1]['t'] if idx+1<len(phrases) else 179.65)-f['t']-.12
        speed=max(1,len(clip)/48000/window)
        proc=subprocess.run(['ffmpeg','-v','error','-f','f32le','-ar','48000','-ac','1','-i','-','-af',f'atempo={speed:.8f},afade=t=in:d=0.008,areverse,afade=t=in:d=0.015,areverse','-f','f32le','-ar','48000','-ac','1','-'],input=clip.tobytes(),capture_output=True,check=True)
        fitted=np.frombuffer(proc.stdout,dtype=np.float32)
        start=int(f['t']*48000);mix[start:start+len(fitted)]+=fitted
        report.append(dict(id=idx+1,text=f['text'],source_start=st,source_end=en,target_start=f['t'],window=window,speed=speed,matched=len(matched),tokens=hi-lo))
        print(f'{idx+1:02d} src {st:.2f}-{en:.2f} -> {f["t"]:.2f} speed {speed:.3f} {f["text"]}',flush=True)
    target=out/'voz-sincronizada.wav'
    subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ar','48000','-ac','1','-i','-','-c:a','pcm_s16le',str(target)],input=mix.tobytes(),check=True)
    (out/'alignment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(target,flush=True)
if __name__=='__main__':main()
