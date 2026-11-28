#!/usr/bin/env python3
"""Reel del sabato di Optometria Giovane — montaggio dinamico.

Uso:  python3 reel-dinamico.py storia.json uscita.mp4 [--anteprima t1 t2 ...]

Tagli a tempo di musica, zoom sulle clip, glitch, lampi, tremolio e testi animati.
I file (clip B-roll, logo-white.png, logo-black.png, ph-end.webp, musica.mp3) devono
stare nella stessa cartella di storia.json. Struttura di storia.json: vedi esempio-dinamico.json.

Tipi di scena:
  gancio   {pill, righe:[{t, evid}], clip:[...]}              righe a tempo, un taglio a ogni battito
  timbro   {testo, tono: red|green|sky}                        timbro su fondo nero, tremolio
  frase    {pill?, righe:[{t, stile: testo|evid|rosso|piccolo|grande}], clip:[...]}
  catena   {pill, passi:[...], barrata: true|false, clip:[...]} passi con frecce, ultimo barrato
  titolo   {grande, righe:[...], clip:[...]}                   titolo centrale (es. META-ANALISI)
  grafico  {titolo, barre:[{etichetta, valore, mostra, nota, tono}], conclusione?, fonte, clip:[...]}
  punti    {domanda, punti:[{t, sotto?}], clip:[...]}           domanda, poi un punto per taglio
  regola   {pill, grande, testo}                               fondo azzurro
  fine     {corso, titolo?, sotto?, cta:[max 2 frasi da max 30 caratteri]}  chiusura con foto
Ogni scena accetta "battiti" per forzare la durata (altrimenti calcolata dalla lunghezza dei testi).
"""
import subprocess, sys, math, random, os, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
args = sys.argv[1:]
prev = []
if '--anteprima' in args:
    i = args.index('--anteprima'); prev = [float(x) for x in args[i + 1:]]; args = args[:i]
STORY, OUT = args[0], args[1]
BASE = os.path.dirname(os.path.abspath(STORY))
S = json.load(open(STORY))
BPM = S.get('bpm', 83.354); P = 60 / BPM
FF = 'ffmpeg'
try:
    subprocess.run([FF, '-version'], capture_output=True, check=True)
except Exception:
    import imageio_ffmpeg; FF = imageio_ffmpeg.get_ffmpeg_exe()

SKY = (31, 162, 224); SKYD = (12, 127, 184); SKYL = (227, 244, 252); BLK = (11, 13, 18)
RED = (255, 90, 95); GRN = (47, 211, 138); WHITE = (255, 255, 255); GREY = (170, 180, 192)
TONI = {'red': RED, 'green': GRN, 'sky': SKY, 'grey': GREY}
def _f(*names):
    for n in names:
        if os.path.exists(n): return n
    return names[-1]
FX = _f('/usr/share/fonts/truetype/google-fonts/Poppins-ExtraBold.ttf', '/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf')
FB = _f('/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf', FX)
FI = _f('/usr/share/fonts/opentype/inter/Inter-SemiBold.otf', FB)
_fc = {}
def font(p, s):
    if (p, s) not in _fc: _fc[(p, s)] = ImageFont.truetype(p, s)
    return _fc[(p, s)]
ease = lambda x: 0 if x <= 0 else 1 if x >= 1 else 1 - (1 - x) ** 3
def back(x):
    x = max(0, min(1, x)); c = 1.9
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2
NONE = (0, 0, 0, 0)

_tc = {}
def text_img(txt, fp, size, color=WHITE, box=None, maxw=920, pad=(22, 6), align='left', lh=1.12, fit=False):
    k = (txt, fp, size, color, box, maxw, align, fit)
    if k in _tc: return _tc[k]
    if fit:
        while font(fp, size).getlength(txt) > maxw - 2 * pad[0] and size > 40: size -= 2
    f = font(fp, size)
    lines, cur = [], ''
    for w in txt.split(' '):
        t = (cur + ' ' + w).strip()
        if f.getlength(t) <= maxw - (2 * pad[0] if box else 0) or not cur: cur = t
        else: lines.append(cur); cur = w
    lines.append(cur)
    lhp = int(size * lh); desc = f.getmetrics()[1]
    tw = int(max(f.getlength(l) for l in lines)); th = lhp * len(lines) + desc // 2
    px, py = pad if box else (0, 0)
    im = Image.new('RGBA', (tw + 2 * px, th + 2 * py), NONE); d = ImageDraw.Draw(im)
    if box and box != NONE:
        if len(lines) == 1: d.rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=18, fill=box)
        else:
            for i, l in enumerate(lines):
                lw = f.getlength(l); x0 = 0 if align == 'left' else (im.width - lw - 2 * px) / 2
                d.rounded_rectangle([x0, i * lhp, x0 + lw + 2 * px, (i + 1) * lhp + 2 * py], radius=16, fill=box)
    for i, l in enumerate(lines):
        lw = f.getlength(l); x = px if align == 'left' else (im.width - lw) / 2
        d.text((x, py + i * lhp - int(size * 0.08)), l, font=f, fill=color)
    _tc[k] = im
    return im

class E:
    def __init__(s, img, x, y, t0, t1, anim='pop', anchor='l'):
        s.img, s.x, s.y, s.t0, s.t1, s.anim, s.anchor = img, x, y, t0, t1, anim, anchor
    def draw(s, fr, t):
        if t < s.t0 or t >= s.t1: return
        lt, out = t - s.t0, s.t1 - t
        a = ease(lt / 0.18) * min(1, out / 0.08); sc, dx, dy = 1, 0, 0
        if s.anim == 'pop': sc = 0.55 + 0.45 * back(lt / 0.32)
        elif s.anim == 'slam': sc = 2.4 - 1.4 * back(lt / 0.28)
        elif s.anim == 'up': dy = int(70 * (1 - ease(lt / 0.35)))
        elif s.anim == 'left': dx = int(-160 * (1 - ease(lt / 0.3)))
        im = s.img
        if sc != 1: im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BILINEAR)
        if a < 1:
            im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v: int(v * a)))
        x = s.x - im.width // 2 if s.anchor == 'c' else s.x - (im.width - s.img.width) // 2
        y = s.y - (im.height - s.img.height) // 2
        fr.alpha_composite(im, (int(x + dx), int(y + dy)))

def stack(items, y0, gap=18, x=80):
    out, y = [], y0
    for it in items:
        img, t0, t1, an = it[:4]; anc = it[4] if len(it) > 4 else 'l'
        out.append(E(img, W // 2 if anc == 'c' else x, y, t0, t1, an, anc)); y += img.height + gap
    return out

ARROW = Image.new('RGBA', (90, 80), NONE)
_d = ImageDraw.Draw(ARROW); _d.rectangle([35, 0, 55, 40], fill=SKY); _d.polygon([(10, 38), (80, 38), (45, 78)], fill=SKY)

# ---------- B-roll ----------
class Clip:
    def __init__(s, name, start):
        s.p, s.start, s.proc, s.idx, s.last = os.path.join(BASE, name), start, None, -1, None
    def frame(s, i):
        if s.proc is None:
            s.proc = subprocess.Popen([FF, '-loglevel', 'quiet', '-stream_loop', '-1', '-ss', f'{s.start:.2f}', '-i', s.p,
                '-vf', f'scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},eq=saturation=0.85',
                '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
        while s.idx < i:
            buf = s.proc.stdout.read(W * H * 3)
            if len(buf) == W * H * 3: s.last = Image.frombytes('RGB', (W, H), buf)
            s.idx += 1
        return s.last if s.last else Image.new('RGB', (W, H), BLK)
    def close(s):
        if s.proc: s.proc.kill(); s.proc = None
        s.idx = -1; s.last = None

class Seg:
    def __init__(s, t0, t1, clip, start, dark):
        s.t0, s.t1, s.clip, s.dark = t0, t1, Clip(clip, start), dark

grad = Image.new('L', (1, H))
for yy in range(H): grad.putpixel((0, yy), int(255 * min(1, 0.6 + 0.3 * abs(yy / H - 0.45) * 2)))
grad = grad.resize((W, H))
DARK = Image.new('RGB', (W, H), (8, 14, 24))

def bg_frame(seg, t):
    lt = t - seg.t0
    im = seg.clip.frame(int(round(lt * FPS)))
    z = (1 + 0.14 * (1 - ease(lt / 0.35))) * (1 + 0.035 * lt)
    cw, ch = W / z, H / z
    im = im.crop((int((W - cw) / 2), int((H - ch) / 2), int((W + cw) / 2), int((H + ch) / 2))).resize((W, H), Image.BILINEAR)
    return Image.composite(DARK, im, grad.point(lambda v: int(v * seg.dark))).convert('RGBA')

# ---------- costruzione della timeline ----------
segs, els, solids, specials = [], [], [], []
fx = {'flash': [], 'glitch': [], 'shake': [], 'redflash': []}
rnd = random.Random(7)
clipstart = {}
def add_clips(b0, b1, clips, every=1.0, dark=0.75):
    """riempie [b0,b1] di tagli ogni `every` battiti ciclando sulle clip."""
    if not clips: return
    b, k = b0, 0
    while b < b1 - 1e-6:
        e = min(b1, b + every)
        if b1 - e < 0.5: e = b1
        c = clips[k % len(clips)]
        st = clipstart.get(c, rnd.uniform(0, 3)); clipstart[c] = st + (e - b) * P
        segs.append(Seg(b * P, e * P, c, st, dark)); fx['flash'].append(b * P) if k else None
        b, k = e, k + 1

def chars(*xs): return sum(len(x) for x in xs)
def nb(sc, base):  # battiti di una scena
    if sc.get('battiti'): return float(sc['battiti'])
    return max(2.0, math.ceil((base / 26 + 0.5) / P * 2) / 2)
def pill_img(txt, fg=BLK, bg=SKY): return text_img(txt.upper(), FX, 38, fg, box=bg, pad=(28, 14), maxw=920, fit=True)
STY = {'testo': (FX, 84, WHITE, None), 'evid': (FX, 96, WHITE, SKY), 'rosso': (FX, 140, WHITE, RED),
       'piccolo': (FX, 58, SKYL, None), 'grande': (FX, 112, WHITE, None)}

b = 0.0
DARKS = S.get('scuro', {})
for sc in S['scene']:
    tipo = sc['tipo']; clips = sc.get('clip', []); dk = sc.get('scuro', 0.75)
    if tipo == 'gancio':
        righe = sc['righe']; n = sc.get('battiti') or max(5, len(righe) + 1.5)
        b0, b1 = b, b + n
        add_clips(b0, b1, clips, 1.0, sc.get('scuro', 0.65))
        els.append(E(pill_img(sc.get('pill', S.get('formato', '')), WHITE, BLK), 80, 330, b0 * P + 0.02, b1 * P, 'slam'))
        items = [(text_img(r['t'], FX, 104, WHITE, box=SKY if r.get('evid') else NONE, pad=(22, 4), maxw=960, fit=True),
                  (b0 + 1 + 0.5 * i) * P, b1 * P, 'pop') for i, r in enumerate(righe)]
        els += stack(items, 470, 14, x=58)
        fx['glitch'].append(((b1 - 0.25) * P, (b1 + 0.1) * P))
    elif tipo == 'timbro':
        n = sc.get('battiti', 3); b0, b1 = b, b + n
        solids.append((b0 * P, b1 * P, BLK)); col = TONI.get(sc.get('tono', 'red'), RED)
        f = font(FX, 200); tw = int(f.getlength(sc['testo']))
        st = Image.new('RGBA', (tw + 140, 300), NONE); d = ImageDraw.Draw(st)
        d.rounded_rectangle([8, 8, tw + 132, 292], 40, outline=col, width=16); d.text((70, 30), sc['testo'], font=f, fill=col)
        st = st.rotate(-7, expand=True, resample=Image.BICUBIC)
        if st.width > 1000: st = st.resize((1000, int(st.height * 1000 / st.width)))
        els.append(E(st, W // 2, 690, (b0 + 0.3) * P, b1 * P, 'slam', 'c'))
        fx['shake'].append(((b0 + 0.55) * P, 0.45, 26)); fx['redflash' if col == RED else 'flash'].append((b0 + 0.55) * P)
    elif tipo == 'frase':
        righe = sc['righe']; n = nb(sc, chars(*[r['t'] for r in righe])); b0, b1 = b, b + n
        add_clips(b0, b1, clips, 2.5, dk)
        items, y0 = [], 520
        if sc.get('pill'): els.append(E(pill_img(sc['pill']), 80, 330, b0 * P, b1 * P, 'left'))
        for i, r in enumerate(righe):
            fp, sz, col, bx = STY[r.get('stile', 'testo')]
            anim = 'slam' if r.get('stile') in ('rosso', 'grande') else 'up'
            items.append((text_img(r['t'], fp, sz, col, box=bx or NONE, pad=(26, 6), maxw=960), (b0 + 0.2 + 0.6 * i) * P, b1 * P, anim))
            if r.get('stile') == 'rosso': fx['shake'].append(((b0 + 0.3 + 0.6 * i) * P, 0.3, 16))
        els += stack(items, y0, 24, x=58)
    elif tipo == 'catena':
        passi = sc['passi']; n = sc.get('battiti') or 1 + 1.5 * len(passi) + (2 if sc.get('barrata', True) else 0.5)
        b0, b1 = b, b + n
        per = (n - (2 if sc.get('barrata', True) else 0.5)) / len(passi)
        for i in range(len(passi)):
            add_clips(b0 + i * per, b0 + (i + 1) * per if i < len(passi) - 1 else b1, [clips[i % len(clips)]] if clips else [], 9, dk)
        els.append(E(pill_img(sc.get('pill', '')), 80, 330, b0 * P, b1 * P, 'left'))
        items = []
        for i, p_ in enumerate(passi):
            last = i == len(passi) - 1
            if i: items.append((ARROW, (b0 + 0.5 + i * per - 0.4) * P, b1 * P, 'pop'))
            img = text_img(p_, FX, 110 if last else 84, WHITE, box=SKY if last else None, pad=(24, 6), maxw=940)
            items.append((img, (b0 + 0.5 + i * per) * P, b1 * P, 'slam' if last else 'left'))
        st = stack(items, 460, 6)
        els += st
        if sc.get('barrata', True):
            specials.append(('strike', (b1 - 2) * P, b1 * P, st[-1])); fx['shake'].append(((b1 - 2) * P, 0.35, 18))
    elif tipo == 'titolo':
        righe = sc.get('righe', []); n = nb(sc, chars(sc['grande'], *righe) * 0.8); b0, b1 = b, b + n
        add_clips(b0, b1, clips, 9, sc.get('scuro', 0.85))
        fx['glitch'].append(((b0 - 0.2) * P, (b0 + 0.15) * P))
        items = [(text_img(sc['grande'], FX, 130, SKY, maxw=1000, fit=True), (b0 + 0.1) * P, b1 * P, 'slam', 'c')]
        items += [(text_img(r, FX if i == 0 else FB, 72 if i == 0 else 52, WHITE, align='center', maxw=1000), (b0 + 0.6 + 0.5 * i) * P, b1 * P, 'up', 'c') for i, r in enumerate(righe)]
        els += stack(items, 640, 20)
    elif tipo == 'grafico':
        barre = sc['barre']; n = sc.get('battiti') or 1 + 2.2 * len(barre) + 1.8; b0, b1 = b, b + n
        times = [b0 + 0.5 + 2.2 * i for i in range(len(barre))]
        for i in range(len(barre)):
            add_clips(times[i] if i else b0, times[i + 1] if i + 1 < len(barre) else b1, [clips[i % len(clips)]] if clips else [], 9, 0.8)
        els.append(E(text_img(sc['titolo'], FX, 64, maxw=920), 80, 340, b0 * P, b1 * P, 'up'))
        if sc.get('conclusione'):
            els.append(E(text_img(sc['conclusione'], FX, 60, TONI.get(barre[-1].get('tono', 'red'), RED), maxw=920), 80, 1250, (times[-1] + 1.1) * P, b1 * P, 'left'))
        els.append(E(text_img('Fonte: ' + sc['fonte'], FI, 32, GREY, maxw=920), 80, 1440, (b0 + 0.3) * P, b1 * P, 'up'))
        mx = max(x['valore'] for x in barre)
        specials.append(('chart', b0 * P, b1 * P, [(x, times[i] * P, mx) for i, x in enumerate(barre)]))
        fx['shake'].append(((times[-1] + 0.1) * P, 0.4, 22))
        if barre[-1].get('tono') == 'red': fx['redflash'].append((times[-1] + 0.1) * P)
    elif tipo == 'punti':
        punti = sc['punti']; dq = max(2, math.ceil((len(sc['domanda']) / 28 + 0.2) / P))
        durs = [max(3, math.ceil((chars(p_['t'], p_.get('sotto', '')) / 26 + 0.4) / P)) for p_ in punti]
        b0 = b; b1 = b + dq + sum(durs)
        fx['glitch'].append(((b0 - 0.2) * P, (b0 + 0.15) * P))
        add_clips(b0, b0 + dq, clips[:1], 9, 0.9)
        dom = sc['domanda'].split(' '); cut = max(1, len(dom) - 2)
        els += stack([(text_img(' '.join(dom[:cut]), FX, 92, maxw=960), (b0 + 0.15) * P, (b0 + dq) * P, 'up'),
                      (text_img(' '.join(dom[cut:]), FX, 92, WHITE, box=SKY, pad=(22, 4)), (b0 + 0.6) * P, (b0 + dq) * P, 'pop')], 620, 14)
        bb = b0 + dq
        for i, (p_, d_) in enumerate(zip(punti, durs)):
            add_clips(bb, bb + d_, [clips[(i + 1) % len(clips)]] if clips else [], 9, 0.88)
            fx['flash'].append(bb * P)
            it = [(text_img(str(i + 1), FX, 200, SKY), bb * P, (bb + d_) * P, 'slam'),
                  (text_img(p_['t'], FX, 82, maxw=940), (bb + 0.4) * P, (bb + d_) * P, 'up')]
            if p_.get('sotto'): it.append((text_img(p_['sotto'], FX, 58, SKYL, maxw=940), (bb + 1.4) * P, (bb + d_) * P, 'up'))
            els += stack(it, 470, 8); bb += d_
        n = b1 - b0
    elif tipo == 'regola':
        n = nb(sc, chars(sc['grande'], sc.get('testo', '')) * 0.8); b0, b1 = b, b + n
        solids.append((b0 * P, b1 * P, SKY)); fx['flash'].append(b0 * P)
        els.append(E(pill_img(sc.get('pill', 'DA RICORDARE'), SKYD, WHITE), 80, 380, b0 * P, b1 * P, 'left'))
        els += stack([(text_img(sc['grande'], FX, 112, BLK, maxw=940), (b0 + 0.3) * P, b1 * P, 'slam'),
                      (text_img(sc.get('testo', ''), FX, 66, WHITE, maxw=940), (b0 + 1.6) * P, b1 * P, 'up')], 520, 40)
    elif tipo == 'fine':
        n = sc.get('battiti', 8); b0, b1 = b, b + n
        specials.append(('end', b0 * P, b1 * P, sc))
    b += n
TOTAL = b * P

# ---------- immagini fisse ----------
def load(name, h):
    im = Image.open(os.path.join(BASE, name)).convert('RGBA'); return im.resize((int(im.width * h / im.height), h))
logo_w = load('logo-white.png', 60); logo_b = load('logo-black.png', 84); ph = load('ph-end.webp', 700)

def draw_strike(fr, t, t0, e):
    p = ease((t - t0) / 0.25); d = ImageDraw.Draw(fr)
    y = e.y + e.img.height // 2; x0 = e.x - 10; x1 = min(W - 20, e.x + e.img.width + 10)
    d.line([x0, y, x0 + (x1 - x0) * p, y], fill=RED, width=16)
    if t - t0 > 0.2 and e.x + e.img.width + 120 < W: d.text((e.x + e.img.width + 20, e.y - 30), 'X', font=font(FX, 150), fill=RED)

def draw_chart(fr, t, bars):
    ov = Image.new('RGBA', (W, H), NONE); d = ImageDraw.Draw(ov); y = 560
    for x, tb, mx in bars:
        lt = t - tb
        if lt < 0: break
        col = TONI.get(x.get('tono', 'sky'), SKY)
        d.text((80, y), x['etichetta'], font=font(FB, 44), fill=WHITE)
        s = x['mostra']
        try:  # conteggio animato se "mostra" contiene il valore
            num = float(str(x['valore'])); txt = s.replace(f"{num:.2f}".replace('.', ','), f"{num * ease(lt / 0.7):.2f}".replace('.', ','))
        except Exception: txt = s
        f = font(FX, 64); d.text((1000 - f.getlength(txt), y - 14), txt, font=f, fill=col)
        d.rounded_rectangle([80, y + 70, 1000, y + 130], 18, fill=(255, 255, 255, 40))
        w = 920 * (x['valore'] / mx) * ease((lt - 0.1) / 0.7)
        if w > 4: d.rounded_rectangle([80, y + 70, 80 + w, y + 130], 18, fill=col)
        if x.get('nota'): d.text((80, y + 140), x['nota'], font=font(FI, 32), fill=GREY)
        y += 215
    fr.alpha_composite(ov)

def draw_end(fr, t, t0, sc):
    lt = t - t0; d = ImageDraw.Draw(fr)
    d.rectangle([0, 0, W, H], fill=SKYL)
    r = 560 + int(30 * math.sin(lt * 2)); p = ease(lt / 0.6)
    d.ellipse([W // 2 - r, 1680 - r + int(300 * (1 - p)), W // 2 + r, 1680 + r + int(300 * (1 - p))], fill=SKY)
    fr.alpha_composite(logo_b, ((W - logo_b.width) // 2, 160))
    rows = [(text_img(sc.get('titolo', 'Lo studio completo'), FX, 84, BLK, align='center', maxw=1000, fit=True), 275),
            (text_img(sc.get('sotto', 'è spiegato nella descrizione'), FX, 52, SKYD, align='center', maxw=1000, fit=True), 385)]
    for i, (im, y) in enumerate(rows):
        pp = back((lt - 0.15 - 0.15 * i) / 0.4)
        if pp <= 0: continue
        im2 = im.resize((max(1, int(im.width * (0.6 + 0.4 * pp))), max(1, int(im.height * (0.6 + 0.4 * pp)))))
        fr.alpha_composite(im2, ((W - im2.width) // 2, y + (im.height - im2.height) // 2))
    if lt > 0.5:
        a = ARROW.resize((64, 56)); fr.alpha_composite(a, ((W - 64) // 2, 462 + int(12 * abs(math.sin(lt * 5)))))
    y = 550
    for i, c in enumerate(sc.get('cta', ['CONDIVIDILO con un collega', 'COMMENTA: tu cosa ne pensi?'])[:2]):
        pc = ease((lt - 0.7 - 0.25 * i) / 0.35)
        im = text_img(c, FX, 44, WHITE, box=BLK if i else SKY, pad=(34, 18), align='center', maxw=960, fit=True)
        if pc > 0: fr.alpha_composite(im, ((W - im.width) // 2 + int(-200 * (1 - pc)), y))
        y += im.height + 18
    pk = ease((lt - 1.3) / 0.4)
    if pk > 0 and sc.get('corso'):
        y += 14
        l1 = text_img('APPROFONDISCI NEL CORSO', FX, 28, SKYD, align='center')
        l2 = text_img(sc['corso'], FB, 42, BLK, align='center', maxw=1000, fit=True)
        fr.alpha_composite(l1, ((W - l1.width) // 2, y)); fr.alpha_composite(l2, ((W - l2.width) // 2, y + 44))
        h = text_img('@optometria_giovane', FX, 34, SKYD, align='center'); fr.alpha_composite(h, ((W - h.width) // 2, y + 110))
    pf = ease((lt - 0.2) / 0.7)
    fr.alpha_composite(ph, ((W - ph.width) // 2, H - ph.height + int(400 * (1 - pf))))

def glitch(fr, t):
    for g0, g1 in fx['glitch']:
        if g0 <= t < g1:
            a = np.array(fr.convert('RGB')); r_ = random.Random(int(t * 1000)); sh = r_.randint(25, 60)
            a[:, :, 0] = np.roll(a[:, :, 0], sh, 1); a[:, :, 2] = np.roll(a[:, :, 2], -sh, 1)
            for _ in range(7):
                y0 = r_.randint(0, H - 120); h = r_.randint(20, 120); a[y0:y0 + h] = np.roll(a[y0:y0 + h], r_.randint(-160, 160), 1)
            return Image.fromarray(a).convert('RGBA')
    return fr

def render(t):
    end = next((s for s in specials if s[0] == 'end' and s[1] <= t < s[2]), None)
    sol = next((s for s in solids if s[0] <= t < s[1]), None)
    if end:
        fr = Image.new('RGBA', (W, H), SKYL); draw_end(fr, t, end[1], end[3])
    elif sol:
        fr = Image.new('RGBA', (W, H), sol[2] + (255,))
        if sol[2] == SKY:
            ov = Image.new('RGBA', (W, H), NONE); d = ImageDraw.Draw(ov); lt = t - sol[0]
            for k in range(4):
                r = 200 + (260 * k + int(160 * lt)) % 1100
                d.ellipse([W - 150 - r, 1750 - r, W - 150 + r, 1750 + r], outline=(255, 255, 255, 45), width=5)
            fr.alpha_composite(ov)
    else:
        seg = next((s for s in segs if s.t0 <= t < s.t1), None)
        fr = bg_frame(seg, t) if seg else Image.new('RGBA', (W, H), BLK + (255,))
    for e in els: e.draw(fr, t)
    for kind, t0, t1, data in specials:
        if t0 <= t < t1:
            if kind == 'strike': draw_strike(fr, t, t0, data)
            elif kind == 'chart': draw_chart(fr, t, data)
    if not end:
        fr.alpha_composite(logo_w, (80, 150))
        ImageDraw.Draw(fr).rectangle([0, 0, int(W * t / TOTAL), 10], fill=WHITE if sol and sol[2] == SKY else SKY)
    for s0, du, amp in fx['shake']:
        if s0 <= t < s0 + du:
            k = 1 - (t - s0) / du; r_ = random.Random(int(t * 997))
            fr2 = Image.new('RGBA', (W, H), BLK + (255,))
            fr2.alpha_composite(fr, (int(r_.uniform(-1, 1) * amp * k), int(r_.uniform(-1, 1) * amp * k))); fr = fr2
    fr = glitch(fr, t)
    for f0 in fx['flash']:
        if f0 <= t < f0 + 0.12: fr.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 255, int(200 * (1 - (t - f0) / 0.12)))))
    for f0 in fx['redflash']:
        if f0 <= t < f0 + 0.25: fr.alpha_composite(Image.new('RGBA', (W, H), RED + (int(150 * (1 - (t - f0) / 0.25)),)))
    return fr.convert('RGB')

if prev:
    for tt in prev:
        for s in segs: s.clip.close()
        render(tt).save(os.path.join(BASE, f'anteprima_{tt:05.2f}.jpg'), quality=88)
    for s in segs: s.clip.close()
    print('anteprime ok, durata', round(TOTAL, 2)); sys.exit()

n = int(TOTAL * FPS); tmp = OUT + '.tmp.mp4'
enc = subprocess.Popen([FF, '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', tmp], stdin=subprocess.PIPE)
cur = None
for i in range(n):
    t = i / FPS
    seg = next((s for s in segs if s.t0 <= t < s.t1), None)
    if seg is not cur and cur is not None: cur.clip.close()
    if seg: cur = seg
    enc.stdin.write(render(t).tobytes())
enc.stdin.close(); enc.wait()
for s in segs: s.clip.close()
musica = os.path.join(BASE, S.get('musica', 'musica.mp3'))
if enc.returncode == 0 and os.path.exists(musica):
    off = S.get('musica_inizio', 14.884)
    r = subprocess.run([FF, '-loglevel', 'error', '-y', '-i', tmp, '-ss', str(off), '-i', musica, '-filter_complex',
        f'[1:a]atrim=0:{TOTAL:.2f},asetpts=PTS-STARTPTS,afade=t=in:d=0.3,afade=t=out:st={TOTAL - 2.2:.2f}:d=2.2,volume=0.95[a]',
        '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', OUT + '.a.mp4'])
    if r.returncode == 0: os.replace(OUT + '.a.mp4', OUT); os.remove(tmp)
    else: os.replace(tmp, OUT)
elif enc.returncode == 0: os.replace(tmp, OUT)
print('OK', OUT, round(TOTAL, 2), 's')
