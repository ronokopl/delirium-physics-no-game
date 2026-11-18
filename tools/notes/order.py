import struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pool import rows, table, root
val, conf = table(os.path.join(root, "crates/delirium-data/src/kv-own.txt"))
name, lo, hi = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
_, rs = rows(name)
dec = sorted((at, i, neg, k) for i, (k, neg, at, how, r) in enumerate(rs) if k in (2, 3) and lo <= at <= hi)
c = {"pinned": "P", "high": "H", "medium": "m", "low": "l"}
out = []
for at, i, neg, k in dec:
    v = val.get(i)
    out.append(f"{at}{'d' if k == 3 else ''}{'-' if neg else ''}:{i}={v:g}{c.get(conf.get(i), '?')}" if v is not None else f"{at}:{i}=?")
print("  ".join(out))
