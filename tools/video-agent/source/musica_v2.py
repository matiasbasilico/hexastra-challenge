"""Música ambiental original (sintetizada acá, sin samples ni obras de terceros) para la v2.

Colchón de acordes La m – Fa – Do – Sol (8 s cada uno) y un arpegio suave sólo en las demos.
Salida: build/v2/musica.wav (180 s, 48 kHz, estéreo). Se mezcla atenuada bajo la voz.
"""
import wave
from pathlib import Path

import numpy as np

SR, TOTAL = 48000, 180
OUT = Path(__file__).resolve().parent.parent / "build" / "v2" / "musica.wav"
ACORDES = [[57, 60, 64], [53, 57, 60], [48, 55, 64], [55, 59, 62]]  # Am F C G (MIDI)
ARPEGIO = [(45, 106)]  # tramos con arpegio (demos + capas), en segundos


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


def main():
    t = np.arange(SR * TOTAL) / SR
    pad = np.zeros_like(t)
    seg = 8.0
    for k in range(int(TOTAL / seg) + 1):
        notas = ACORDES[k % 4]
        t0 = k * seg
        env = np.clip(np.minimum((t - t0 + 1.5) / 2.5, (t0 + seg + 1.5 - t) / 2.5), 0, 1)
        env = np.sin(env * np.pi / 2) ** 2
        for m in notas + [notas[0] - 12]:
            f = hz(m)
            for det in (-0.12, 0.0, 0.12):
                pad += env * np.sin(2 * np.pi * (f + det) * t) * (0.5 if m < notas[0] else 1.0)
    pad *= 0.6 + 0.4 * np.sin(2 * np.pi * t / 23) ** 2
    arp = np.zeros_like(t)
    paso = 60 / 96 / 2  # corcheas a 96 bpm
    for a, b in ARPEGIO:
        n = int((b - a) / paso)
        for i in range(n):
            ti = a + i * paso
            acorde = ACORDES[int(ti / seg) % 4]
            m = (acorde + [acorde[0] + 12])[i % 4] + 12
            s0, s1 = int(ti * SR), min(int((ti + 1.2) * SR), len(t))
            tt = t[s0:s1] - ti
            arp[s0:s1] += np.sin(2 * np.pi * hz(m) * tt) * np.exp(-tt * 4.5) * (1 - np.exp(-tt * 300))
        fade = np.clip(np.minimum((t - a) / 3, (b - t) / 3), 0, 1)
        arp *= np.where((t >= a - 1) & (t <= b + 1), fade, 1)
    mezcla = pad / np.abs(pad).max() * 0.22 + arp / max(np.abs(arp).max(), 1e-9) * 0.10
    mezcla *= np.clip(np.minimum(t / 2.0, (TOTAL - t) / 3.0), 0, 1)
    izq = mezcla
    der = np.roll(mezcla, int(0.012 * SR))
    est = np.stack([izq, der], 1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUT), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(est, -1, 1) * 32767).astype(np.int16).tobytes())
    print("listo:", OUT)


if __name__ == "__main__":
    main()
