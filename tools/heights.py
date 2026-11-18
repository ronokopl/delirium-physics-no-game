# Reads the Playroom's --headless output (each part's place and turn per step, as hex floats) and prints how
# high the pelvis, chest, head and feet are over time: a quick "is he standing" check. NOT part of the original.
import struct, sys
names = {0: "pelvis", 10: "chest", 12: "head", 3: "footL", 6: "footR", 16: "handL", 20: "handR"}
rows = []
for line in open(sys.argv[1], encoding="utf-8", errors="replace"):
    parts = line.strip().split(" | ")
    if len(parts) != 21: continue
    try:
        f = [[struct.unpack(">f", bytes.fromhex(h))[0] for h in p.split()] for p in parts]
    except (ValueError, struct.error):
        continue
    rows.append(f)
every = int(sys.argv[2]) if len(sys.argv) > 2 else 30
print("steps", len(rows))
print("step  " + "  ".join(f"{n:>18}" for n in names.values()))
for i, f in enumerate(rows):
    if i % every == 0 or i == len(rows) - 1:
        print(f"{i:4}  " + "  ".join(f"{f[k][0]:5.2f} {f[k][1]:5.2f} {f[k][2]:5.2f}" for k in names))
if rows:
    bad = sum(1 for f in rows for p in f for x in p if x != x or abs(x) > 1e4)
    print("not-a-number or runaway values:", bad)
