# Turns a motion made with NVIDIA's Kimodo (https://github.com/nv-tlabs/kimodo) into the text the no-game Playroom
# reads as a get-up clip (crates/delirium-room/src/getup-front-kimodo.txt / getup-back-kimodo.txt). NOT part of the original.
# Run with Kimodo's own Python (it needs Kimodo's skeleton):
#   <kimodo>/.venv/Scripts/python tools/kimodo_to_clip.py <motion.npz> <out.txt> [--from FRAME] [--to FRAME] [--speed 1.0] [--note TEXT]
# The text: "fps hip-height speed", then each of Homer's 21 parts' bone direction in Kimodo's T-pose, then one line per frame:
# each part's turn from that T-pose (x y z w), where the hips are on the floor, and four 0/1 marks: left foot, right foot,
# left hand, right hand resting on the floor (a foot: low and not moving; a hand: low). Axes: x right, y forward, z up.
import sys
import numpy as np
import torch
from kimodo.skeleton.registry import build_skeleton

a = sys.argv[1:]
def opt(name, default=None):
    if name in a:
        i = a.index(name); v = a[i + 1]; del a[i:i + 2]; return v
    return default
first, last, note, speed = opt("--from"), opt("--to"), opt("--note", ""), float(opt("--speed", "1"))
src, out = a[0], a[1]
d = np.load(src)
G, P = d["global_rot_mats"], d["posed_joints"]
if G.ndim == 5: G, P = G[0], P[0]
T, J = G.shape[:2]
sk = build_skeleton(J)
names = sk.bone_order_names
ix = {n: i for i, n in enumerate(names)}
eye = torch.eye(3).repeat(1, J, 1, 1)
rest_rot, rest, _ = sk.fk(eye, torch.zeros(1, 3))
rest, rest_rot = rest[0].numpy(), rest_rot[0].numpy()
# Kimodo: y up, z forward, x to his left. Ours: x right, y forward, z up.
C = np.array([[-1.0, 0, 0], [0, 0, 1], [0, 1, 0]])
assert rest[ix["LeftArm"], 0] > 0 and np.allclose(rest_rot, np.eye(3), atol=1e-4), "T-pose is not what this script assumes"

# Homer's parts in order, and the Kimodo joint each follows (a pair: halfway between the two)
PARTS = ["Hips", "LeftLeg", "LeftShin", "LeftFoot", "RightLeg", "RightShin", "RightFoot", "Spine1", "Spine2", ("Spine2", "Chest"), "Chest",
         "Neck1", "Head", "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand", "RightShoulder", "RightArm", "RightForeArm", "RightHand"]
# the bone each limb part lies along in the T-pose; none for the trunk, head and feet (upright and flat in both bodies)
BONE = {1: ("LeftLeg", "LeftShin"), 2: ("LeftShin", "LeftFoot"), 4: ("RightLeg", "RightShin"), 5: ("RightShin", "RightFoot"),
        13: ("LeftShoulder", "LeftArm"), 14: ("LeftArm", "LeftForeArm"), 15: ("LeftForeArm", "LeftHand"), 16: ("LeftHand", "LeftHandMiddleEnd"),
        17: ("RightShoulder", "RightArm"), 18: ("RightArm", "RightForeArm"), 19: ("RightForeArm", "RightHand"), 20: ("RightHand", "RightHandMiddleEnd")}

def quat(m):
    w = np.sqrt(max(0.0, 1 + m[0, 0] + m[1, 1] + m[2, 2])) / 2
    x = np.sqrt(max(0.0, 1 + m[0, 0] - m[1, 1] - m[2, 2])) / 2
    y = np.sqrt(max(0.0, 1 - m[0, 0] + m[1, 1] - m[2, 2])) / 2
    z = np.sqrt(max(0.0, 1 - m[0, 0] - m[1, 1] + m[2, 2])) / 2
    return np.array([np.copysign(x, m[2, 1] - m[1, 2]), np.copysign(y, m[0, 2] - m[2, 0]), np.copysign(z, m[1, 0] - m[0, 1]), w])

dirs = []
for k in range(len(PARTS)):
    if k in BONE:
        v = C @ (rest[ix[BONE[k][1]]] - rest[ix[BONE[k][0]]]); v /= np.linalg.norm(v)
    else:
        v = np.zeros(3)
    dirs += list(v)
feet = [ix[n] for n in ("LeftFoot", "RightFoot", "LeftToeBase", "RightToeBase")]
hips = rest[ix["Hips"], 1] - min(rest[i, 1] for i in feet)
lo, hi = int(first or 0), int(last or T - 1)

def tidy(m):   # close gaps of up to 2 frames, drop marks shorter than 4
    m = [bool(x) for x in m]
    def runs(v):
        out, s = [], None
        for i, x in enumerate(m + [not v]):
            if x == v and s is None: s = i
            if x != v and s is not None: out.append((s, i)); s = None
        return out
    for s, e in runs(False):
        if s > 0 and e < len(m) and e - s <= 2: m[s:e] = [True] * (e - s)
    for s, e in runs(True):
        if e - s < 4: m[s:e] = [False] * (e - s)
    return m
def speed_of(j):
    v = np.zeros(T)
    v[1:-1] = np.linalg.norm(P[2:, j] - P[:-2, j], axis=1) * 15
    v[0], v[-1] = v[1], v[-2]
    return v
marks = []
for toe, ankle in (("LeftToeBase", "LeftFoot"), ("RightToeBase", "RightFoot")):
    marks.append(tidy((P[:, ix[toe], 1] < 0.10) & (speed_of(ix[toe]) < 0.2) & (speed_of(ix[ankle]) < 0.3)))
for hand in ("LeftHand", "RightHand"):
    marks.append(tidy(P[:, ix[hand], 1] < 0.12))
lines = [f"# {note}".rstrip(), f"# made with NVIDIA Kimodo from {src.replace(chr(92), '/').split('/')[-1]}, frames {lo}-{hi}", f"30 {hips:.4f} {speed:g}", " ".join(f"{v:.4f}" for v in dirs)]
prev = [None] * len(PARTS)
for f in range(lo, hi + 1):
    row = []
    for k, p in enumerate(PARTS):
        if isinstance(p, tuple):
            qa, qb = quat(C @ G[f, ix[p[0]]] @ C.T), quat(C @ G[f, ix[p[1]]] @ C.T)
            q = qa + (qb if qa @ qb >= 0 else -qb); q /= np.linalg.norm(q)
        else:
            q = quat(C @ G[f, ix[p]] @ C.T)
        if prev[k] is not None and prev[k] @ q < 0: q = -q
        prev[k] = q
        row += list(q)
    at = C @ P[f, ix["Hips"]]
    lines.append(" ".join(f"{v:.5f}" for v in row) + f" {at[0]:.4f} {at[1]:.4f} " + " ".join(str(int(m[f])) for m in marks))
open(out, "w").write("\n".join(lines) + "\n")
print(out, hi - lo + 1, "frames; hip height in the T-pose", round(float(hips), 3), "; hips at start", np.round(P[lo, ix['Hips']], 2), "at end", np.round(P[hi, ix['Hips']], 2))
