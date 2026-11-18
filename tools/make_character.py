# Writes crates/delirium-room/src/homer-own.json: our own stand-in for the game's character file and body.
#
# NOT part of the original Delirium. The original reads the character (joint axes, limits, muscle strengths, part
# frames, masses) from the game's fred.xrt and the body's shapes from the game's ped model. None of that is here.
# The conventions (axes, joint frames, flips, zero pose) are the ones the engine's code expects (worked out from the
# source; see docs/no-game.md and tools/notes/rig_spec_*.md). Limits and strengths are estimates.
#
# The SIZES are measured from Delirium's own pictures of the real Homer, not taken from any game file:
#   docs/playroom.png   the skeleton drawn over him gives every joint; the camera was solved from the 0.5 m floor
#                       grid (0.1 px fit), the foot and hand boxes from their drawn outlines, widths from his outline;
#   docs/homer-wave.gif frame 0 (see-through skin, front view) checks the trunk, head and arm shapes.
# The measuring scripts are in run/body/. Heights are above the sole. What one picture cannot give (how far forward
# a joint is, the trunk parts' depth) rests on the assumptions written beside the numbers.
#
# Asset space: X right, Y forward, Z up, metres. The engine turns it half round about Z (x, y -> -x, -y).
import json, math, sys

import os
DROOP = math.radians(float(os.environ.get("DROOP_DEG", "45")))    # zero pose: arms out and this far below level, elbows straight (DROOP_DEG is for trying others)
# The pose he is made in: arms hanging as the real one's do at rest in both pictures: upper arms 17 degrees out from
# straight down, forearms almost straight down (2 degrees out). An elbow only bends one way, so that takes the upper
# arm turned in about its own length (TURN) and the elbow a little bent (BEND); the forearm then also points 17 degrees
# forward, which the pictures neither show nor rule out.
HANG = math.radians(73)
TURN, BEND = 0.70, 0.40
KG = 77.69

# Feet: boxes 0.265 long, 0.11 wide, 0.076 tall (both feet measured alike). The ankle joint is above the back half.
FOOT = (0.055, 0.038, 0.132)    # half extents: across, up, along
FOOT_AHEAD = 0.061              # foot box centre ahead of the ankle joint
Z_ANKLE = 0.1255                # ankle joint above the sole
SHIN, THIGH = 0.4085, 0.4265    # knee to ankle, hip to knee (left and right legs agreed within 1 and 15 mm)
Z_KNEE = Z_ANKLE + SHIN
Z_HIP = Z_KNEE + THIGH          # 0.9605
ROOT = (-0.010, Z_HIP - 0.017)  # pelvis part centre as (forward, height): the hip joints are 10 mm ahead of it, 17 mm above

# The trunk from the side, as (forward, up) from the pelvis centre, read with every spine joint taken to lie in his
# middle plane. The real spine is no straight post: it starts behind the pelvis centre and the neck and head are well
# forward. (He was balancing in the picture, so a few degrees of this may be lean and not build.)
J_SPINE = [(-0.020, 0.090), (-0.015, 0.160), (0.000, 0.236), (0.029, 0.351)]   # the joints into Spine0..Spine3
J_NECK, J_HEAD = (0.109, 0.589), (0.134, 0.677)                               # the joints into Neck and Head
# Part centres (forward, up from the pelvis centre), capsule radius, half length. Trunk capsules lie across the body.
PELVIS = ((0.000, 0.000), 0.1325, 0.045)        # 0.355 wide
# The trunk's outline is read from the demo clips, where he is solid (docs/moves.gif): under the chest there are four
# even rolls of one width (Spine2, Spine1, Spine0, pelvis), each showing about 0.11 m of height, the sides nearly straight.
SPINE = [((0.020, 0.110), 0.110, 0.0625),       # Spine0
         ((0.030, 0.220), 0.115, 0.0575),       # Spine1: the belly, a little further forward
         ((0.030, 0.340), 0.110, 0.0625),       # Spine2
         ((0.064, 0.466), 0.122, 0.0825)]       # Spine3: the chest, 0.41 wide
NECK = ((0.1215, 0.633), 0.066, 0.023)          # midway between its two joints
HEAD = ((0.150, 0.717), 0.0995, 0.029)          # 0.20 wide, 0.26 tall; the top of the head is at 1.79 m
J_CLAV = (0.040, 0.075, 0.529)                  # clavicle joint: (out from the middle, forward, up) from the pelvis centre
J_SHOULDER = (0.190, 0.073, 0.521)              # shoulder joint, the same way
CLAV = (0.060, 0.060)                           # radius, half length (0.24 long): mostly inside the chest, a small round shoulder showing
CLAV_DROP = 0.025                               # the part's centre is this far below the midpoint of its two joints
UPPER, FORE, HAND = 0.286, 0.269, 0.085         # shoulder to elbow, elbow to wrist, wrist to the hand's centre
UPPER_SHAPE, FORE_SHAPE = (0.045, 0.123), (0.0435, 0.1145)      # radius, half length
HAND_BOX = (0.020, 0.085, 0.038)                # half extents: through the palm, along the hand, across it
# Legs. The thigh's capsule is 15 mm inside the hip-knee line and starts 7 cm under the hip.
THIGH_SHAPE = (0.086, 0.171, 0.241, 0.015)      # radius, half length, centre below the hip joint, centre towards the middle
SHIN_SHAPE = (0.0695, 0.199, 0.229)             # radius, half length, centre below the knee joint

def v(*a): return [float(x) for x in a]
def add(a, b): return [a[i] + b[i] for i in range(3)]
def sub(a, b): return [a[i] - b[i] for i in range(3)]
def mul(a, k): return [x * k for x in a]
def cross(a, b): return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
def ours(a): return [-a[0], -a[1], a[2]]

def quat(cols):
    """Quaternion (x, y, z, w) of the rotation whose columns are the three axes."""
    m = [[cols[c][r] for c in range(3)] for r in range(3)]
    tr = m[0][0] + m[1][1] + m[2][2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        q = [(m[2][1] - m[1][2]) / s, (m[0][2] - m[2][0]) / s, (m[1][0] - m[0][1]) / s, 0.25 * s]
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2
        q = [0.25 * s, (m[0][1] + m[1][0]) / s, (m[0][2] + m[2][0]) / s, (m[2][1] - m[1][2]) / s]
    elif m[1][1] > m[2][2]:
        s = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2
        q = [(m[0][1] + m[1][0]) / s, 0.25 * s, (m[1][2] + m[2][1]) / s, (m[0][2] - m[2][0]) / s]
    else:
        s = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2
        q = [(m[0][2] + m[2][0]) / s, (m[1][2] + m[2][1]) / s, 0.25 * s, (m[1][0] - m[0][1]) / s]
    n = math.sqrt(sum(x * x for x in q))
    return [x / n for x in q]

def qmul(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return [aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz]
def qinv(a): return [-a[0], -a[1], -a[2], a[3]]

# Part frames as three local axes (x, y, z) in asset space. Capsules lie along local y.
TRUNK = [v(0, 0, 1), v(-1, 0, 0), v(0, -1, 0)]      # up, left, back
LIMB = [v(1, 0, 0), v(0, 0, 1), v(0, -1, 0)]        # right, up, back
def arm_dir(side, droop): return v(side * math.cos(droop), 0, -math.sin(droop))   # side -1 left, +1 right
def arm_axes(side, droop):
    d = arm_dir(side, droop)
    x = cross(d, v(0, 1, 0))                        # the elbow's bending axis; the palm's axis
    return [x, d, cross(x, d)]
def turned(a, axis, angle):                         # a turned right-handed about a unit axis
    c, s, k = math.cos(angle), math.sin(angle), sum(a[i] * axis[i] for i in range(3))
    w = cross(axis, a)
    return [a[i] * c + w[i] * s + axis[i] * k * (1 - c) for i in range(3)]
def arm_pose(side, droop, turn=0.0, bend=0.0):
    """(upper arm axes, forearm axes, hand axes) with the upper arm turned in about its length and the elbow bent.
    The hand is turned back at the wrist so the palm still faces the thigh, as the real one's does.
    Worked out for the left arm and mirrored, so the two sides are exact mirror images. No turn, no bend: arm_axes."""
    x, d, z = arm_axes(-1, droop)
    x, z = turned(x, d, turn), turned(z, d, turn)   # positive: the elbow's bend swings from forwards to inwards
    upper, fore = [x, d, z], [x, turned(d, x, bend), turned(z, x, bend)]
    hand = [turned(fore[0], fore[1], -turn), fore[1], turned(fore[2], fore[1], -turn)]
    if side > 0:
        flip = lambda a: [-a[0], a[1], a[2]]
        upper, fore, hand = ([mul(flip(a[0]), -1), flip(a[1]), flip(a[2])] for a in (upper, fore, hand))
    return upper, fore, hand

HIP = 0.1285                                        # the engine's own figure for pelvis centre to hip
z_ankle, z_knee, z_hip = Z_ANKLE, Z_KNEE, Z_HIP
def trunk(p, x=0.0): return v(x, ROOT[0] + p[0], ROOT[1] + p[1])            # a (forward, up) pair from the pelvis centre
SH = v(J_SHOULDER[0], ROOT[0] + J_SHOULDER[1], ROOT[1] + J_SHOULDER[2])     # right shoulder joint (left is mirrored)
CL = v(J_CLAV[0], ROOT[0] + J_CLAV[1], ROOT[1] + J_CLAV[2])                 # right clavicle joint

names = ["Buttocks", "Thigh_Left", "Shin_Left", "Foot_Left", "Thigh_Right", "Shin_Right", "Foot_Right", "Spine0", "Spine1",
         "Spine2", "Spine3", "Neck", "Head", "Clavicle_Left", "Upper_Arm_Left", "Lower_Arm_Left", "Hand_Left",
         "Clavicle_Right", "Upper_Arm_Right", "Lower_Arm_Right", "Hand_Right"]
bones = ["Char_Pelvis", "Char_L_Thigh", "Char_L_Calf", "Char_L_Foot", "Char_R_Thigh", "Char_R_Calf", "Char_R_Foot", "Char_Spine",
         "Char_Spine1", "Char_Spine2", "Char_Spine3", "Char_Neck", "Char_Head", "Char_L_Clavicle", "Char_L_UpperArm",
         "Char_L_Forearm", "Char_L_Hand", "Char_R_Clavicle", "Char_R_UpperArm", "Char_R_Forearm", "Char_R_Hand"]
parent = [None, 0, 1, 2, 0, 4, 5, 0, 7, 8, 9, 10, 11, 10, 13, 14, 15, 10, 17, 18, 19]

def body(droop, turn=0.0, bend=0.0):
    """Each part's (axes, centre, radius, half, box) with the arms at this droop, turn and elbow bend."""
    p = [None] * 21
    p[0] = (TRUNK, trunk(PELVIS[0]), PELVIS[1], PELVIS[2], None)
    for side, k in ((-1, 1), (1, 4)):
        x = side * HIP
        p[k] = (LIMB, v(x - side * THIGH_SHAPE[3], 0, z_hip - THIGH_SHAPE[2]), THIGH_SHAPE[0], THIGH_SHAPE[1], None)
        p[k + 1] = (LIMB, v(x, 0, z_knee - SHIN_SHAPE[2]), SHIN_SHAPE[0], SHIN_SHAPE[1], None)
        p[k + 2] = (LIMB, v(x, FOOT_AHEAD, FOOT[1]), FOOT[1], 0.0, v(*FOOT))
    for i, (c, r, h) in enumerate(SPINE):
        p[7 + i] = (TRUNK, trunk(c), r, h, None)
    p[11] = (LIMB, trunk(NECK[0]), NECK[1], NECK[2], None)
    p[12] = (LIMB, trunk(HEAD[0]), HEAD[1], HEAD[2], None)
    for side, k in ((-1, 13), (1, 17)):
        sh, cl = v(side * SH[0], SH[1], SH[2]), v(side * CL[0], CL[1], CL[2])
        ax, fx, hx = arm_pose(side, droop, turn, bend)
        elbow = add(sh, mul(ax[1], UPPER))
        cx, cy = v(0, 0, -side), v(side, 0, 0)
        p[k] = ([cx, cy, cross(cx, cy)], add(mul(add(sh, cl), 0.5), v(0, 0, -CLAV_DROP)), CLAV[0], CLAV[1], None)
        p[k + 1] = (ax, add(sh, mul(ax[1], UPPER / 2)), UPPER_SHAPE[0], UPPER_SHAPE[1], None)
        p[k + 2] = (fx, add(elbow, mul(fx[1], FORE / 2)), FORE_SHAPE[0], FORE_SHAPE[1], None)
        p[k + 3] = (hx, add(elbow, mul(fx[1], FORE + HAND)), HAND_BOX[0], 0.0, v(*HAND_BOX))
    return p

def pivots(droop, turn=0.0, bend=0.0):
    """Where each part joins its parent (asset space), with the arms in this pose. Part 0 has none."""
    j = [None] * 21
    for side, k in ((-1, 1), (1, 4)):
        x = side * HIP
        j[k], j[k + 1], j[k + 2] = v(x, 0, z_hip), v(x, 0, z_knee), v(x, 0, z_ankle)
    for i, c in enumerate(J_SPINE):
        j[7 + i] = trunk(c)
    j[11], j[12] = trunk(J_NECK), trunk(J_HEAD)
    for side, k in ((-1, 13), (1, 17)):
        sh = v(side * SH[0], SH[1], SH[2])
        ax, fx, _ = arm_pose(side, droop, turn, bend)
        elbow = add(sh, mul(ax[1], UPPER))
        j[k], j[k + 1], j[k + 2], j[k + 3] = v(side * CL[0], CL[1], CL[2]), sh, elbow, add(elbow, mul(fx[1], FORE))
    return j

def local(part, q):
    """The asset-space point q in the part's own axes, from its centre."""
    return [sum((q[i] - part[1][i]) * a[i] for i in range(3)) for a in part[0]]

def inside(part, q, grow=0.0):
    l, (_, _, radius, half, box) = local(part, q), part
    if box:
        return all(abs(l[i]) <= box[i] + grow for i in range(3))
    y = max(-half, min(half, l[1]))
    return l[0] * l[0] + (l[1] - y) ** 2 + l[2] * l[2] <= (radius + grow) ** 2

def cells(part, step):
    """The grid cells whose centres are inside the part."""
    c, r = part[1], (math.sqrt(sum(e * e for e in part[4])) if part[4] else part[2] + part[3])
    lo = [int(math.floor((c[i] - r) / step)) for i in range(3)]
    hi = [int(math.ceil((c[i] + r) / step)) for i in range(3)]
    return {(ix, iy, iz) for ix in range(lo[0], hi[0] + 1) for iy in range(lo[1], hi[1] + 1) for iz in range(lo[2], hi[2] + 1)
            if inside(part, ((ix + 0.5) * step, (iy + 0.5) * step, (iz + 0.5) * step))}

def volumes(parts, step=0.012):
    """Litres of each part, the space shared by overlapping parts split equally between them (a grid count)."""
    owners = {}
    for k, part in enumerate(parts):
        for c in cells(part, step):
            owners.setdefault(c, []).append(k)
    out = [0.0] * len(parts)
    for ks in owners.values():
        for k in ks:
            out[k] += step ** 3 * 1000.0 / len(ks)
    return out

zero = body(DROOP)
stand = body(HANG, TURN, BEND)

# Mass: half by size (one density through the whole body as he stands: each part weighs its own share of the space)
# and half by the shares of an ordinary man, because capsules are a crude picture of flesh: a capsule shin holds far
# more than a shin weighs, and an upper arm loses the space it shares with the chest.
ORDINARY = [9.5, 7.6, 3.6, 1.1, 7.6, 3.6, 1.1, 5.5, 6.0, 7.0, 9.5, 1.3, 4.8, 1.8, 2.1, 1.3, 0.55, 1.8, 2.1, 1.3, 0.55]
litres = volumes(stand)
twin = {1: 4, 2: 5, 3: 6, 13: 17, 14: 18, 15: 19, 16: 20}
for a, b in twin.items():                           # the grid is not exactly even left and right
    litres[a] = litres[b] = (litres[a] + litres[b]) / 2
mass = [KG * (0.5 * litres[k] / sum(litres) + 0.5 * ORDINARY[k] / sum(ORDINARY)) for k in range(21)]

def mirror(l):      # a right-side joint's raw range on a flipped axis
    return [-l[1], -l[0]]

def joint(index, name, three, pos, twist, lean, limits, right=False, stiff=10.0, torque=(300.0, 150.0)):
    lim = [list(l) for l in limits]
    if right and three:
        lim[1], lim[2] = mirror(lim[1]), mirror(lim[2])
    return {"name": name, "index": index, "three": three, "pos": pos, "twist_axis": twist, "lean_axis": lean, "limits": lim,
            "flip": [False, right and three, right and three], "muscle_stiffness": 1.0, "damping": 2.0 * stiff,
            "strength": stiff * stiff, "max_torque": list(torque), "centred": True}

joints = []
N = [0, 0]
for side, base, tag in ((-1, 0, "left"), (1, 3, "right")):
    x, r = side * HIP, side > 0
    joints.append(joint(base, f"hip_{tag}", True, v(x, 0, z_hip), v(0, 0, -1), v(0, 1, 0), [(-0.5, 1.5), (-0.6, 0.4), (-0.5, 0.5)], r, 12, (600, 300)))
    joints.append(joint(base + 1, f"knee_{tag}", False, v(x, 0, z_knee), v(1, 0, 0), v(0, 0, 0), [(-2.3, 0.05), N, N], r, 12, (500, 0)))
    joints.append(joint(base + 2, f"ankle_{tag}", True, v(x, 0, z_ankle), v(0, 1, 0), v(0, 0, 1), [(-0.9, 0.6), (-0.4, 0.4), (-0.2, 0.2)], r, 12, (250, 120)))
for k, nm in enumerate(("spine_0", "spine_1", "spine_2", "spine_3")):
    joints.append(joint(6 + k, nm, True, trunk(J_SPINE[k]), v(0, 0, 1), v(0, 1, 0), [(-0.25, 0.30), (-0.25, 0.25), (-0.3, 0.3)], False, 12, (400, 200)))
joints.append(joint(10, "neck_lower", True, trunk(J_NECK), v(0, 0, 1), v(0, 1, 0), [(-0.4, 0.4), (-0.3, 0.3), (-0.6, 0.6)], False, 10, (80, 40)))
joints.append(joint(11, "neck_upper", True, trunk(J_HEAD), v(0, 0, 1), v(0, 1, 0), [(-0.4, 0.4), (-0.3, 0.3), (-0.6, 0.6)], False, 10, (80, 40)))
for side, base, tag in ((-1, 12, "left"), (1, 16, "right")):
    r = side > 0
    sh = v(side * SH[0], SH[1], SH[2])
    d = arm_dir(side, DROOP)
    hinge = cross(d, v(0, 1, 0))
    joints.append(joint(base, f"clavicle_{tag}", True, v(side * CL[0], CL[1], CL[2]), v(side, 0, 0), v(0, 1, 0), [(-0.35, 0.45), (-0.5, 0.2), (-0.3, 0.3)], r, 10, (150, 75)))
    joints.append(joint(base + 1, f"shoulder_{tag}", True, sh, d, v(0, 1, 0), [(-1.0, 1.8), (-1.5, 0.85), (-1.6, 1.0)], r, 10, (150, 75)))
    joints.append(joint(base + 2, f"elbow_{tag}", False, add(sh, mul(d, UPPER)), hinge, v(0, 0, 0), [(0.0, 2.5), N, N], r, 10, (100, 0)))
    joints.append(joint(base + 3, f"wrist_{tag}", True, add(sh, mul(d, UPPER + FORE)), d, v(0, 1, 0), [(-0.6, 0.6), (-1.2, 1.0), (-1.2, 1.2)], r, 10, (40, 20)))
joints.sort(key=lambda j: j["index"])
for j in joints:
    j["limits"] = [[float(a), float(b)] for a, b in j["limits"]]
for k, piv in enumerate(pivots(DROOP)):             # the joint list and the parts' pivots are the same points
    assert piv is None or max(abs(a - b) for a, b in zip(piv, joints[k - 1]["pos"])) < 1e-9, names[k]

parts = []
for k, (ax, c, _, _, _) in enumerate(zero):
    rows = [[ax[col][row] for col in range(3)] for row in range(3)]     # the local axes are the matrix's columns
    parts.append({"name": names[k], "frame": rows + [c], "mass": mass[k]})

# The pairs that are tested against each other. The engine switches the leg and hand ones off itself at times.
pairs = [(1, 4), (1, 5), (2, 4), (2, 5), (2, 6), (3, 5), (3, 6), (20, 16), (20, 15), (19, 16),
         (16, 0), (20, 0), (16, 1), (20, 4), (16, 4), (20, 1), (15, 0), (19, 0), (12, 16), (12, 20), (12, 15), (12, 19),
         (16, 12), (15, 1), (19, 4), (16, 10), (20, 10), (16, 9), (20, 9), (15, 19)]
pairs = sorted({(min(a, b), max(a, b)) for a, b in pairs})
# None of them may already touch as he stands (a touching pair would be pushed apart the moment he is made).
grid = [cells(p, 0.01) for p in stand]
touching = [(names[a], names[b]) for a, b in pairs if grid[a] & grid[b]]
assert not touching, f"tested pairs that overlap in the standing pose: {touching}"

# The build: shapes, and the pose he is made in (standing, arms hanging), in the engine's space.
rot = [quat([ours(a) for a in ax]) for ax, *_ in stand]
piv = pivots(HANG, TURN, BEND)
def anchor(k, at):      # the asset-space point `at` in part k's own axes, from its centre: the same in the engine's space
    return local(stand[k], at)
build = []
for k, (ax, c, radius, half, box) in enumerate(stand):
    q = parent[k]
    hinge = k in (2, 5, 15, 19)
    build.append({
        "name": bones[k], "parent": q, "mass": mass[k], "radius": radius, "half": half,
        "offset": {"pos": v(0, 0, 0), "rot": v(0, 0, 0, 1)},
        "rest": v(0, 0, 0, 1) if q is None else qmul(qinv(rot[k]), rot[q]),
        # where the joint to the parent is, seen from the parent and from this part (the skeleton view draws these)
        "anchor_parent": v(0, 0, 0) if q is None else anchor(q, piv[k]), "anchor": v(0, 0, 0) if q is None else anchor(k, piv[k]),
        "limit": "locked" if q is None else {"cone": {"swing": 1.2 if not hinge else 2.3, "twist": 0.6}},
        "lower": k <= 6, "reach": k in (14, 15, 18, 19), "bind": rot[k],
        **({"boxed": box} if box else {}),
        "inertia": v(0, 0, 0), "length": 2.0 * half,
        "frame": {"pos": ours(c), "rot": rot[k]},
    })

out = {"format": "nm-character-1", "joints": joints, "parts": parts, "self_collision": [list(p) for p in pairs], "build": build}
if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "crates/delirium-room/src/homer-own.json"
    json.dump(out, open(path, "w", encoding="utf-8", newline="\n"), indent=1)
    top = max(p[1][2] + p[2] + p[3] for p in stand)
    com = [sum(mass[k] * stand[k][1][i] for k in range(21)) / KG for i in range(3)]
    print("wrote", path, "mass", round(sum(mass), 2), "kg, head top", round(top, 3), "m, centre of mass", round(com[1], 3), "m ahead of the ankles,", round(com[2], 3), "m up")
    if "-v" in sys.argv:
        for k in range(21):
            print(f"  {k:2} {names[k]:16} {litres[k]:6.2f} l  {mass[k]:6.2f} kg")
