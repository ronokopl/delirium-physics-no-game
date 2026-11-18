# Lists decimal slots that hold one value at different places in the PC program. NOT part of the original.
# In the PC program each decimal constant seems to be stored once, so two slots at different places should differ.
import os, sys, collections, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pool import rows, table, root
val, conf = table(sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, "crates/delirium-data/src/kv-own.txt"))
_, pc = rows("kv.map")
f32 = lambda v: struct.unpack("<I", struct.pack("<f", v))[0]
g = collections.defaultdict(set)
for i, (k, neg, at, how, r) in enumerate(pc):
    if k == 2 and i in val:
        g[f32(abs(val[i]))].add((at, i))
trusted = lambda i: conf.get(i) in ("pinned", "high")
tt = bad = 0
for bits, m in sorted(g.items()):
    places = collections.defaultdict(list)
    for at, i in m: places[at].append(i)
    if len(places) > 1:
        tp = [at for at, sl in places.items() if any(trusted(i) for i in sl)]
        if len(tp) > 1: tt += 1
        bad += 1
        v = struct.unpack("<f", struct.pack("<I", bits))[0]
        print(f"{v:<12g}", "  ".join(f"@{at}:" + ",".join(f"{i}{conf.get(i,'?')[0]}" for i in sl) for at, sl in sorted(places.items())))
print("values at more than one place:", bad, "of which with trusted slots at two places:", tt, "distinct values:", len(g))
