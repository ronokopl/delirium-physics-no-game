import struct, sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pool import rows, table, root
val, conf = table(os.path.join(root, "crates/delirium-data/src/kv-own.txt"))
for name in ("kv.map", "kv-disc.map"):
    _, rs = rows(name)
    g = collections.defaultdict(list)
    for i, (k, neg, at, how, r) in enumerate(rs):
        if k: g[(k, at)].append((i, neg))
    for (k, at), m in sorted(g.items()):
        if len(m) > 1:
            vs = [(i, val.get(i), conf.get(i), n) for i, n in m]
            a = [abs(v) for _, v, _, _ in vs if v is not None]
            ok = len(a) == len(vs) and max(a) - min(a) <= 1e-6 * max(1, max(a))
            if not ok: print(name, "kind", k, "place", at, vs)
# 16-bit and two-instruction whole numbers on the disc: what range ours must be in
_, dx = rows("kv-disc.map")
for i, (k, neg, at, how, r) in enumerate(dx):
    v = val.get(i)
    if k == 4 and v is not None and not (-32768 <= v <= 65535): print("disc 16-bit but ours is", i, v, conf.get(i))
    if k == 5: print("disc two-instruction", i, v, conf.get(i), "signed-add" if r[9] == 1 else "or")
    if k == 1 and v is not None and conf.get(i) == "low" and abs(v) < 32768: pass
