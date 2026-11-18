# Applies a sheet of corrections (slot TAB value TAB confidence TAB [old] TAB reason) to kv-own.txt. NOT part of the original.
# usage: python tools/notes/apply.py changes.tsv [kv-own.txt]
import os, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(root, "crates/delirium-data/src/kv-own.txt")
ch = {}
for l in open(sys.argv[1], encoding="utf-8"):
    w = l.rstrip("\n").split("\t")
    if len(w) >= 3 and w[0].strip().isdigit():
        ch[int(w[0])] = (w[1].strip(), w[2].strip(), w[-1].strip())
lines, seen = [], set()
for l in open(path, encoding="utf-8").read().split("\n"):
    w = l.split("#")[0].split()
    if len(w) >= 2 and w[0].isdigit() and int(w[0]) in ch:
        i = int(w[0]); v, c, r = ch[i]; seen.add(i)
        print(f"slot {i}: {w[1]} -> {v} ({c})")
        l = f"{i} {v}   # {c}: {r}"
    lines.append(l)
new = sorted(set(ch) - seen)
body = [l for l in lines if l.strip()]
for i in new:
    v, c, r = ch[i]; print(f"slot {i}: (unset) -> {v} ({c})")
    body.append(f"{i} {v}   # {c}: {r}")
head = [l for l in body if not l.split("#")[0].split()]
rows = sorted((l for l in body if l.split("#")[0].split()), key=lambda l: int(l.split()[0]))
open(path, "w", encoding="utf-8", newline="\n").write("\n".join(head + rows) + "\n")
