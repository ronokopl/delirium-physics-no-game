# Rig spec: frame maths, body parts, pelvis, legs, feet

Source root: `E:\AI\claude\assets\delirium\DeliriumNoGame\crates`. Paths below are relative to it
(`delirium/src/...` unless a crate is named). Tags: **PROVEN** = follows from the code alone (given that the
character must move anatomically); **INFERRED** = best reading, with confidence stated.

## 0. The three coordinate conventions (read first)

| Space | Right | Forward | Up | Evidence |
|---|---|---|---|---|
| Asset file (joint pos/axes, part matrices) | +X | +Y | +Z | derived in 1.3 |
| Engine, body in its build/zero pose | -X | -Y | +Z | `ours` = (-x,-y,z) nmrs.rs:69-71; "the base body faces -Y" docs/modding.md:439 |
| NM "COM frame" `Snap.m` (a,b,c) | a | -c | b | 1.3 |

- **PROVEN** asset -> engine is `ours(v) = (-x, -y, z)` for every vector AND position (nmrs.rs:69-71, 132-133,
  156-162). It is a 180 degree turn about Z, a proper rotation, so handedness and cross products are preserved.
- **PROVEN** left leg (parts 1-3, joint 0-2) sits at asset -X, engine +X. Right leg at asset +X, engine -X.
- The asset origin is the character "instance" origin: `cg()` (nmrs.rs:41-46) expresses part 0's position in
  part 0's frame and `inst_place` (nmbb.rs:357-362) subtracts it. Only differences matter for joints
  (nmrs.rs:128,139,161-162), so any origin works; heights (z) are used absolutely only as differences too.

## 1. Part matrices

### 1.1 How an asset matrix becomes M34 {a,b,c,d}  (PROVEN)
- File layout: `frame = [row0,row1,row2,pos]` (sdk character.rs:41-45; nm_asset.rs:418-419).
- `asset_frame(m, true)` (nmrs.rs:328-332) builds the matrix whose ROWS are row0..2, takes its COLUMNS, applies
  `ours` to each. So local axis i of the part, in asset space, is column i = `(row0[i], row1[i], row2[i])`.
- `zero_pose[k] = asset_frame(m_k) * link(k)^-1` (nmrs.rs:305-308). M34 of a part at run time is
  `m34(frames[k].rotation * link(k))` = that quaternion applied to X,Y,Z (nmdbm.rs:837-839, 895-906), and the
  rigid path gives the same (columns of `Body.r`, which is rows of `Mat3(q*l)`: ragdoll.rs:553-556, nmdbm.rs:900-902).
- Therefore at the zero pose: `a = ours(col0)`, `b = ours(col1)`, `c = ours(col2)`, `d = ours(pos)`.
- Recipe: to get engine axes a,b,c at the zero pose write
  `row0 = (-a.x, -b.x, -c.x)`, `row1 = (-a.y, -b.y, -c.y)`, `row2 = (a.z, b.z, c.z)`, `pos = (-d.x, -d.y, d.z)`.
  Simpler: think in asset space (X right, Y fwd, Z up) and put the three local axes in the COLUMNS.
- Must be exactly orthonormal, det +1: `bodies` re-orthonormalises with `matrix_fix` (nmrs.rs:62,
  delirium-data matfix.rs:30-39) but `asset_frame` does not; the .xrt reader rejects error > 1e-4 (nm_asset.rs:282-312, 415).
- In the SDK path `links` is empty (`asset_links` only reads env `NM_LINKS`, nmdbm.rs:80-95; sdk character.rs:162),
  so `link = identity` and M34 == `frames[k].rotation`. INFERRED (high): the build's `frame.rot` of each part
  must be `Root * asset_frame(m_k)` when spawned in the zero pose, otherwise joints start off zero.

### 1.2 Part 0 quarter turn  (PROVEN, and it cancels for you)
- `bodies` applies `quarter_rows` to part 0 (nmrs.rs:48-53, 64): rows (x,y,z) -> (-y,x,z) = `R * Rz(-90deg)`.
  `rage_link(…,0)` appends the same `Rz(-90deg)` (nmdbm.rs:67-70) and `Ragdoll::new` gives part 0
  `att = Rz(+90deg)` and swaps its x/y inertia (ragdoll.rs:1938-1946).
- Effect: the solver's Link rows of part 0 are in a "RAGE" frame (right, up, back); every M34 the behaviours
  read for part 0 (`part(0)`, `pmat(0)`, `parts()` ragdoll.rs:2215-2219 via `bound()` 572-574) is the plain
  asset frame. You author the plain asset frame; nothing to compensate.
- Cross-check that pins the pelvis axes: `block()` uses reference rows `[m2, m1, -m0]` for part 0
  (nmdbm.rs:973-979, 989-995). With the pelvis matrix of 1.4 this equals the standard matrix exactly, and
  `M_pelvis * Rz(-90)` = standard matrix. Any other pelvis convention makes the COM frame wrong.

### 1.3 Which way is forward  (PROVEN)
- COM frame from `rigid::block(swap=true)`: `b = col2` (asset Z), `c = -col1` (asset -Y), `a = b x c` (asset +X)
  (rigid.rs:370-377; same in the fallback nmdbm.rs:1003-1007).
- `a` = right: left foot target is `pc - a*offset`, right is `pc + a*offset` (nmdbm.rs:429-434, 441-445);
  support polygon puts the left foot's outer edge at `-a`, the right's at `+a` (nmdbm.rs:303-308).
- `c` = BACK (the task text calls pelvis.c "forward"; it is the opposite): spine twist is zero when the target
  lies along `-c` (nmst.rs:59), hip yaw is zero when velocity is along `-c` (nmdbm.rs:501-506), "behind" is
  `c . dir > 0.7` (nmbr.rs:379), "front" is `-c` (nmhf.rs:273, 324), pedal `centre_forwards` multiplies `-p.c` (nmpd.rs:74).
- So asset forward = +Y, engine forward at the build pose = -Y. Room path agrees: idle pose is placed with
  `Rz(-90deg)` to stand (room getup.rs:160, 441; ragdoll.rs:4307-4318).

### 1.4 Axis table

| Part | a | b | c | Status | Evidence |
|---|---|---|---|---|---|
| 0 Buttocks | up | left (= c x up) | back | PROVEN | desired pelvis `{a: up, b: c x up, c}` nmdbm.rs:748-760; `reach` 332-337; nmst.rs:59; nmhf.rs:210-225; nmfow.rs:191-192 (legs reach along -a); nmpd.rs:74 |
| 7 Spine0 | up | left | back | PROVEN a,b | nmpd.rs:114-122 (`up.a < -0.4` = upside down; `(v x up).b > 0` = moving backwards) |
| 9 Spine2 | up | left | back | PROVEN | frame `[m.a, -m.b, m.c]` equated with COM `[m.b, m.a, m.c]` nmbb.rs:122-128; nmbr.rs:313-317 |
| 10 Spine3 | up | left | back | PROVEN | nmru.rs:189 (`-2c + b*side`, side +1 = left arm); nmhl.rs:76-80 (`a*len` reaches the head) |
| 8 Spine1 | up | left | back | INFERRED high | by continuity; no direct use found |
| 3,6 Feet | right | up | back | PROVEN | `support_at` nmdbm.rs:303-308; `foot_yaw` needs `up.b > 0` 1471-1472; ankle gravity uses `(n.b)^2` 1351; `stance` compares foot c with pelvis c 1116-1118 |
| 2,5 Shins | right | up (along bone) | back | PROVEN a,c | swing-leg ankle term `-(w.a)*k + c.normal` nmdbm.rs:794 |
| 1,4 Thighs | right | up (along bone) | back | INFERRED medium | no behaviour reads thigh axes; only the capsule rule below |
| 12 Head | right | up | back | PROVEN a,c | arms go to `head.d +/- head.a` (right arm on +a) nmhf.rs:310-315; `stance` head.c vs feet nmdbm.rs:1119; nmhl.rs:108 |
| 11 Neck | right | up | back | INFERRED high | lean1 from `-(c.v)`, lean2 from `-(a.v)` nmcf.rs:240-244, nmhf.rs:443-447 (a must be lateral) |
| Hands | lateral (palm) axis = a | - | - | partial | `hand.d - hand.a*(side*k)` nmgr.rs:450 (other agent) |

- **PROVEN** collision capsules lie along the part frame's local Y = b (ragdoll.rs:1456, 132-139;
  sdk include/delirium_physics.h:183 "along its frame's Y"); feet are boxes with half extents on (a,b,c).
  That matches the table: limb capsules run along the bone, pelvis/spine capsules run sideways.
- `d` (position) is the part's centre of mass and shape centre.

### 1.5 Ready-made matrices (asset space, zero pose upright, facing asset +Y)
- Standard (thigh, shin, foot, neck, head): `[[1,0,0],[0,0,-1],[0,1,0]]` -> engine a=(-1,0,0), b=(0,0,1), c=(0,1,0).
- Pelvis and Spine0..3: `[[0,-1,0],[0,0,-1],[1,0,0]]` -> engine a=(0,0,1), b=(1,0,0), c=(0,1,0).
- Matching engine quaternions (x,y,z,w) for the build frames: standard (0, 0.70711, 0.70711, 0);
  pelvis/spine (-0.5,-0.5,-0.5,0.5). Tilt a bone-aligned part by rotating all three columns together.

## 2. Joint frame maths (all joints)

- **PROVEN** frame at the zero pose = `[x, z cross x, z]`, `z = ours(twist_axis)`, `x = ours(lean_axis)` made
  perpendicular to z (nmrs.rs:132-136). The rigid path builds the same frame in asset space as
  `[lean, twist x lean, twist]` WITHOUT re-orthogonalising (nmrs.rs:197-215, 283-293). So author both axes
  as exact unit vectors, exactly perpendicular.
- **PROVEN** raw angle meanings (rigid.rs:204-208, 160-189; nmrs.rs:340-359, 390-401):
  - lean1 = rotation about +y: swings the child's twist axis toward +x (toward the lean axis).
  - lean2 = rotation about -x: swings the child's twist axis toward +y (= twist x lean).
  - twist = right-handed rotation about +z.
- **PROVEN** effector value = `raw + mid`, or `-(raw + mid)` when that axis is flipped (nmrs.rs:426-431;
  nmdbm.rs:880-884). `mid` = middle of the file's limit range; the stored frames are pre-turned by it
  (`rage_turns` nmrs.rs:183-190), so effector 0 = zero pose. File limits are in RAW sign; a flipped axis has
  effector range `(-hi, -lo)` (nmrs.rs:689-695). `set_relative(j,k,x)` = `mid + half*x` in effector space (697-701).
- Hinges: `x0 = z cross Z` (nmrs.rs:133), angle = right-handed rotation of child about `ours(twist_axis)`
  (nmrs.rs:602-603; rigid.rs:218-228). No mid offset: angle 0 = zero pose, `limits[0] = (lo,hi)` absolute.
  Hinge flips must stay false (the reader forces it, nm_asset.rs:362-364; `limits()` would honour a flip).
- JSON: joints are sorted by `index` (sdk character.rs:140); 20 joints, 21 parts (120-127); `centred` defaults true.

## 3. Hips (joints 0 left, 3 right)

- **PROVEN** z (twist_axis) points hip -> knee: `predict_knee` puts the knee at `frame * (0,0,len)`
  (nmdbm.rs:717-724); `hip_leans` uses `acos(v.z)` to the foot (346-352). Author `twist_axis = unit(knee - hip)`.
- **PROVEN** `side` = +1 left, -1 right: nmdbm.rs:780, 790 (`if i == 0 { 1.0 } else { -1.0 }`), 441-445;
  nmfow.rs:193-197; nmhf.rs:330-332.
- **PROVEN** flips: left `[false,false,false]`, right `[false,true,true]`. `leg_ik` writes
  `[mid1 + l1, side*l2 + mid2, side*tw + midT]` (nmdbm.rs:704) with `mid = flip(mid)` (917-923) and
  `predict_knee` inverts it with the same `side` (719-720). That equals `effector_angles` only if lean1 is
  never flipped and lean2/twist are flipped exactly when side = -1.
- Consequence: both hip frames are PARALLEL (same axes), mirroring is done by the flips.
- **PROVEN** lean axis x = FORWARD on both hips: positive lean1 is flexion. catchFall `hip = +leg`,
  `knee = -2*leg` (nmcf.rs:133-135, 217-222); flinch on the ground hip 1.5, knee -2 (nmfl.rs:330-331);
  rollUp hip up to 1.6 (nmru.rs:135-136). Pedal circle is in the hip x-z plane about -y (nmpd.rs:88, 94).
- Hence y = z cross x = down x forward = RIGHT on both hips.
- Signs (effector values, identical meaning on both legs):
  - lean1 > 0 = thigh FORWARD (flexion). PROVEN.
  - lean2 > 0 = thigh INWARD (adduction), < 0 = legs apart. PROVEN geometrically; agrees with rollUp
    `-(…)*spread` and writhe `-0.1 +/- 0.2` both negative (nmru.rs:145-146; nmbw.rs:133, 137).
  - twist > 0 = toes IN (internal rotation). PROVEN twice: geometry (right-hand turn about "down" moves the
    toes right) and the stance: yaw targets are `[turn - splay, -turn - splay]` with splay > 0 = toes out
    (nmdbm.rs:1116, 1172-1178), and the IK feeds yaw into twist (689-704).
- Asset vectors for vertical thighs: `twist_axis (0,0,-1)`, `lean_axis (0,1,0)` on BOTH hips.
- Limits: left file limits are effector limits. Right: lean1 same; lean2 and twist negated and swapped,
  `(-hi_L, -lo_L)`, to get mirror-equal effector ranges.
- What callers imply about ranges (INFERRED): lean1 must reach about +1.5 (flexion) and allow some negative;
  hip yaw target is clamped to +/-0.6 (nmdbm.rs:528, kv119); the "loose" option widens hip twist to at least
  +/-40 deg (nmrs.rs:7), so the original twist half-range is below 0.70 rad. Step reach is an ellipse of
  `1.5 * half_lean1` m fore/aft and `kv33 * half_lean2` m sideways (nmdbm.rs:339, 455), so the half ranges
  directly set how far he can step. Suggested: lean1 (-0.5, 1.5), lean2 (-0.6, 0.4), twist (-0.5, 0.5). Low confidence.

## 4. Knees (joints 1, 4; hinges)

- **PROVEN** bent knee = NEGATIVE angle: every leg call passes `bend = -1.0` (nmdbm.rs:780; nmfow.rs:197;
  nmhf.rs:330-332) and `bend = (pi - acos(arg)) * c.bend + off` (687); targets -2.0 (nmcf.rs:135, nmfl.rs:331);
  taper reads `-knee.actual - 1.5` (nmdbm.rs:1346). Arms use +1.0.
- **PROVEN** axis: `twist_axis = (+1,0,0)` in asset space (character's RIGHT) on BOTH knees. A right-handed
  turn about +X moves a hanging shin forward, so flexion is negative. Second proof: planted ankle
  `lean1 = asin(knee.c . ((knee - foot) x normal))` (nmdbm.rs:801-802) is positive for a forward-leaning shin
  only if knee.c is "right", and positive must be dorsiflexion (section 5).
- Limits (INFERRED, medium): `lo` at or below -2.0, `hi` about 0. Desired is clamped only to
  `mid +/- 1.6*half` (nmrs.rs:718), the hard stop is the limit itself. Knee strength tapers from 1 at -1.5 rad
  to 0.2 at -2.157 rad with slope kv281 = 1.21833 = 2/(pi - 1.5) (nmdbm.rs:1346). Project-authored poses use
  relative 0.7 and 0.6 +/- 0.3 for "nearly straight" (extras_fall.rs:1024, 1127, 1164), which fits `hi ~ 0`.
  Suggested (-2.3, 0.05).

## 5. Ankles (joints 2, 5)

- **PROVEN** lean1 > 0 = DORSIFLEXION (toes up / shin forward over the foot), same sign both feet, no flip:
  swing leg adds `acos(leg_length)` (nmdbm.rs:799); planted formula 801-802; the sagittal balance term makes
  lean1 smaller when the COM is ahead of the feet (546-560, 812-817); catchFall and rollUp use negative values
  to point the toes (nmcf.rs:133; nmru.rs:158-159).
- **PROVEN** effector lean1 = 0 means shin perpendicular to the ground with the foot flat (801-802).
- **PROVEN** lean2 is written as `pv.yaw[i] * 0.5` (nmdbm.rs:815, 819), a mirror-symmetric quantity with the
  hip-twist sign (toes in positive). So ankle lean2 is mirror-flipped between the feet.
- Twist is never driven (stays at effector 0). lean1 is finally clamped to +/-kv280 (1294-1300, value unknown).
- **NOT PROVEN: which physical motion lean2 and twist are.** Two readings:
  - H2 (recommended, about 65%): twist axis along the foot (asset `twist (0,1,0)`, `lean (0,0,1)`, y = right).
    lean1 = toes up, lean2 = foot yaw (toes in positive on the left), twist = roll. Fits NM's "twist axis
    along the child bone" (hips, and wrists in nmbr.rs:115-129), fits lean2 following hip yaw, and fits the
    "loose" option widening lean1 (50 deg) and lean2 but not twist (nmrs.rs:7).
  - H1: same frame as the hip (`twist (0,0,-1)`, `lean (0,1,0)`): lean2 = roll (inversion), twist = yaw.
  - If H2 is authored and H1 is true, the foot only yaws a little extra. The reverse makes the foot roll onto
    its edge by up to 0.3 rad while turning. H2 is the safer mistake.
- Flips (INFERRED high, by the mirror argument): left `[false,false,false]`, right `[false,true,true]`.
- Ranges (INFERRED low): original lean1 half-range is under 50 deg and lean2 under kv38 deg (nmrs.rs:7).
  Suggested lean1 (-0.9, 0.6), lean2 (-0.4, 0.4), twist (-0.2, 0.2); mirror lean2/twist on the right as in 3.

## 6. Feet

- Frame (right, up, back), centre at mid-foot. Support polygon is +/-0.05 m along a and +/-0.15 m along c
  around the part centre (kv68, kv9: nmdbm.rs:423, 1378). "Sole" point = centre - c*0.1, i.e. 0.1 m ahead (461).
- Standing foot centre is held kv131*size above the ground hit (nmdbm.rs:1255); kv131 unknown, a few cm.
  The foot box half height should be about that.
- Feet targets are pushed at least `foot_width` = 0.2392 m apart (nmdbm.rs:416-419, 1136-1139).
- Yaw hold while planted needs foot b = up and c horizontal (nmdbm.rs:1461-1490).
- Ankle gravity torque is capped about foot a (toes-up side at 0.25*max) and foot c (+/-0.5*max) (1440-1450).
- Friction multiplier by build part NAME: "…Foot" 1.0, "…Hand" 2.25, others 0.75 (ragdoll.rs:23-25). Other code
  also keys on build names `L_Thigh`, `L_Calf`, `L_Foot`, `Pelvis`, `_Spine`, `Neck`, `Head`, `_L_`/`_R_`,
  `Clavicle`, `UpperArm`, `Forearm` (nm.rs:74-90; ragdoll.rs:360, 4400-4436).

## 7. Zero pose for the legs

- **PROVEN** it is the reference of maximum leg extension: `pelvis_height` = zero-pose pelvis z minus mean
  zero-pose foot z (nmdbm.rs:1159-1162, from `zero_places` = asset part positions, nmrs.rs:310-326);
  `stance` divides the current height by it and caps at 1 (1114-1115); standing target height is
  `pelvis_height * leg_length` (744, 1256).
- **PROVEN** knee 0 = straight (bends only negative), ankle 0 = flat foot under a vertical shin, hip 0 = thigh
  along its twist axis. So: standing upright, legs straight, feet flat.
- INFERRED: feet in the zero pose pointing straight ahead is the simplest consistent choice; the constants
  below describe the game's idle stance, not the zero pose.
- `Effector.zero` (used by `blend_to_zero`) is the angle set at agent creation, not the asset zero (nmrs.rs:488-489, 562).

Known values kv269-281 (all describe the ORIGINAL character; `set_zero*` in nm.rs:633-657 would recompute
them but nothing in the SDK or room calls it, so they are always used for our rig too):

| Slot | Value | Name | Meaning |
|---|---|---|---|
| 269 | 0.9898098 | CHAR_LEGS.0 | idle pelvis height / zero-pose pelvis height; used as `leg_length` (nm.rs:443; nmdbm.rs:1164) |
| 270 | 0.2392247 | CHAR_LEGS.1 | idle horizontal foot spacing * kv18 (0.75 -> 0.319 m real); used as min foot spacing and step size |
| 271 | 0.0831231 | CHAR_YAW.0 "splay" | asin(up.(r.c x l.c))/4: feet 0.3325 rad apart, each about 9.5 deg toes out |
| 272 | 0.0446337 | CHAR_YAW.1 "turn" | asin(up.(feet.c x pelvis.c))/2: pelvis 5.1 deg left of the feet |
| 273 | 0.9895031 | MARGE_LEGS.0 | same as 269 for the female rig |
| 274 | 0.1437579 | MARGE_LEGS.1 | same as 270 (0.192 m real) |
| 275 | 0.0180682 | MARGE_YAW.0 | used negated: slight toe-in |
| 276 | 0.0555569 | MARGE_YAW.1 | used negated |
| 277 | 0.2964098 | CHAR_HEAD | asin(up.(feet.c x head.c)), 17 deg; only the melee look uses it (nmshot.rs:1122) |
| 278 | 0.0963944 | MARGE_HEAD | same, female |
| 279 | 0.1285 | HIP_DIST | horizontal distance pelvis centre -> left hip joint, so hips about 0.257 m apart (nmdbm.rs:1140, 1155) |
| 281 | 1.2183290 | knee taper | 2/(pi - 1.5), section 4 |

Resulting standing hip-yaw targets: left 0.0446 - 0.0831 = -0.0385, right -0.0446 - 0.0831 = -0.1278 rad
(nmdbm.rs:540). Slot 280 (ankle clamp) is not in the known sheet.

## 8. Hard-coded body dimensions

| What | Value | Where |
|---|---|---|
| Total ragdoll mass of the original | 77.69 kg (kv205) | nm.rs:427; 77.7 `HOMER_KG` room world.rs:204; "kg 77" delirium_physics.h:109 |
| Height the tuning assumes | about 1.8 m; "Average" profile 1.75 m / 77 kg returns the base body unchanged | docs/modding.md:347, 822; ragdoll.rs:4501, 4568-4571 |
| Hip joint half spacing | 0.1285 m (kv279) | nmdbm.rs:1146 (only used when size != 1) |
| Foot spacing / step width | 0.2392 m (kv270), +0.2 m tolerance | nmdbm.rs:426, 1136-1142 |
| Foot support half width / half length | 0.05 / 0.15 m | nmdbm.rs:423, 1378 |
| Foot centre to ball | 0.1 m | nmdbm.rs:461 |
| Reach centre below pelvis | 0.4 m (kv116) | nmdbm.rs:336 |
| Leg length reference | zero-pose pelvis-to-foot-centre height, floor 0.7 m | nmdbm.rs:1159; nm.rs:612 |
| Ground probe | from knee height down max(size, 1) m | nmdbm.rs:1250-1252 |
| Balance gives up | COM under 0.5 m above the lower foot (taper on); "standing" needs over 0.7 m | nmdbm.rs:1235, 1241 |
| Step look-ahead / step offset | 0.2 s * size; `step*0.3 + kv130*size` | nmdbm.rs:1165 |
| Part masses | asset mass replaces build mass; floor 0.1 kg; inertia = shape unit inertia * asset mass | ragdoll.rs:1934-1948 |
| Pedal circle | radius 0.25 m default, centre `r - kv523` along pelvis a | nm.rs:237; nmpd.rs:70-74 |
| Gravity | kv34 | ragdoll.rs:13 |

Not hard-coded anywhere I found: thigh/shin lengths, part radii, pelvis height in metres. They come from the rig.

## 9. Leg authoring checklist (asset space: X right, Y forward, Z up)

1. Parts: pelvis/spine matrix and standard matrix from 1.5; positions = part centres.
2. Hips: `pos`, `twist (0,0,-1)` (or unit knee-hip), `lean (0,1,0)`; flips L `[f,f,f]`, R `[f,t,t]`.
3. Knees: `three=false`, `twist (1,0,0)`, limits `(neg, ~0)`, flips false.
4. Ankles: `twist (0,1,0)`, `lean (0,0,1)` (H2); flips L `[f,f,f]`, R `[f,t,t]`.
5. Right-side raw limits for flipped axes = `(-hi_L, -lo_L)`.
6. Zero pose: legs straight and vertical, feet flat; left leg at -X.

## 10. Open points, most important first

1. Ankle lean2/twist physical meaning (H2 vs H1). Code fixes only lean1 and the mirror rule.
2. Original limit ranges are unknown; only bounds and usage hints exist.
3. Unknown slots that touch the legs: kv131 (foot centre height), kv280 (ankle lean1 clamp), kv33 (side reach
   factor), kv38 (loose ankle lean2), kv523 (pedal), kv130.
4. Thigh and Spine1 part axes are by analogy only.
5. The SDK path needs build frames equal to the asset frames (1.1); I did not trace the build section further.
6. Homer's stance constants stay active for a custom rig (section 7), so a rig with very different hip width
   or foot turn-out will be steered toward his stance.
