# Checks our stand-in decimals against the ORDER the release's maps give them. NOT part of the original.
# kv.map (PC program) and kv-disc.map (disc program) say where each number sits. In both programs the decimal
# constants sit in pools sorted by value, so the order of two slots' places is the order of their values, and two
# slots at one place hold one number. No game file is read: only the two maps that ship with Delirium.
# usage: python tools/notes/pool.py [kv-own.txt] [--all]
import os, struct, sys
here = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(os.path.dirname(here))
N = 1096

def rows(name):
    b = open(os.path.join(root, "crates/delirium-data/src", name), "rb").read()
    out = []
    for i in range(N):
        r = b[44 + i * 13: 44 + (i + 1) * 13]
        out.append((r[0] & 0x7f, bool(r[0] & 0x80), struct.unpack("<I", r[1:5])[0], r[5], r))
    return b[:4], out

def table(path):
    val, conf = {}, {}
    for l in open(path, encoding="utf-8"):
        body, _, note = l.partition("#")
        w = body.split()
        if len(w) >= 2 and w[0].isdigit():
            val[int(w[0])] = float(int(w[1], 16)) if w[1].startswith("0x") else float(w[1])
            conf[int(w[0])] = note.strip().split(":")[0]
    return val, conf

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    val, conf = table(args[0] if args else os.path.join(root, "crates/delirium-data/src/kv-own.txt"))
    for name in ("kv.map", "kv-disc.map"):
        magic, rs = rows(name)
        kinds = {}
        for k, *_ in rs:
            kinds[k] = kinds.get(k, 0) + 1
        print("==", name, magic, "kinds", kinds)
        dec = sorted((at, i, neg) for i, (k, neg, at, how, r) in enumerate(rs) if k == 2)
        # clusters: runs of decimals whose places are close together
        runs, cur = [], []
        for d in dec:
            if cur and d[0] - cur[-1][0] > 4096:
                runs.append(cur); cur = []
            cur.append(d)
        runs.append(cur)
        for run in runs:
            if len(run) < 8:
                continue
            vals = [(at, i, abs(val[i]) if i in val else None) for at, i, neg in run]
            inv = 0
            last = None
            for at, i, v in vals:
                if v is None: continue
                if last is not None and v < last[2] - 1e-9 and at != last[0]:
                    inv += 1
                last = (at, i, v)
            print(f"-- run of {len(run)} decimals, places {run[0][0]}..{run[-1][0]}, out of order: {inv}")
            if "--all" in sys.argv:
                for at, i, v in vals:
                    print(f"   {at:9} +{(at - run[0][0]) // 4:5}  slot {i:4}  {v!s:>14}  {conf.get(i, '')}")
