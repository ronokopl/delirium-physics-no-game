import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pool import rows, table, root
val, conf = table(os.path.join(root, "crates/delirium-data/src/kv-own.txt"))
slots = {int(k): v for k, v in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "slots.json"))).items()}
_, rs = rows("kv.map")
LEAK = {554: 2.8415928, 557: 3.0415928, 581: 0.021}
pool = sorted((at, i, neg) for i, (k, neg, at, how, r) in enumerate(rs) if k == 2 and 12483132 <= at <= 12484972)
base = pool[0][0]
anchor = lambda i: i in LEAK or conf.get(i) in ("pinned", "high")
maxuse = int(sys.argv[1]) if len(sys.argv) > 1 else 3
for n, (at, i, neg) in enumerate(pool):
    r = (at - base) // 4
    v = LEAK.get(i, val.get(i))
    if anchor(i):
        print(f"[{r:4}] ANCHOR slot {i} = {v:g}"); continue
    lo = next(((LEAK.get(j, val[j]), (a - base)//4) for a, j, _ in reversed(pool[:n]) if anchor(j)), None)
    hi = next(((LEAK.get(j, val[j]), (a - base)//4) for a, j, _ in pool[n+1:] if anchor(j)), None)
    print(f"[{r:4}] slot {i}{' NEG' if neg else ''} ours {v} ({conf.get(i)})  between {lo} and {hi}")
    for u in slots[i]["uses"][:maxuse]:
        print(f"         {u[0].split('/')[-1]}:{u[1]} {u[3].strip()[:170]}")
    if len(slots[i]["uses"]) > maxuse: print(f"         (+{len(slots[i]['uses']) - maxuse} more uses)")
