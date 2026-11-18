# Merges the part sheets into DeliriumNoGame's kv-own.txt and reports gaps and clashes.
import json, os, sys, glob, math, collections
here = os.path.dirname(os.path.abspath(__file__))
slots = {int(k): v for k, v in json.load(open(os.path.join(here, "slots.json"))).items()}
out_path = sys.argv[1]
PI = math.pi

def num(t):
    t = t.strip().replace("pi", str(PI)) if t.strip() in ("pi", "-pi") else t.strip()
    if t.lower().startswith(("0x", "-0x")):
        return float(int(t, 16))
    return float(t)

val, why, conf = {}, {}, {}
for p in sorted(glob.glob(os.path.join(here, "numbers", "part_*.tsv"))):
    for n, line in enumerate(open(p, encoding="utf-8", errors="replace"), 1):
        w = line.rstrip("\n").split("\t")
        if len(w) < 3 or not w[0].strip().isdigit():
            continue
        i = int(w[0])
        try:
            v = num(w[1])
        except ValueError:
            print("bad value", os.path.basename(p), n, w[:2]); continue
        val[i], conf[i], why[i] = v, w[2].strip(), (w[3].strip() if len(w) > 3 else "")

# Values the source's own docs state, and ones fixed by hand after cross-checking: these win.
pinned = {}
pp = os.path.join(here, "pinned.tsv")
if os.path.exists(pp):
    for line in open(pp, encoding="utf-8"):
        w = line.rstrip("\n").split("\t")
        if len(w) >= 2 and w[0].strip().isdigit():
            pinned[int(w[0])] = (num(w[1]), w[2] if len(w) > 2 else "pinned")
for i, (v, r) in pinned.items():
    if i in val and abs(val[i] - v) > 1e-6 * max(1, abs(v)):
        print(f"pinned overrides slot {i}: {val[i]} -> {v}")
    val[i], conf[i], why[i] = v, "pinned", r

# Two slots read from one place in the program hold one number: the surer value goes to both.
rank = {"pinned": 0, "high": 1, "medium": 2, "low": 3}
groups = collections.defaultdict(list)
for i, s in slots.items():
    if s["kind"] != "known":
        groups[(s["kind"] == "whole", s["at"])].append(i)
for (_, at), g in groups.items():
    have = [i for i in g if i in val]
    if len(g) > 1 and have:
        best = min(have, key=lambda i: rank.get(conf[i], 9))
        for i in g:
            if i != best and (i not in val or abs(val[i] - val[best]) > 1e-9 * max(1.0, abs(val[best]))):
                print(f"same place: slot {i} {val.get(i)} <- slot {best} {val[best]} ({conf[best]})")
                val[i], conf[i], why[i] = val[best], conf[best], f"same place in the program as slot {best}: " + why[best]

need = [i for i, s in slots.items() if s["kind"] != "known"]
missing = [i for i in need if i not in val]
eng = [i for i in missing if {u[0].split("/")[0] for u in slots[i]["uses"]} != {"delirium-data"}]
print("need", len(need), "have", len(need) - len(missing), "missing", len(missing), "of which engine/room", len(eng), eng[:40])

# clashes: two slots of one kind with one value, or a value a known slot already has; and forbidden literals
by = collections.defaultdict(list)
for i in need:
    if i in val:
        by[(slots[i]["kind"] == "whole", round(val[i], 9) if abs(val[i]) > 1e-6 else val[i])].append(i)
known_dec = {round(s["f32"], 7): i for i, s in slots.items() if s["kind"] == "known" and s["whole"] > 1 << 40}
known_whole = {s["whole"]: i for i, s in slots.items() if s["kind"] == "known" and s["whole"] < 1 << 40}
for (whole, v), l in sorted(by.items(), key=lambda x: x[0][1]):
    if len(l) > 1:
        print("same value", v, "whole" if whole else "decimal", [(i, conf[i]) for i in l])
for i in need:
    if i not in val: continue
    v = val[i]
    if slots[i]["kind"] == "whole":
        if v in (0, 1, 2): print("literal value", i, v)
        if int(v) in known_whole: print("repeats known whole", i, v, "= slot", known_whole[int(v)], conf[i])
    else:
        if v in (0.0, 0.5, 1.0, 2.0): print("literal value", i, v)
        if round(v, 7) in known_dec: print("repeats known decimal", i, v, "= slot", known_dec[round(v, 7)], conf[i])

with open(out_path, "w", encoding="utf-8", newline="\n") as f:
    f.write("# Delirium's numbers for running with NO game: our own stand-ins, not the game's.\n")
    f.write("# The release reads these 706 slots from the player's GTAIV.exe. Each value here was worked out from how\n")
    f.write("# the source uses the slot (its own parameter docs, physics, cross-checks) and marked with how sure it is.\n")
    f.write("# slot value   # confidence: reason\n")
    for i in sorted(need):
        if i not in val: continue
        v = val[i]
        t = str(int(v)) if slots[i]["kind"] == "whole" else repr(v)
        f.write(f"{i} {t}   # {conf[i]}: {why[i][:150]}\n")
print("wrote", out_path, collections.Counter(conf[i] for i in need if i in val))
