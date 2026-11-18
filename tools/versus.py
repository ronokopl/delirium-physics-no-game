# Films one scripted scene in the no-game Playroom at the same frame times as a stretch of one of Delirium's own demo
# GIFs (the real thing), and puts the two on one sheet: real on top, ours below. NOT part of the original.
# usage: python tools/versus.py <name> <ref folder> <first> <last> "<t cmd>;<t cmd>" [--step 4] [--cam "yaw pitch dist height"]
#        [--look NAME] [--pedcol NAME] [--skel] [--numbers FILE] [--character FILE] [--pre "<t cmd>;..."] [--fps 15] [--tmp FOLDER]
#        [--tp FILE] [--w 200]
# Times in the commands are seconds after filming starts (which is when the reference stretch starts).
import os, subprocess, sys
from PIL import Image, ImageDraw

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
a = sys.argv[1:]
def opt(k, d=None):
    if k in a:
        i = a.index(k); v = a[i + 1]; del a[i:i + 2]; return v
    return d
def flag(k):
    if k in a:
        a.remove(k); return True
    return False
step, cam, look, pedcol = int(opt("--step", "4")), opt("--cam", "-1.57 0.2 3.1 0.95"), opt("--look", "void"), opt("--pedcol", "opaque")
numbers = opt("--numbers", os.path.join(root, "crates/delirium-data/src/kv-own.txt"))
tp, W = opt("--tp"), int(opt("--w", "200"))
character, pre, fps, skel = opt("--character"), opt("--pre", ""), float(opt("--fps", "15")), flag("--skel")
name, ref, first, last, cmds = a[0], a[1], int(a[2]), int(a[3]), a[4]
import shutil, tempfile
# The frames are 1600x900 PNGs: they go to the system temp folder (a slow or full disk makes the room skip frames)
# and are deleted once the sheet is made.
out = os.path.join(opt("--tmp", os.path.join(tempfile.gettempdir(), "delirium-versus")), name)
shutil.rmtree(out, ignore_errors=True)
os.makedirs(out)
T0 = 4.0
lines = [(2.0, f"!look {look}"), (2.1, "!hide"), (2.15, f"!pedcol {pedcol}"), (2.2, f"!cam {cam}"), (2.5, "!button balance")]
if not skel:
    lines.append((2.3, "!skel"))
for c in pre.split(";"):
    if c.strip():
        t, rest = c.strip().split(" ", 1); lines.append((2.6 + float(t), rest))
for c in cmds.split(";"):
    if c.strip():
        t, rest = c.strip().split(" ", 1); lines.append((T0 + float(t), rest))
picks = list(range(first, last + 1, step))
for k, i in enumerate(picks):
    lines.append((T0 + (i - first) / fps + 0.005, f"!screenshot {out}/f{k:03}.png".replace("\\", "/")))
lines.append((T0 + (last - first) / fps + 0.8, "!quit"))
script = os.path.join(out, "script.txt")
open(script, "w").write("".join(f"{t:.3f} {c}\n" for t, c in sorted(lines, key=lambda x: x[0])))
env = dict(os.environ, DELIRIUM_NUMBERS=numbers)
if character:
    env["DELIRIUM_CHARACTER"] = character
if tp:
    env["TP"] = tp
exe = os.path.join(root, "target", "release", "delirium-room.exe")
r = subprocess.run([exe, "--script", script], cwd=root, env=env, capture_output=True, text=True, timeout=180)
err = [l for l in r.stderr.splitlines() if "panicked" in l or "crashed" in l]
frames = {int(f[1:4]): f for f in os.listdir(out) if f.endswith(".png")}
print(name, "exit", r.returncode, "frames", len(frames), "of", len(picks), *err[:3])
refs = sorted(f for f in os.listdir(ref) if f.endswith(".png"))
def tile(im, label):
    w, h = im.size
    s = min(w, h)                                   # centre square
    im = im.crop(((w - s) // 2, (h - s) // 2, (w + s) // 2, (h + s) // 2)).resize((W, W))
    ImageDraw.Draw(im).text((4, 2), label, fill=(255, 255, 0))
    return im
cols = min(12, len(picks))
rows = (len(picks) + cols - 1) // cols
sheet = Image.new("RGB", (cols * W, rows * 2 * W), "white")
for k, i in enumerate(picks):
    x, y = (k % cols) * W, (k // cols) * 2 * W
    sheet.paste(tile(Image.open(os.path.join(ref, refs[i])).convert("RGB"), f"real {i}"), (x, y))
    if k in frames:
        sheet.paste(tile(Image.open(os.path.join(out, frames[k])).convert("RGB"), "ours"), (x, y + W))
p = os.path.join(root, "run", "film", name + ".jpg")
sheet.save(p, quality=84)
print(p, sheet.size)
shutil.rmtree(out, ignore_errors=True)
