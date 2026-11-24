#!/usr/bin/env python3
"""Rendering dei reel di Optometria Giovane.

Uso: python3 compose.py grafica.html data.json uscita.mp4

- grafica.html e i file che usa (foto, logo) devono stare nella stessa cartella.
- Se data.json contiene "broll": ["broll-05.mp4", ...] (file nella stessa cartella),
  le clip vengono messe sotto le schede (una clip per scheda, a rotazione) e la
  grafica viene sovrapposta con trasparenza. Senza "broll" il video è solo grafica.
"""
import json, os, sys, shutil, subprocess
from playwright.sync_api import sync_playwright
import imageio_ffmpeg

FPS = 25
html, data_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
base = os.path.dirname(os.path.abspath(html))
data = json.load(open(data_path))
broll = [os.path.join(base, b) for b in data.get("broll") or [] if os.path.exists(os.path.join(base, b))]
if data.get("broll") and not broll:
    data["broll"] = []  # clip mancanti: video solo grafica
use_broll = bool(broll)
ff = imageio_ffmpeg.get_ffmpeg_exe()
tmp = os.path.join(base, "_frames")
shutil.rmtree(tmp, ignore_errors=True)
os.makedirs(tmp)

exe = "/usr/bin/google-chrome" if os.path.exists("/usr/bin/google-chrome") else None
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
    pg = b.new_page(viewport={"width": 1080, "height": 1920})
    pg.add_init_script("window.DATA=" + json.dumps(data))
    pg.goto("file://" + os.path.abspath(html))
    pg.wait_for_timeout(1000)
    total = pg.evaluate("TOTAL")
    scenes = pg.evaluate("window.SCENES||null")
    n = int(total * FPS)
    for i in range(n):
        pg.evaluate(f"render({i / FPS})")
        if use_broll:
            pg.screenshot(path=f"{tmp}/f{i:05d}.png", omit_background=True)
        else:
            pg.screenshot(path=f"{tmp}/f{i:05d}.jpg", type="jpeg", quality=92)
    b.close()

enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
if not use_broll:
    subprocess.run([ff, "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", f"{tmp}/f%05d.jpg", *enc, out], check=True)
else:
    if not scenes:
        scenes = [[0, total, True]]
    # una clip per ogni scena-scheda, a rotazione; le scene opache riusano l'ultima clip (sono coperte)
    segs, k, last = [], 0, broll[0]
    for s0, d, card in scenes:
        if card:
            last = broll[k % len(broll)]
            k += 1
        segs.append((last, d))
    cmd = [ff, "-loglevel", "error", "-y"]
    for clip, d in segs:
        cmd += ["-stream_loop", "-1", "-t", f"{d:.3f}", "-i", clip]
    cmd += ["-framerate", str(FPS), "-i", f"{tmp}/f%05d.png"]
    parts = "".join(f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps={FPS},setsar=1,setpts=PTS-STARTPTS[v{i}];" for i in range(len(segs)))
    conc = "".join(f"[v{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=1:a=0[bg];"
    ov = f"[bg][{len(segs)}:v]overlay=0:0:shortest=1[o]"
    cmd += ["-filter_complex", parts + conc + ov, "-map", "[o]", *enc, out]
    subprocess.run(cmd, check=True)
shutil.rmtree(tmp, ignore_errors=True)
print(f"OK {out} {total:.1f}s broll={len(broll)}")
