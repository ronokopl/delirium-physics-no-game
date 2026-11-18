# Writes, for every number slot, how it is stored and every place the source uses it.
import struct, re, os, sys, collections, json
root, out = sys.argv[1], sys.argv[2]
m = open(os.path.join(root, "crates/delirium-data/src/kv.map"), "rb").read()
N = 1096
slots = {}
for i in range(N):
    r = m[44+i*13:44+(i+1)*13]; k = r[0] & 0x7f
    s = {"kind": {0: "known", 1: "whole", 2: "decimal", 3: "double"}[k], "neg": bool(r[0] & 0x80), "at": struct.unpack_from("<I", r, 1)[0], "uses": []}
    if k == 0:
        w = struct.unpack_from("<Q", r, 1)[0]; h = struct.unpack_from("<I", r, 9)[0]
        s["whole"] = w; s["f32"] = struct.unpack("<f", struct.pack("<I", h))[0]; s["f64"] = struct.unpack("<d", struct.pack("<Q", w))[0]
    slots[i] = s
pat = re.compile(r"(?:delirium_data::|crate::)?kv!\((\d+)(?:\s+(\w+))?\)")
for d, _, fs in os.walk(os.path.join(root, "crates")):
    for f in sorted(fs):
        if not f.endswith(".rs"): continue
        p = os.path.join(d, f); rel = os.path.relpath(p, root).replace(os.sep, "/")[7:]
        for n, line in enumerate(open(p, encoding="utf-8", errors="replace"), 1):
            for mm in pat.finditer(line):
                a, b = max(0, mm.start() - 150), min(len(line), mm.end() + 110)
                ctx = line[a:mm.start()] + ">>>" + mm.group(0).replace("delirium_data::", "").replace("crate::", "") + "<<<" + line[mm.end():b]
                ctx = ctx.replace("delirium_data::kv!", "kv!").replace("crate::kv!", "kv!").strip()
                slots[int(mm.group(1))]["uses"].append((rel, n, mm.group(2) or "", ctx))
json.dump(slots, open(out, "w"))
tot = sum(len(s["uses"]) for s in slots.values())
print("slots", len(slots), "uses", tot)
