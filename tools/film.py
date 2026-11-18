# Films one scripted scene in the Playroom running with NO game, and makes a contact sheet of it.
# NOT part of the original. Usage: python tools/film.py <name> "<t command>;<t command>;..." [seconds] [numbers file]
# Times are seconds after the scene starts (the room needs about 3 s to open first).
import os, subprocess, sys
from PIL import Image

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
name, cmds = sys.argv[1], sys.argv[2]
secs = float(sys.argv[3]) if len(sys.argv) > 3 else 5.0
numbers = sys.argv[4] if len(sys.argv) > 4 else os.path.join(root, "crates/delirium-data/src/kv-own.txt")
out = os.path.join(root, "run", "film", name)
os.makedirs(out, exist_ok=True)
for f in os.listdir(out):
    os.remove(os.path.join(out, f))
T0, step = 3.0, 0.2
lines = [(2.0, "!look daylight"), (2.1, "!hide"), (2.2, "!cam -1.3 0.2 4.6 0.9"), (2.5, "!button balance")]
for c in cmds.split(";"):
    c = c.strip()
    if c:
        t, rest = c.split(" ", 1)
        lines.append((T0 + float(t), rest))
n = int(secs / step) + 1
for i in range(n):
    lines.append((T0 + i * step + 0.01, f"!screenshot {out}/f{i:03}.png".replace("\\", "/")))
lines.append((T0 + secs + 0.8, "!quit"))
script = os.path.join(out, "script.txt")
open(script, "w").write("".join(f"{t:.2f} {c}\n" for t, c in sorted(lines)))
env = dict(os.environ, DELIRIUM_NUMBERS=numbers)
exe = os.path.join(root, "target", "release", "delirium-room.exe")
r = subprocess.run([exe, "--script", script], cwd=root, env=env, capture_output=True, text=True, timeout=120)
err = [l for l in r.stderr.splitlines() if "panicked" in l or "crashed" in l]
frames = sorted(f for f in os.listdir(out) if f.endswith(".png"))
print(name, "exit", r.returncode, "frames", len(frames), *err[:3])
if frames:
    pick = frames[:: max(1, len(frames) // 12)][:12]
    ims = [Image.open(os.path.join(out, f)).convert("RGB") for f in pick]
    w, h = ims[0].size
    box = (int(w * 0.2), int(h * 0.12), int(w * 0.8), int(h * 0.98))
    ims = [im.crop(box).resize((320, int(320 * (box[3] - box[1]) / (box[2] - box[0])))) for im in ims]
    cw, ch = ims[0].size
    cols = 6
    sheet = Image.new("RGB", (cols * cw, ((len(ims) + cols - 1) // cols) * ch), "white")
    for i, im in enumerate(ims):
        sheet.paste(im, ((i % cols) * cw, (i // cols) * ch))
    sheet.save(os.path.join(root, "run", "film", name + ".jpg"), quality=85)
