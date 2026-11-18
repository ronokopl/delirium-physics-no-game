import struct, sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pool import rows, table, root
val, conf = table(os.path.join(root, "crates/delirium-data/src/kv-own.txt"))
_, pc = rows("kv.map"); _, dx = rows("kv-disc.map")
c = collections.Counter((pc[i][0], dx[i][0]) for i in range(1096))
print("pc kind, disc kind -> count", sorted(c.items()))
def stored(r):
    w = struct.unpack("<Q", r[1:9])[0]; h = struct.unpack("<I", r[9:13])[0]
    return w, struct.unpack("<d", struct.pack("<Q", w))[0], struct.unpack("<f", struct.pack("<I", h))[0]
print("slots the disc map stores as-is but the PC map reads from the program:")
for i in range(1096):
    if pc[i][0] != 0 and dx[i][0] == 0:
        w, d, f = stored(dx[i][4])
        print(f"  slot {i} pc kind {pc[i][0]} disc stored: int {w} double {d!r} float {f!r}   ours {val.get(i)} {conf.get(i)}")
print("slots the PC map stores as-is but the disc reads:")
n = 0
for i in range(1096):
    if pc[i][0] == 0 and dx[i][0] != 0:
        n += 1
        w, d, f = stored(pc[i][4])
        if n <= 80: print(f"  slot {i} disc kind {dx[i][0]} pc stored: int {w} double {d!r} float {f!r}")
print(n)
