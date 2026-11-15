from pathlib import Path
import json,sys,subprocess,importlib.util,copy
import cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent.parent;D=R/'build/elevenlabs/ignacio-pitch-refinado'
im=Image.open(D/'dimensiones.png').convert('RGB');dr=ImageDraw.Draw(im);dr.rectangle((0,0,1919,300),fill=(7,9,21))
f=ImageFont.truetype(str(R/'build/fonts/Montserrat.ttf'),60);f.set_variation_by_name('Bold')
dr.text((110,110),'TASI · Índice creado por HexAstra',font=f,fill=(246,247,254))
f=ImageFont.truetype(str(R/'build/fonts/OpenSans.ttf'),26);f.set_variation_by_name('Regular')
dr.text((112,205),'Cinco dimensiones para entender qué se parece y qué cambia.',font=f,fill=(168,175,199));im.save(D/'dimensiones.png')
sys.argv=['render','--guion','guion_pitch_refinado.json','--salida','hexastra-pitch-3min-ignacio-refinado.mp4']
spec=importlib.util.spec_from_file_location('montaje',R/'scripts/montar_v2.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
anchors=[(0,0),(2.3,5),(11.1,9.5),(13.5,14.5),(19,17.2),(23.5,21.7),(28,28)]
class Demo:
 def __init__(self,path):
  q=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height','-of','json',str(path)],text=True))['streams'][0]
  self.w,self.h=q['width'],q['height'];self.n=-1;self.frame=None;self.retime=Path(path).name=='modo-facil.mp4'
  self.p=subprocess.Popen(['ffmpeg','-v','error','-i',str(path),'-vf','fps=30','-f','rawvideo','-pix_fmt','bgr24','-'],stdout=subprocess.PIPE)
 def at(self,t):
  if self.retime:
   for (t0,s0),(t1,s1) in zip(anchors,anchors[1:]):
    if t<=t1:t=s0+(s1-s0)*(t-t0)/(t1-t0);break
  want=int(min(t,27.99 if self.retime else 21.99)*30+1e-6)
  while self.n<want:
   buf=self.p.stdout.read(self.w*self.h*3)
   if len(buf)<self.w*self.h*3:break
   self.frame=np.frombuffer(buf,np.uint8).reshape(self.h,self.w,3);self.n+=1
  return self.frame
m.Demo=Demo
for p in m.G['planos']:
 if p['id']=='demo-facil':
  p['src']='modo-facil.mp4';p['ref']=1280;p['cam']=[[0,640,360,1280]]
  p['retiming_anchors']=anchors;p.pop('archivo_en_build',None);p.pop('primer_fundido_incluido',None)
render=m.render_plano
result=next(p for p in m.G['planos'] if p['id']=='resultado')
def corrected(p,t,fuentes,cache):
 if p['id']=='demo-avanzada' and t<.633333333:
  prev=render(result,0,fuentes,cache)
  if t<.3:return prev
  frame=render(p,t,fuentes,cache);a=m.ease((t-.3)/(.333333333));return cv2.addWeighted(frame,a,prev,1-a,0)
 return render(p,t,fuentes,cache)
m.render_plano=corrected
(R/'scripts/guion_pitch_refinado.json').write_text(json.dumps(m.G,ensure_ascii=False,indent=2))
print(m.video(m.planos_con_inicio()),flush=True)
