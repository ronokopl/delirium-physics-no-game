# Makes a contact sheet from a folder of frames. NOT part of the original.
# usage: python tools/sheet.py <folder> <out.jpg> [first] [last] [step] [cols] [width] [crop l,t,r,b as fractions]
import os, sys
from PIL import Image, ImageDraw
d, out = sys.argv[1], sys.argv[2]
fs = sorted(f for f in os.listdir(d) if f.endswith(".png"))
a = int(sys.argv[3]) if len(sys.argv) > 3 else 0
b = int(sys.argv[4]) if len(sys.argv) > 4 else len(fs) - 1
st = int(sys.argv[5]) if len(sys.argv) > 5 else 1
cols = int(sys.argv[6]) if len(sys.argv) > 6 else 8
w = int(sys.argv[7]) if len(sys.argv) > 7 else 240
crop = [float(x) for x in sys.argv[8].split(",")] if len(sys.argv) > 8 else None
pick = list(range(a, min(b, len(fs) - 1) + 1, st))
ims = []
for i in pick:
    im = Image.open(os.path.join(d, fs[i])).convert("RGB")
    if crop:
        W, H = im.size
        im = im.crop((int(W * crop[0]), int(H * crop[1]), int(W * crop[2]), int(H * crop[3])))
    im = im.resize((w, int(w * im.size[1] / im.size[0])))
    ImageDraw.Draw(im).text((4, 2), str(i), fill=(255, 255, 0))
    ims.append(im)
h = ims[0].size[1]
sheet = Image.new("RGB", (cols * w, ((len(ims) + cols - 1) // cols) * h), "white")
for k, im in enumerate(ims):
    sheet.paste(im, ((k % cols) * w, (k // cols) * h))
sheet.save(out, quality=82)
print(out, sheet.size, len(ims))
