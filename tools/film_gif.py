# Films labelled scenes in the no-game Playroom and joins them into one looping GIF for the README, in the style of the
# original's docs/moves.gif (dark "void" look, solid body, soft light, a label in the corner). NOT part of the original.
# usage: python tools/film_gif.py <set> <out.gif> [--only LABEL,LABEL] [--sheet sheet.png] [--size 320]
# Needs ffmpeg on the path. Frames go to the system temp folder.
import os, shutil, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
a = sys.argv[1:]
def opt(k, d=None):
    if k in a:
        i = a.index(k); v = a[i + 1]; del a[i:i + 2]; return v
    return d
only, sheet, S = opt("--only"), opt("--sheet"), int(opt("--size", "320"))
which, out_path = a[0], os.path.join(root, a[1])
FPS, T0 = 15.0, 4.0
CAM = "-1.15 0.22 3.6 0.9"      # yaw pitch distance height
FAR = "-1.15 0.3 6.5 0.9"

# label, seconds, commands (time after the scene starts), camera, commands before the scene starts
SETS = {
    "moves": [
        ("DRUNK", 3.0, "-0.5 !button drunk", CAM, ""),
        ("STAGGER", 3.0, "0.2 staggerFall start=true", CAM, ""),
        ("WINDMILL", 2.6, "0.2 !button windmill;0.2 !button push back", CAM, ""),
        ("ELECTROCUTE", 2.5, "0.2 !button electrocute", CAM, ""),
        ("FLINCH", 3.0, "0.47 !gun 0.3,0.1,0.0;1.0 !gun 0.25,0.25,0.35", CAM, ""),
        ("ICE", 2.6, "0.1 !button ice;0.15 !button drunk", CAM, ""),
    ],
    "action": [
        ("SHOVE", 4.5, "0.3 applyImpulse partIndex=10 impulse=70,0,0;2.6 applyImpulse partIndex=10 impulse=-60,40,0", CAM, ""),
        ("KNOCKED DOWN", 3.0, "0.3 applyImpulse partIndex=10 impulse=0,200,0", FAR, ""),
        ("SHOT", 3.0, "0.4 !shoot 10;1.1 !shoot 10;1.6 !shoot 10", CAM, ""),
        ("BLAST", 3.5, "0.4 !blast 0.3,0.6,0.0", FAR, ""),
        ("WRECKING BALL", 4.0, "0.2 !button wrecking ball", FAR, ""),
        ("HIGH FALL", 3.5, "0.2 !hfall 9", FAR, ""),
    ],
}

def font(size):
    for f in ("arialbd.ttf", "arial.ttf"):
        try: return ImageFont.truetype(f, size)
        except OSError: pass
    return ImageFont.load_default()
F = font(max(12, S // 18))

def square(im):
    w, h = im.size
    s = min(w, h)
    return im.crop(((w - s) // 2, (h - s) // 2, (w + s) // 2, (h + s) // 2)).resize((S, S), Image.LANCZOS)

def label(im, text):
    d = ImageDraw.Draw(im)
    x, y, h = S // 16, S - S // 6, F.size
    d.rectangle((x, y - 2, x + 2, y + h + 2), fill=(230, 80, 60))
    d.text((x + 9, y + 1), text, font=F, fill=(0, 0, 0))
    d.text((x + 8, y), text, font=F, fill=(255, 255, 255))
    return im

tmp = os.path.join(tempfile.gettempdir(), "delirium-film-gif")
def film(name, secs, cmds, cam, before):
    out = os.path.join(tmp, "s_" + "".join(c for c in name.lower() if c.isalnum()))
    n, best = int(secs * FPS), None
    for attempt in range(3):
        shutil.rmtree(out, ignore_errors=True)
        os.makedirs(out)
        lines = [(2.0, "!look void"), (2.05, "!set soft 1"), (2.1, "!hide"), (2.15, "!pedcol opaque"), (2.2, f"!cam {cam}"), (2.3, "!skel"), (2.5, "!button balance")]
        for c in filter(None, (before + ";" + cmds).split(";")):
            t, rest = c.strip().split(" ", 1); lines.append((T0 + float(t), rest))
        for k in range(n):
            lines.append((T0 + k / FPS + 0.005, f"!screenshot {out}/f{k:03}.png".replace("\\", "/")))
        lines.append((T0 + n / FPS + 0.8, "!quit"))
        script = os.path.join(out, "script.txt")
        open(script, "w").write("".join(f"{t:.3f} {c}\n" for t, c in sorted(lines, key=lambda x: x[0])))
        r = subprocess.run([os.path.join(root, "target", "release", "delirium-room.exe"), "--script", script], cwd=root, capture_output=True, text=True, timeout=300)
        got = {int(f[1:4]): square(Image.open(os.path.join(out, f)).convert("RGB")) for f in os.listdir(out) if f.endswith(".png")}
        print(name, "try", attempt + 1, "exit", r.returncode, "frames", len(got), "of", n, flush=True)
        if best is None or len(got) > len(best): best = got
        if len(got) >= n - 1: break
    shutil.rmtree(out, ignore_errors=True)
    frames, last = [], Image.new("RGB", (S, S))
    for k in range(n):
        last = best.get(k, last); frames.append(label(last.copy(), name))
    return frames

scenes = [s for s in SETS[which] if not only or s[0].lower() in only.lower().split(",")]
work = os.path.join(tmp, "out")
shutil.rmtree(work, ignore_errors=True)
os.makedirs(work)
n_out, picks = 0, []
for s in scenes:
    fr = film(*s)
    picks += fr[::max(1, len(fr) // 6)][:6]
    for im in fr:
        im.save(os.path.join(work, f"o{n_out:05}.png")); n_out += 1
if sheet:
    sh = Image.new("RGB", (6 * S, S * len(scenes)))
    for i, im in enumerate(picks): sh.paste(im, ((i % 6) * S, (i // 6) * S))
    sh.save(sheet)
r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(work, "o%05d.png"), "-vf",
                    "split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer:bayer_scale=4", out_path], capture_output=True, text=True)
print("ffmpeg", r.returncode, r.stderr[-300:], out_path, n_out, "frames", os.path.getsize(out_path) // 1024, "KB")
shutil.rmtree(tmp, ignore_errors=True)
look = os.path.join(root, "target", "release", "delirium-room.look")   # filming changes the saved look: put the usual one back
open(look, "w").write("0.78 0.79 0.81 0.58 0.59 0.61 1 0 1 0 1 -33.7 59\n")
