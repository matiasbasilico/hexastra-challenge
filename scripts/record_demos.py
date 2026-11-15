#!/usr/bin/env python3
"""Record the real guided/advanced UI and export presentation-ready GIFs/MP4s.

Requires Playwright Chromium and FFmpeg. No mocked responses or fabricated UI.
The explicit URL language makes recordings independent of browser settings.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from urllib.parse import urlencode, urlparse
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]

def run(command):
    subprocess.run(command,check=True)

def export_video(source,start,duration,output):
    run(['ffmpeg','-v','error','-y','-ss',str(max(0,start)), '-i',str(source),'-t',str(duration),'-an','-vf','fps=24','-c:v','libx264','-preset','medium','-crf','22','-pix_fmt','yuv420p','-movflags','+faststart',str(output.with_suffix('.mp4'))])
    # Preserve the whole interface and map attribution; tune only resolution/palette.
    for width,fps,colors in [(1280,10,128),(1120,8,112),(960,8,96)]:
        vf=f'fps={fps},scale={width}:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors={colors}:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle'
        run(['ffmpeg','-v','error','-y','-i',str(output.with_suffix('.mp4')),'-filter_complex',vf,'-loop','0',str(output.with_suffix('.gif'))])
        if output.with_suffix('.gif').stat().st_size < 10_000_000:break
    else:raise RuntimeError('GIF exceeds the submission image size limit.')

def record(browser,args,mode,directory):
    context=browser.new_context(viewport={'width':args.width,'height':args.height},locale='en-US' if args.language=='en' else 'es-AR',reduced_motion='reduce',record_video_dir=str(directory),record_video_size={'width':args.width,'height':args.height})
    context.add_init_script("localStorage.setItem('hexastra.onboarding.v1','seen')")
    forbidden=[]
    if urlparse(args.url).hostname not in ['localhost','127.0.0.1']:
        def guard(route):
            host=urlparse(route.request.url).hostname or ''
            if host in ['localhost','127.0.0.1'] or host.endswith('.trycloudflare.com'):
                forbidden.append(host);route.abort()
            else:route.continue_()
        context.route('**/*',guard)
    before=time.monotonic();page=context.new_page();errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    if mode=='guided':path='/?'+urlencode({'lang':args.language})
    else:path='/classic.html?'+urlencode({'mode':'advanced','target':'arsia-mons','preset':'terreno','region':'country:AR','site':'laguna-antofagasta','mask':'true','lang':args.language})
    page.goto(args.url.rstrip('/')+path,wait_until='domcontentloaded',timeout=90000)
    if mode=='guided':page.wait_for_function("document.querySelector('#site-count').textContent==='60' && !document.querySelector('#apply-mission').disabled",timeout=90000)
    else:page.wait_for_selector('#panel .site-title',timeout=90000)
    if mode=='advanced':
        page.locator('#map-earth [data-view="flat"]').click()
    page.evaluate('document.fonts.ready');page.wait_for_timeout(1800)
    page.evaluate('''()=>{const cursor=document.createElement('div');cursor.id='demo-cursor';cursor.setAttribute('aria-hidden','true');cursor.style.cssText='position:fixed;top:-30px;left:-30px;width:16px;height:16px;border:2px solid #65d0ea;background:#07091588;border-radius:50%;z-index:2147483647;pointer-events:none;transform:translate(-50%,-50%)';document.body.append(cursor);document.addEventListener('pointermove',e=>{cursor.style.left=e.clientX+'px';cursor.style.top=e.clientY+'px'});}''')
    start=time.monotonic()-before
    def pause(seconds=1):page.wait_for_timeout(seconds*1000)
    def click(selector,hold=1):
        locator=page.locator(selector).first
        box=locator.bounding_box()
        if not box:raise RuntimeError('Control is not visible: '+selector)
        page.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2,steps=12);pause(.15);locator.click();pause(hold)
    pause(1)
    if mode=='guided':
        click('#open-mission',1.6)
        click('.planet-card-moon',.9);click('.planet-card-mars',1.2)
        click('#apply-mission',1.2)
        page.locator('#world-target').select_option('arsia-mons');pause(3.8)
        click('#apply-mission',1.5)
        click('label.preset-card:has(input[value="terreno"])',1.3)
        click('#mission-filters-tab',1.2)
        page.locator('#world-region').select_option('country:AR');pause(1.8)
        click('#mission-test-tab',.8)
        click('#apply-mission',.4)
        page.wait_for_selector('#compare-content .compare-score',timeout=60000);pause(4)
        click('.tasi-help-trigger',3.5);page.keyboard.press('Escape');pause(1)
    else:
        pause(2)
        click('#weights-menu > summary',2)
        slider=page.locator('#w-T');slider.focus();slider.press('End')
        for _ in range(8):slider.press('ArrowLeft');pause(.1)
        pause(2);click('#weights-menu [data-close-menu]',.5)
        click('#options-menu > summary',2);click('#options-menu [data-close-menu]',.5)
        click('#btn-buscar',.4)
        page.wait_for_function("!document.querySelector('#btn-buscar').disabled",timeout=60000);pause(2)
        click('.layers-menu > summary',3)
        click('.earth-layers-panel [data-close-menu]',.7)
        heading=page.locator('#panel h3').filter(has_text='Data side by side' if args.language=='en' else 'Datos lado a lado').first
        heading.scroll_into_view_if_needed();pause(3)
    duration=time.monotonic()-before-start
    if errors:raise RuntimeError('Browser errors: '+repr(errors))
    if forbidden:raise RuntimeError('The public demo tried to use local/tunnel services: '+repr(forbidden))
    output=args.output/(mode+'-'+args.language)
    page.screenshot(path=str(output.with_suffix('.png')))
    video=page.video;context.close();source=video.path()
    export_video(source,start,duration,output)
    print(mode,args.language,'seconds',round(duration,2),'GIF bytes',output.with_suffix('.gif').stat().st_size,flush=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='https://hexastra.pages.dev')
    parser.add_argument('--language',choices=['en','es'],default='en')
    parser.add_argument('--output',type=Path,default=ROOT/'assets/demo')
    parser.add_argument('--width',type=int,default=1280)
    parser.add_argument('--height',type=int,default=800)
    parser.add_argument('--mode',choices=['both','guided','advanced'],default='both')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    if not shutil.which('ffmpeg'):raise SystemExit('Install FFmpeg before recording.')
    with tempfile.TemporaryDirectory(prefix='hexastra-demo-') as temp:
        with sync_playwright() as p:
            browser=p.chromium.launch(args=['--enable-unsafe-swiftshader'])
            for mode in ['guided','advanced'] if args.mode=='both' else [args.mode]:record(browser,args,mode,Path(temp))
            browser.close()

if __name__=='__main__':main()
