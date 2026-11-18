# Films the no-game Playroom at EVERY frame time of stretches of Delirium's own demo GIFs (the real thing) and writes
# one side-by-side video: real on the left, ours on the right, each stretch played twice. NOT part of the original.
# usage: python tools/versus_video.py [--out run/compare.mp4] [--only NAME,NAME] [--tmp FOLDER] [--cam "yaw pitch dist height"]
# Needs ffmpeg on the path.
import os, shutil, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
a = sys.argv[1:]
def opt(k, d=None):
    if k in a:
        i = a.index(k); v = a[i + 1]; del a[i:i + 2]; return v
    return d
out_path = os.path.join(root, opt("--out", "run/compare.mp4"))
only = opt("--only")
cam = opt("--cam", "-1.57 0.2 3.1 0.95")
import tempfile
tmp = opt("--tmp", os.path.join(tempfile.gettempdir(), "delirium-versus"))
FPS, T0, S = 15.0, 4.0, 480

# name, folder of real frames, first, last, commands (seconds after the stretch starts), note under the title.
# The real clips do not say when each move was triggered: the times here are set by eye from where the real one starts to move.
SCENES = [
    ("DRUNK", "moves", 38, 82, "-0.5 !button drunk", "same kind of movement"),
    ("STAGGER", "moves", 165, 209, "0.2 staggerFall start=true", "same kind of movement; ours hunches less"),
    ("WINDMILL + SLAB FROM BEHIND", "moves", 210, 247, "0.2 !button windmill;0.2 !button push back", "same kind of movement; ours swings a little lower"),
    ("ELECTROCUTE", "moves", 128, 164, "0.2 !button electrocute", "same: a small standing tremor"),
    # The real clip's tracer lines show two shots that miss him: one past his chest, then one past the back of his head.
    ("FLINCH: TWO NEAR MISSES", "moves", 83, 127, "0.47 !gun 0.3,0.1,0.0;1.0 !gun 0.25,0.25,0.35", "same kind: guards, then ducks with hands over head"),
    # Ice alone leaves him standing (ours and, as far as the clip shows, the real one until he steps): he is made to stumble on it.
    ("ICE + DRUNK", "moves", 0, 37, "0.1 !button ice;0.15 !button drunk", "same kind: steps, slips, falls on his front (trigger guessed)"),
]
if only:
    SCENES = [s for s in SCENES if s[0].split()[0].lower().strip(":") in only.lower().split(",")]

def film(name, first, last, cmds):
    # Screenshots are 1600x900 PNGs: on a slow or full disk the room stalls and skips some, so they go to --tmp
    # (default: the system temp folder), the scene is filmed again if too many are missing, and a gap shows the frame before it.
    out = os.path.join(tmp, "vid_" + "".join(c for c in name.split()[0].lower() if c.isalnum()))
    n = last - first + 1
    best = None
    for attempt in range(4):
        shutil.rmtree(out, ignore_errors=True)
        os.makedirs(out)
        # the demo clips were made with the soft fill light on (no black shading on the body); the no-game default is the hard sun
        lines = [(2.0, "!look void"), (2.05, "!set soft 1"), (2.1, "!hide"), (2.15, "!pedcol opaque"), (2.2, f"!cam {cam}"), (2.3, "!skel"), (2.5, "!button balance")]
        for c in cmds.split(";"):
            t, rest = c.strip().split(" ", 1); lines.append((T0 + float(t), rest))
        for k in range(n):
            lines.append((T0 + k / FPS + 0.005, f"!screenshot {out}/f{k:03}.png".replace("\\", "/")))
        lines.append((T0 + n / FPS + 0.8, "!quit"))
        script = os.path.join(out, "script.txt")
        open(script, "w").write("".join(f"{t:.3f} {c}\n" for t, c in sorted(lines, key=lambda x: x[0])))
        exe = os.path.join(root, "target", "release", "delirium-room.exe")
        r = subprocess.run([exe, "--script", script], cwd=root, capture_output=True, text=True, timeout=240)
        got = {int(f[1:4]): square(Image.open(os.path.join(out, f)).convert("RGB")) for f in os.listdir(out) if f.endswith(".png")}
        print(name, "try", attempt + 1, "exit", r.returncode, "frames", len(got), "of", n, "missing", [k for k in range(n) if k not in got], flush=True)
        if best is None or len(got) > len(best):
            best = got
        if len(got) >= n - 1:
            break
    shutil.rmtree(out, ignore_errors=True)
    frames, lastim = [], Image.new("RGB", (S, S))
    for k in range(n):
        lastim = best.get(k, lastim); frames.append(lastim)
    return frames, n - len(best)

def font(size):
    for f in ("arialbd.ttf", "arial.ttf"):
        try: return ImageFont.truetype(f, size)
        except OSError: pass
    return ImageFont.load_default()
F1, F2 = font(22), font(16)

def square(im):
    w, h = im.size
    s = min(w, h)
    return im.crop(((w - s) // 2, (h - s) // 2, (w + s) // 2, (h + s) // 2)).resize((S, S), Image.LANCZOS)

work = os.path.join(tmp, "vid_out")
shutil.rmtree(work, ignore_errors=True)
os.makedirs(work)
HEAD, n_out, total_gaps = 64, 0, 0
for name, ref, first, last, cmds, note in SCENES:
    frames, gaps = film(name, first, last, cmds)
    total_gaps += gaps
    refdir = os.path.join(root, "run", "ref", ref)
    refs = sorted(f for f in os.listdir(refdir) if f.endswith(".png"))
    comp = []
    for k in range(last - first + 1):
        im = Image.new("RGB", (2 * S + 8, S + HEAD), (18, 18, 22))
        d = ImageDraw.Draw(im)
        d.text((10, 6), name, font=F1, fill=(255, 255, 255))
        d.text((10, 36), note, font=F2, fill=(255, 120, 90) if note.startswith("DIFFERS") else (255, 200, 90) if note.startswith("PARTLY") else (150, 220, 150))
        im.paste(square(Image.open(os.path.join(refdir, refs[first + k])).convert("RGB")), (0, HEAD))
        im.paste(frames[k], (S + 8, HEAD))
        for x, label in ((0, "REAL Delirium (its own demo clip)"), (S + 8, "This copy, no game files")):
            d.rectangle((x, HEAD, x + 8 + d.textlength(label, font=F2) + 8, HEAD + 24), fill=(0, 0, 0))
            d.text((x + 8, HEAD + 3), label, font=F2, fill=(255, 235, 60))
        comp.append(im)
    for im in comp + comp:                              # each stretch twice
        im.save(os.path.join(work, f"o{n_out:05}.png")); n_out += 1
    for _ in range(6):                                  # short hold on the last frame
        comp[-1].save(os.path.join(work, f"o{n_out:05}.png")); n_out += 1

r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(work, "o%05d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart", out_path], capture_output=True, text=True)
print("ffmpeg", r.returncode, r.stderr[-400:], out_path, n_out, "frames", round(n_out / FPS, 1), "s; frames of ours missing:", total_gaps)
shutil.rmtree(work, ignore_errors=True)
