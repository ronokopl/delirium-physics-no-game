# Films scripted scenes in the no-game Playroom at a real frame rate and joins them into one video. NOT part of the original.
# usage: python tools/film_video.py <out.mp4> [--fps 30] "<title>|<seconds>|<t command>;<t command>;..." [more scenes...]
# Frames go to the system temp folder (a full or slow disk makes the room skip screenshots); a skipped frame shows the one before.
import os, shutil, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
a = sys.argv[1:]
fps = 30.0
if "--fps" in a:
    i = a.index("--fps"); fps = float(a[i + 1]); del a[i:i + 2]
out_path, scenes = os.path.join(root, a[0]), a[1:]
tmp = os.path.join(tempfile.gettempdir(), "delirium-film-video")
shutil.rmtree(tmp, ignore_errors=True)
os.makedirs(os.path.join(tmp, "out"))
T0 = 3.0
try: F = ImageFont.truetype("arialbd.ttf", 26)
except OSError: F = ImageFont.load_default()
n_out = missing = 0
for s, scene in enumerate(scenes):
    title, secs, cmds = scene.split("|", 2)
    n = int(float(secs) * fps)
    d = os.path.join(tmp, f"s{s}"); os.makedirs(d)
    lines = [(2.0, "!look studio"), (2.1, "!hide"), (2.2, "!cam -1.3 0.2 4.6 0.9"), (2.5, "!button balance")]
    for c in cmds.split(";"):
        t, rest = c.strip().split(" ", 1); lines.append((T0 + float(t), rest))
    for k in range(n):
        lines.append((T0 + k / fps + 0.002, f"!screenshot {d}/f{k:04}.png".replace("\\", "/")))
    lines.append((T0 + n / fps + 0.8, "!quit"))
    script = os.path.join(d, "script.txt")
    open(script, "w").write("".join(f"{t:.3f} {c}\n" for t, c in sorted(lines, key=lambda x: x[0])))
    r = subprocess.run([os.path.join(root, "target", "release", "delirium-room.exe"), "--script", script], cwd=root, capture_output=True, text=True, timeout=600)
    last, got = Image.new("RGB", (1280, 720)), 0
    for k in range(n):
        p = os.path.join(d, f"f{k:04}.png")
        if os.path.exists(p):
            last = Image.open(p).convert("RGB").resize((1280, 720), Image.LANCZOS); got += 1
            dr = ImageDraw.Draw(last); dr.rectangle((0, 0, 1280, 44), fill=(0, 0, 0)); dr.text((12, 7), title, font=F, fill=(255, 235, 60))
        last.save(os.path.join(tmp, "out", f"o{n_out:05}.jpg"), quality=92); n_out += 1
    missing += n - got
    print(title, "exit", r.returncode, "frames", got, "of", n, flush=True)
    shutil.rmtree(d, ignore_errors=True)
r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", os.path.join(tmp, "out", "o%05d.jpg"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart", out_path], capture_output=True, text=True)
print("ffmpeg", r.returncode, r.stderr[-300:], out_path, round(n_out / fps, 1), "s at", fps, "fps; frames missing:", missing)
shutil.rmtree(tmp, ignore_errors=True)
