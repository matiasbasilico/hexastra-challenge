from pathlib import Path
import json,subprocess,sys,importlib.util,shutil
R=Path(__file__).resolve().parent.parent;D=R/'build/elevenlabs/ignacio-pitch-refinado';OUT=R/'hexastra-pitch-3min-ignacio-refinado.mp4'
report=json.loads((D/'alignment.json').read_text())
sys.argv=['export','--guion','guion_pitch_refinado.json','--salida',OUT.name]
spec=importlib.util.spec_from_file_location('montaje',R/'scripts/montar_v2.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
mix=m.mezcla(D/'voz-sincronizada.wav',R/'build/v2/musica.wav')
subprocess.run(['ffmpeg','-v','error','-y','-i',str(R/'build/v2/video-hexastra-pitch-3min-ignacio-refinado.mp4'),'-i',str(mix),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-t','180','-movflags','+faststart','-metadata','title=HexAstra · Ignacio · Pitch refinado','-metadata','comment=Locución generada con IA en ElevenLabs. TASI es una propuesta del equipo, no un índice oficial de NASA. PDF actualizado, presentación quieta, demo real. No afirma ahorros medidos ni primacía histórica.',str(OUT)],check=True)
def ts(s):
 n=round(s*1000);return f'{n//3600000:02}:{n//60000%60:02}:{n//1000%60:02},{n%1000:03}'
def clean(s):return s.replace('Ársia','Arsia').replace('Mars Ódisi','Mars Odyssey').replace('Diváiner','Diviner')
sub=[];narr=[]
for i,f in enumerate(report,1):
 text=clean(f.get('onscreen',f['text']));end=f['t']+f['duration'];sub.append(f'{i}\n{ts(f["t"])} --> {ts(end)}\n{text}\n');narr.append(f'[{ts(f["t"])}] {text}')
OUT.with_suffix('.es.srt').write_text('\n'.join(sub))
(R/'guion-ignacio-refinado.txt').write_text('HEXASTRA · PITCH REFINADO · IGNACIO · 180 SEGUNDOS\n\n'+'\n\n'.join(narr)+'\n\nFuente de Arsia Mons: NASA, Seven Possible Cave Skylights on Mars, 21/09/2007.\nhttps://science.nasa.gov/resource/seven-possible-cave-skylights-on-mars/\n')
g=json.loads((R/'scripts/guion_pitch_refinado.json').read_text());t=0;actions=[]
for p in g['planos']:
 actions.append(f'{ts(t)} - {ts(t+p["dur"])} | {p["id"]} | {p["src"]}');t+=p['dur']
(D/'acciones-180s.txt').write_text('\n'.join(actions))
print(OUT,flush=True)
