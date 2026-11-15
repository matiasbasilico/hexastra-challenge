"""Video v2 (180 s): compositor cuadro a cuadro + voz + música original.

- Planos de guion_v2.json: capturas reales de la app (HD), láminas corregidas 2x y las dos demos
  completas (cada una una sola vez, sin bucle). Cámara con easing sub-píxel, fundidos cortos.
- Voz: edge-tts (voz y pronunciación en el guion). Pista reemplazable: build/v2/voz.wav.
  Para cambiar de voz: `--voz es-AR-TomasNeural` (regenera frases) o `--voz-wav archivo.wav`.
- Música: build/v2/musica.wav (scripts/musica_v2.py, sintetizada acá, original), atenuada bajo la voz.
Uso: build/.venv/bin/python scripts/montar_v2.py [--guion guion_quieta.json] [--salida NOMBRE.mp4]
     [--voz NOMBRE] [--voz-wav WAV] [--solo-audio]
"""
import asyncio
import json
import subprocess
import sys
from pathlib import Path

import cv2
import edge_tts
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
B = ROOT / "build"
V2 = B / "v2"
DEMOS = ROOT / "inputs" / "demos"
GUION = sys.argv[sys.argv.index("--guion") + 1] if "--guion" in sys.argv else "guion_v2.json"
G = json.loads((ROOT / "scripts" / GUION).read_text())
W, H, FPS = 1920, 1080, 30
TOTAL = G["duracion_total_s"]
XF = G["fundido_s"]
OUT = ROOT / (sys.argv[sys.argv.index("--salida") + 1] if "--salida" in sys.argv else "hexastra-pitch-3min-v2.mp4")
TAG = OUT.stem
FONTS = B / "fonts"
COLORES = {"cian": (101, 208, 234), "celeste": (114, 156, 216), "marte": (216, 126, 78),
           "violeta": (160, 115, 230), "sol": (212, 150, 78)}
NOCHE = (7, 9, 21)
TEXTO = (246, 247, 254)


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def dur(path) -> float:
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True)
    return float(r.stdout)


# ---------------------------------------------------------------- tiempos
def planos_con_inicio():
    t, out = 0.0, []
    for p in G["planos"]:
        out.append({**p, "inicio": t})
        t += p["dur"]
    assert abs(t - TOTAL) < 1e-6, f"los planos suman {t}, no {TOTAL}"
    return out


def frases_absolutas(planos):
    fr = []
    for p in planos:
        for f in p.get("frases", []):
            fr.append({**f, "t": round(p["inicio"] + f["at"], 3), "plano": p["id"]})
    for i, f in enumerate(fr):
        f["id"] = f"{i + 1:02d}"
    return fr


# ---------------------------------------------------------------- voz
def texto_tts(texto: str) -> str:
    for k, v in G["pronunciacion"].items():
        texto = texto.replace(k, v)
    return texto


def generar_voz(frases, voz):
    d = V2 / f"voz-{voz}"
    d.mkdir(parents=True, exist_ok=True)
    for f in frases:
        tts = texto_tts(f["texto"])
        mp3, txt, wav = d / f"{f['id']}.mp3", d / f"{f['id']}.txt", d / f"{f['id']}.wav"
        if not mp3.exists() or not txt.exists() or txt.read_text() != tts + G["velocidad"]:
            asyncio.run(edge_tts.Communicate(tts, voz, rate=G["velocidad"]).save(str(mp3)))
            txt.write_text(tts + G["velocidad"])
        trim = ("silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
                "silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
                "afade=t=in:d=0.02,areverse,afade=t=in:d=0.05,areverse")
        run(["ffmpeg", "-v", "error", "-y", "-i", str(mp3), "-af", trim, "-ar", "48000", "-ac", "1", str(wav)])
        f["wav"], f["dur"] = wav, dur(wav)
    return frases


def revisar_frases(frases):
    ok = True
    for i, f in enumerate(frases):
        fin = f["t"] + f["dur"]
        prox = frases[i + 1]["t"] if i + 1 < len(frases) else TOTAL - 0.5
        hueco = prox - fin
        marca = "SUPERPUESTA" if fin > prox - 0.15 else ("hueco largo" if hueco > 2.6 else "")
        print(f"{f['id']} {f['t']:6.1f}→{fin:6.1f} hueco {hueco:4.1f} {marca:12} {f['texto'][:60]}")
        ok &= fin <= prox - 0.15
    if not ok:
        sys.exit("Hay frases superpuestas: ajustar 'at' en guion_v2.json")


def pista_voz(frases) -> Path:
    wav = V2 / f"voz-{TAG}.wav"
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for f in frases:
        cmd += ["-i", str(f["wav"])]
    parts = [f"[{i}:a]adelay={int(f['t'] * 1000)}:all=1[a{i}]" for i, f in enumerate(frases)]
    parts.append("".join(f"[a{i}]" for i in range(len(frases))) +
                 f"amix=inputs={len(frases)}:normalize=0,apad,atrim=0:{TOTAL}[out]")
    run(cmd + ["-filter_complex", ";".join(parts), "-map", "[out]", "-ar", "48000", "-ac", "1", str(wav)])
    return wav


def mezcla(voz_wav: Path, musica_wav: Path) -> Path:
    out = V2 / f"mezcla-{TAG}.wav"
    fc = ("[0:a]highpass=f=70,acompressor=threshold=-20dB:ratio=3:attack=5:release=120,"
          "aformat=channel_layouts=stereo,asplit=2[v][key];"
          "[1:a]volume=0.55[m];"
          "[m][key]sidechaincompress=threshold=0.02:ratio=6:attack=40:release=600:makeup=1[md];"
          f"[v][md]amix=inputs=2:normalize=0,atrim=0:{TOTAL},"
          "loudnorm=I=-16:TP=-1.5:LRA=11[out]")
    run(["ffmpeg", "-v", "error", "-y", "-i", str(voz_wav), "-i", str(musica_wav),
         "-filter_complex", fc, "-map", "[out]", "-ar", "48000", "-ac", "2", str(out)])
    return out


# ---------------------------------------------------------------- imagen
def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def camara(cam, t):
    if t <= cam[0][0]:
        return cam[0][1:]
    for a, b in zip(cam, cam[1:]):
        if a[0] <= t <= b[0]:
            k = ease((t - a[0]) / (b[0] - a[0]))
            return [a[i] + (b[i] - a[i]) * k for i in (1, 2, 3)]
    return cam[-1][1:]


def matriz(cx, cy, w, src_w, src_h, ref):
    s = src_w / ref
    cx, cy, w = cx * s, cy * s, w * s
    w = min(w, src_w, src_h * 16 / 9)
    h = w * 9 / 16
    cx = min(max(cx, w / 2), src_w - w / 2)
    cy = min(max(cy, h / 2), src_h - h / 2)
    k = W / w
    return np.float32([[k, 0, -(cx - w / 2) * k], [0, k, -(cy - h / 2) * k]])


class Demo:
    """Lee la demo cuadro a cuadro a 30 fps (sólo hacia adelante); devuelve el último al terminar."""

    def __init__(self, path):
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"fps={FPS}",
                                   "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
        self.w, self.h, self.n, self.frame = 1280, 720, -1, None

    def at(self, t):
        want = int(t * FPS + 1e-6)
        while self.n < want:
            buf = self.p.stdout.read(self.w * self.h * 3)
            if len(buf) < self.w * self.h * 3:
                break
            self.frame = np.frombuffer(buf, np.uint8).reshape(self.h, self.w, 3)
            self.n += 1
        return self.frame


def fuente(nombre, size, peso):
    f = ImageFont.truetype(str(FONTS / nombre), size)
    f.set_variation_by_name(peso)
    return f


F_ETQ = fuente("Montserrat.ttf", 22, "SemiBold")
F_TXT = fuente("Montserrat.ttf", 38, "Bold")
F_TXT_CHICO = fuente("OpenSans.ttf", 27, "SemiBold")


def chip_img(chip):
    """Etiqueta superior (Montserrat 600, mayúsculas, color semántico) + texto; fondo noche translúcido."""
    color = COLORES[chip["color"]]
    largo = len(chip["texto"]) > 48
    ftxt = F_TXT_CHICO if largo else F_TXT
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    maxw = chip.get("ancho_max", 1180)
    palabras, lineas, cur = chip["texto"].split(" "), [], ""
    for p in palabras:
        prueba = (cur + " " + p).strip()
        if tmp.textlength(prueba, font=ftxt) > maxw and cur:
            lineas.append(cur)
            cur = p
        else:
            cur = prueba
    lineas.append(cur)
    etq = chip["etiqueta"]
    ancho_etq = sum(tmp.textlength(c, font=F_ETQ) + 3 for c in etq)
    w = int(max(ancho_etq, *(tmp.textlength(l, font=ftxt) for l in lineas))) + 64
    lh = 40 if largo else 48
    h = 30 + 28 + lh * len(lineas) + 22
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=14, fill=(*NOCHE, 214), outline=(42, 50, 80, 255), width=2)
    d.rounded_rectangle((0, 0, 7, h - 1), radius=4, fill=(*color, 255))
    x = 32
    for c in etq:  # espaciado de etiqueta 0,14 em
        d.text((x, 22), c, font=F_ETQ, fill=(*color, 255))
        x += tmp.textlength(c, font=F_ETQ) + 3
    y = 56
    for l in lineas:
        d.text((32, y), l, font=ftxt, fill=(*TEXTO, 255))
        y += lh
    a = np.array(im)
    return cv2.cvtColor(a, cv2.COLOR_RGBA2BGRA)


def pegar(frame, img, x, y, alpha):
    h, w = img.shape[:2]
    roi = frame[y:y + h, x:x + w].astype(np.float32)
    a = img[:, :, 3:4].astype(np.float32) / 255 * alpha
    frame[y:y + h, x:x + w] = (roi * (1 - a) + img[:, :, :3] * a).astype(np.uint8)


def dibujar_chips(frame, plano, t, cache):
    for i, c in enumerate(plano.get("chips", [])):
        if not (c["t0"] - 0.01 <= t <= c["t1"]):
            continue
        key = (plano["id"], i)
        if key not in cache:
            cache[key] = chip_img(c)
        img = cache[key]
        k = min(ease((t - c["t0"]) / 0.35), ease((c["t1"] - t) / 0.35))
        dy = int((1 - k) * 18)
        h, w = img.shape[:2]
        x = 96 if c["lado"] == "izq" else W - w - 96
        pegar(frame, img, x, H - h - 92 + dy, k)


def dibujar_enlace(frame, plano, t, M):
    e = plano.get("enlace")
    if not e or t < e["t0"]:
        return
    k = ease((t - e["t0"]) / (e["t1"] - e["t0"]))
    s = 1.0  # coordenadas en px de la captura (ref 3200 = ancho real)
    p0 = M @ np.array([e["de"][0] * s, e["de"][1] * s, 1])
    p1 = M @ np.array([e["a"][0] * s, e["a"][1] * s, 1])
    pk = p0 + (p1 - p0) * k
    capa = frame.copy()
    for grosor, col in ((14, (234, 208, 101)), (4, (255, 240, 200))):
        cv2.line(capa, tuple(int(v * 4) for v in p0), tuple(int(v * 4) for v in pk), col, grosor, cv2.LINE_AA, shift=2)
    pulso = 0.5 + 0.5 * np.sin(t * 4)
    for p in (p0, pk) if k < 1 else (p0, p1):
        cv2.circle(capa, (int(p[0] * 4), int(p[1] * 4)), int((26 + 8 * pulso) * 4), (234, 208, 101), 3, cv2.LINE_AA, shift=2)
    cv2.addWeighted(capa, 0.85, frame, 0.15, 0, dst=frame)


def render_plano(plano, t, fuentes, cache):
    if plano.get("video"):
        src = fuentes[plano["id"]].at(min(t, plano["dur"] - 1 / FPS))
    else:
        src = fuentes[plano["id"]]
    sh, sw = src.shape[:2]
    M = matriz(*camara(plano["cam"], t), sw, sh, plano["ref"])
    frame = cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    dibujar_enlace(frame, plano, t, M)
    dibujar_chips(frame, plano, t, cache)
    return frame


def video(planos) -> Path:
    fuentes = {}
    for p in planos:
        if p.get("video"):
            assert abs(dur(DEMOS / p["src"]) - p["dur"]) < 0.05, f"{p['src']} no dura {p['dur']}"
            fuentes[p["id"]] = Demo(DEMOS / p["src"])
        else:
            fuentes[p["id"]] = cv2.imread(str(B / p["src"]))
    out = V2 / f"video-{TAG}.mp4"
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                            "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)],
                           stdin=subprocess.PIPE)
    cache = {}
    for n in range(int(TOTAL * FPS)):
        T = n / FPS
        i = max(j for j, p in enumerate(planos) if p["inicio"] <= T + 1e-9)
        p = planos[i]
        frame = render_plano(p, T - p["inicio"], fuentes, cache)
        if i > 0 and T - p["inicio"] < XF:
            q = planos[i - 1]
            prev = render_plano(q, T - q["inicio"], fuentes, cache)
            a = ease((T - p["inicio"]) / XF)
            frame = cv2.addWeighted(frame, a, prev, 1 - a, 0)
        if T < 0.4:
            frame = (frame * ease(T / 0.4)).astype(np.uint8)
        if T > TOTAL - 0.8:
            frame = (frame * ease((TOTAL - T) / 0.8)).astype(np.uint8)
        enc.stdin.write(frame.tobytes())
        if n % 900 == 0:
            print(f"  video {T:5.0f}/{TOTAL} s", flush=True)
    enc.stdin.close()
    enc.wait()
    return out


def srt(frases):
    def ts(s):
        ms = int(round(s * 1000))
        return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"
    bloques = [f"{i}\n{ts(f['t'])} --> {ts(f['t'] + f['dur'])}\n{f['texto']}\n" for i, f in enumerate(frases, 1)]
    (ROOT / f"{TAG}.es.srt").write_text("\n".join(bloques), encoding="utf-8")


def main():
    planos = planos_con_inicio()
    frases = frases_absolutas(planos)
    voz_wav = arg("--voz-wav")
    if voz_wav:
        voz_wav = Path(voz_wav)
        frases = generar_voz(frases, G["voz"])  # sólo para tiempos del .srt
    else:
        frases = generar_voz(frases, arg("--voz", G["voz"]))
        revisar_frases(frases)
        voz_wav = pista_voz(frases)
    musica = V2 / "musica.wav"
    if not musica.exists():
        run([sys.executable, str(ROOT / "scripts" / "musica_v2.py")])
    audio = mezcla(voz_wav, musica)
    srt(frases)
    v = V2 / f"video-{TAG}.mp4"
    if "--solo-audio" not in sys.argv or not v.exists():
        v = video(planos)
    run(["ffmpeg", "-v", "error", "-y", "-i", str(v), "-i", str(audio), "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", str(TOTAL), "-movflags", "+faststart", str(OUT)])
    print("listo:", OUT, dur(OUT))


if __name__ == "__main__":
    main()
