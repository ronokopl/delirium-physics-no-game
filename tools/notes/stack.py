# Stacks several versus.py sheets of the SAME stretch into one: the real row once, then each variant's row under it.
# NOT part of the original. usage: python tools/notes/stack.py out.jpg name1 name2 ... [--w 200]
import os, sys
from PIL import Image, ImageDraw
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
a = sys.argv[1:]
W = 200
if "--w" in a:
    i = a.index("--w"); W = int(a[i + 1]); del a[i:i + 2]
out, names = a[0], a[1:]
ims = [Image.open(os.path.join(root, "run", "film", n + ".jpg")) for n in names]
w, h = ims[0].size
bands = h // (2 * W)
sheet = Image.new("RGB", (w, bands * (1 + len(names)) * W))
y = 0
for b in range(bands):
    sheet.paste(ims[0].crop((0, b * 2 * W, w, b * 2 * W + W)), (0, y)); y += W
    for n, im in zip(names, ims):
        sheet.paste(im.crop((0, b * 2 * W + W, w, (b + 1) * 2 * W)), (0, y))
        ImageDraw.Draw(sheet).text((40, y + 2), n, fill=(255, 80, 80))
        y += W
sheet.save(out, quality=82)
print(out, sheet.size)
