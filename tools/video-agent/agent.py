#!/usr/bin/env python3
"""Prepare and operate the reproducible HexAstra pitch-video workspace.

This runner packages the actual refined-pitch compositor/alignment sources.
It does not purchase, synthesize, or publish licensed narration automatically.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent

def load_plan(path):
    plan = json.loads(Path(path).read_text())
    total = sum(p['dur'] for p in plan['planos'])
    if abs(total - 180) > 1e-6 or plan['duracion_total_s'] != 180:
        raise ValueError('The reviewed pitch must total exactly 180 seconds.')
    for shot in plan['planos']:
        if not shot.get('video') and shot['id'] != 'gancho':
            cameras = shot.get('cam', [])
            if len(cameras) > 1 and any(c[1:] != cameras[0][1:] for c in cameras[1:]):
                raise ValueError('Presentation/image shots must remain static: ' + shot['id'])
    return plan

def phrases(plan):
    start = 0
    result = []
    for shot in plan['planos']:
        for phrase in shot.get('frases', []):
            spoken = phrase['texto']
            for before, after in plan.get('pronunciacion', {}).items():
                spoken = spoken.replace(before, after)
            result.append({'t':round(start + phrase['at'], 3), 'text':spoken, 'onscreen':phrase['texto'], 'shot':shot['id']})
        start += shot['dur']
    return result

def prepare(args):
    work = args.workdir.resolve()
    if work == HERE or HERE in work.parents:
        raise ValueError('Use an external working directory; do not generate media inside the source package.')
    plan = load_plan(args.plan)
    (work/'scripts').mkdir(parents=True, exist_ok=True)
    for path in (HERE/'source').glob('*.py'):
        shutil.copy2(path, work/'scripts'/path.name)
    (work/'scripts/guion_pitch_refinado.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2))
    for folder in ['inputs/audio','inputs/demos','build/fonts','build/v2/shots','build/pdf-nuevo/slides-video','build/elevenlabs/ignacio-pitch-refinado']:
        (work/folder).mkdir(parents=True, exist_ok=True)
    data = work/'build/elevenlabs/ignacio-pitch-refinado'
    text = phrases(plan)
    (data/'frases.json').write_text(json.dumps(text, ensure_ascii=False, indent=2))
    (data/'texto-elevenlabs.txt').write_text('\n\n'.join(p['text'] for p in text)+'\n')
    shutil.copy2(HERE/'assets/dimensions.es.png',data/'dimensiones.png')
    if args.pdf:
        shutil.copy2(args.pdf, work/'inputs/presentation.pdf')
        subprocess.run(['pdfinfo',str(work/'inputs/presentation.pdf')],check=True)
        subprocess.run(['pdftoppm','-png','-scale-to-x','1920','-scale-to-y','1080',str(work/'inputs/presentation.pdf'),str(work/'build/pdf-nuevo/slides-video/s')],check=True)
    print(work)
    return work

def inspect(args):
    plan=load_plan(args.plan)
    print(json.dumps({'duration_seconds':180,'shots':len(plan['planos']),'phrases':len(phrases(plan)),'voice':plan['voz']},indent=2))
    if args.workdir:
        work=args.workdir.resolve()
        required=[work/'build/fonts/Montserrat.ttf',work/'build/fonts/OpenSans.ttf',work/'inputs/audio/base.mp3']
        for shot in plan['planos']:
            required.append((work/'inputs/demos' if shot.get('video') else work/'build')/shot['src'])
        missing=sorted({str(p.relative_to(work)) for p in required if not p.exists()})
        print(json.dumps({'missing_inputs':missing},indent=2))
        return 1 if missing else 0
    return 0

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,default=HERE/'plan.es.json')
    commands=parser.add_subparsers(dest='command',required=True)
    setup=commands.add_parser('prepare');setup.add_argument('--workdir',type=Path,required=True);setup.add_argument('--pdf',type=Path)
    check=commands.add_parser('inspect');check.add_argument('--workdir',type=Path)
    for name in ['align','render','export','music']:
        sub=commands.add_parser(name);sub.add_argument('--workdir',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='prepare':prepare(args);return
    if args.command=='inspect':raise SystemExit(inspect(args))
    work=args.workdir.resolve()
    if args.command in ['render','export']:
        for executable in ['ffmpeg','ffprobe']:
            if not shutil.which(executable):raise SystemExit('Missing executable: '+executable)
    names={'align':'hexastra_align_refinado.py','render':'hexastra_render_refinado.py','export':'hexastra_export_refinado.py','music':'musica_v2.py'}
    env=dict(os.environ,HEXASTRA_VIDEO_LANGUAGE='es')
    subprocess.run([sys.executable,str(work/'scripts'/names[args.command])],cwd=work,env=env,check=True)

if __name__=='__main__':main()
