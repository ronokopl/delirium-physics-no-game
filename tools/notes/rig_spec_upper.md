# Rig spec, upper body: spine, neck/head, clavicles, shoulders, elbows, wrists

Scope: joints 6-19 and parts 7-20 of the 21-part rig. Paths are relative to `crates/`. Line numbers are those of the
shipped sources. Tags: **[PROVEN]** = follows from the code's own arithmetic; **[INFERRED hi/med/low]** = deduced from
what a behaviour is meant to look like, or from anatomy. A numeric re-implementation of `rotation`, `angles`,
`rage_turns`, `effector_angles` and `pose` (script `upper_check.py` in this scratchpad) confirmed sections 1 and 3.

## 0. Coordinate systems

- **Asset space is X = character's right, Y = forward, Z = up** [PROVEN for the non-rigid path, hi overall].
  `Body::block` (delirium/src/nmdbm.rs:984-1007) averages `part_rotation * zero_rotation^-1`; in the zero pose that is
  `diag(-1,-1,1)`, and it then takes `c = -row(1)`, `a = row(2) x c`, i.e. engine back = +Y, right = -X. Undoing
  `ours` (-x,-y,z; nmrs.rs:69-71) gives asset back = -Y, right = +X. The COM frame is a = right, b = up, c = back
  (left foot target is `pc - a*so`, nmdbm.rs:431-433; "forward" is `-m.c` at nmhf.rs:324, nmcf.rs:195).
- `ours` is a 180 degree turn about Z, a proper rotation, so every relation below can be read directly in asset
  space. All vectors in this document are **asset-space** unless stated.
- Index 0 = left, 1 = right everywhere (`limb(i)`, nmshot.rs:26-34; PARTS names, delirium-data/src/nm_asset.rs:381).

## 1. What the three angles mean (all 3-axis joints)

Joint frame (nmrs.rs:132-135): `z = twist_axis`, `x = lean_axis` made perpendicular to z, `y = z cross x`.

- **[PROVEN]** raw lean1 > 0 swings the child's twist axis toward **+x (the lean axis)**; raw lean2 > 0 swings it
  toward **+y = twist x lean**; raw twist > 0 is a right-handed turn about z. Source: `rotation` / `angles`
  (nmrs.rs:340-359, 390-401), and the IK that feeds them: `hip_leans` uses `l1 ~ v.x`, `l2 ~ v.y` (nmdbm.rs:346-352).
- **[PROVEN]** effector angle = raw + mid, or `-raw - mid` if that axis is flipped (nmrs.rs:426-431); effector
  angle 0 on every axis is exactly the asset pose even when the limit mids are not 0 (frames are pre-turned by the
  mids, nmrs.rs:183-190, 295-303; checked numerically).
- **[PROVEN]** asset `limits` are in raw (unflipped) sense about those axes, measured from the zero pose. In effector
  space a flipped axis has range `(-hi, -lo)` (`Character::limits`, nmrs.rs:689-695). The hard limit is an ellipse
  with half-axes (half lean1, half lean2) about the mid direction, twist +/- half about its mid
  (delirium/src/ragdoll.rs:634-637). Targets are clamped to that ellipse scaled by `1 + 20/strength`
  (nmrs.rs:542-556). **A zero-width lean range divides by zero** (nmrs.rs:548): never author one.
- Hinges: angle = right-handed turn of child about `twist_axis`, 0 at the zero pose (nmrs.rs:601-604); no flip
  (reader forces false, nm_asset.rs:362-364); desired is clamped to `mid +/- 1.6*half` (nmrs.rs:718) and the hard
  limit is `[lo, hi]` as written (ragdoll.rs:636).
- `set_relative(j,k,x)` writes `mid + half*x` in effector space (nmrs.rs:697-701).
- Trap: `Effector.zero` / `blend_to_zero` is NOT the asset zero pose; it is the joint angles of the pose the
  character was created in (nmrs.rs:488-490, 513-518, 562).

## 2. Mirroring and flip flags

- **[PROVEN] Shoulders: left flip = [false,false,false], right flip = [false,true,true].** The limb IK returns
  geometric raw angles and writes `[mid1 + l1, side*l2 + mid2, side*tw + midtw]` (nmdbm.rs:704) with mids already
  flip-signed (nmdbm.rs:919-923). That only reproduces the raw angles if lean2/twist are flipped exactly where
  `side = -1` and lean1 never is. Arm callers pass side = +1 left, -1 right (table in section 5).
- **[PROVEN] Wrists: same pattern.** `Shot::wrist` / `brace_wrist` build the frame `(pa, pb*side, pc)` and write
  `[-(phi*s), phi*co, tw]` in it (delirium/src/nmshot.rs:1063-1087, nmbr.rs:115-130): the y axis is mirrored by
  `side`, which is what flip[1], flip[2] on the right do.
- **[INFERRED hi] Clavicles: same pattern.** No side sign anywhere; identical values go to both (windmill
  nmaw.rs:84-85; catch fall `[l1, l2, 0.3]` nmcf.rs:333; flinch `(-0.4, -0.5)` nmfl.rs:310), `clav_follow` copies
  shoulder effector leans to the clavicle by limit ratio (nmcf.rs:344-349), and spine twist writes `+x` right,
  `-x` left on lean1 on purpose (nmst.rs:71-74).
- **[PROVEN, numerically checked]** With flips [F,T,T] on the right, equal effector values give mirror-image poses
  iff the right joint's `twist_axis` and `lean_axis` are the plain left-right mirror images of the left's
  (negate X). To keep effector ranges equal, the right joint's asset limits on axes 1 and 2 must be
  `(-hi_left, -lo_left)`; axis 0 is copied.
- Elbows (hinges, no flip): the same positive angle is written to both (nmbb.rs:301, nmbf.rs:90), so the right hinge
  axis must be **minus** the mirror image of the left one [PROVEN given symmetric intent].
- Spine and neck: central, no flips needed [INFERRED hi]; nothing multiplies them by a side sign.
- Contradiction on record: extras_fall.rs:410-414 writes shoulder twist `s * twist` with s = +1/-1 "arms turn out".
  Under the IK-proven flips that is antisymmetric. It is project-written code, low weight; treat as its quirk.

## 3. Per-joint conventions

Signs are effector-space, identical for left and right after section 2.

### Spine 6-9 (pelvis->Spine0 ... Spine2->Spine3) and neck 10 (Spine3->Neck), head 11 (Neck->Head)
Author: `twist_axis = (0,0,1)` up, `lean_axis = (0,1,0)` forward, no flips. Then y = left.

| angle | meaning | evidence |
|---|---|---|
| lean1 + | bend/nod **forward** (flexion) | foetal spine 0.5, neck 0.5 (nmbf.rs:82-85); roll-up (nmru.rs:147-152); catch fall arches back with `-1.0` on spine 2,3 when hands are down in front (nmcf.rs:322-325); head look `lean1` sign `-(u1 . c)` with c = back (nmhl.rs:115-116) [PROVEN for neck given part axes, INFERRED hi for spine] |
| lean2 + | bend to the character's **left** | head look `lean2` sign `+(u2 . b)`, b = left (nmhl.rs:117-118); flinch leans away from a threat on the right with positive lean2 (nmfl.rs:261-264, 313-316) [INFERRED hi] |
| twist + | turn to the **left** (counter-clockwise from above) | head look `twist` sign `-(n2 . b)` (nmhl.rs:113-114); spine twist `atan2(pelvis.b . n, -pelvis.c . n)` (nmst.rs:56-58); bodyBalance twists by left-hip minus right-hip flexion (nmbb.rs:240-244) [INFERRED hi] |

All three neck signs agree with one frame (z up, x forward) and no flips, which is a strong cross-check.
Zero pose: upright neutral standing spine and neck [INFERRED hi]: neutral is commanded as 0 everywhere
(nmbb.rs:228-230, nmhf.rs:270, nmshot.rs:1125) and the balancer takes standing pelvis height from the asset pose
(nmdbm.rs:1159-1162).

Limit constraints **[PROVEN]**: neck and head need `lo < 0 < hi` on all three axes (head look shares an angle by
`lo/(lo_n+lo_h)` and `hi/(hi_n+hi_h)`, nmhl.rs:41-44, 127-131); spine twist needs `lo < 0 < hi` with non-zero sums
(nmst.rs:35-42, 67-70); spine 2 and 3 twist limits are also used as clamps (nmhl.rs:122-125).
Suggested ranges [INFERRED low, radians]: each spine joint lean1 (-0.25, +0.45), lean2 (-0.25, +0.25), twist
(-0.3, +0.3); lower neck and head each lean1 (-0.4, +0.4), lean2 (-0.3, +0.3), twist (-0.6, +0.6). Basis: literals
written per joint (0.25 nmbb.rs:236; 0.5 nmbf.rs:83; 1.0 and -1.0 rely on clamping, nmhf.rs:386-388, nmcf.rs:324),
spine twist allows 1.35x the range (nmst.rs:37), neck total twist cap is `(hi_n+hi_h)*1.2` (nmhl.rs:99).
`spine_lean(l1,l2)` spreads l1 as 2/6, 2/6, 1/6, 1/6 and l2 as 0.5, 0.5, 0.25, 0.25 (nmshot.rs:296-302).

### Clavicles 12 (left), 16 (right)
Author left: `twist_axis` = along the clavicle toward the shoulder joint (about (-1,0,0)), `lean_axis = (0,1,0)`.
Right: X negated, flip [F,T,T]. Then y = down on both sides in effector terms.

- lean1 + = shoulder **forward** (protraction): spine twist to the left drives the right clavicle `+x`, left `-x`
  (nmst.rs:71-74); reach for a low wound uses the upper limit (nmshot.rs:1022-1025) [INFERRED hi].
- lean2 + = shoulder **down**, lean2 - = **shrug up**: wound on pelvis/low spine uses `+0.5*hi`, a higher wound uses
  `0.6*lo` (nmshot.rs:1023-1029); flinch hunches with -0.5 (nmfl.rs:310) [INFERRED hi].
- twist: only literal is +0.3 in catch fall (nmcf.rs:333) [meaning unknown].
- Limits **[PROVEN]**: lean1 and lean2 need `lo < 0 < hi` (ratios `cl/sl` nmcf.rs:347-348; sums nmpa.rs:55-58).
  Suggested [low]: lean1 (-0.35, +0.45), lean2 (-0.5, +0.2), twist (-0.3, +0.3). Literals far outside these
  (-1.455 at nmfow.rs:183) are meant to saturate.

### Shoulders 13 (left), 17 (right)
Author left: `twist_axis` = unit vector from shoulder joint to elbow joint, `lean_axis = (0,1,0)` forward.
Right: X negated, flip [F,T,T]. `y = twist x lean` then lies in the frontal plane, pointing "arm lowers".

- **[PROVEN]** the twist axis must point from the shoulder joint to the elbow joint in the zero pose
  (`predict_knee` places the elbow at `+z * length`, nmdbm.rs:717-724, used for arms at nmshot.rs:1066).
- lean1 + = arm swings **forward** (horizontal adduction / flexion): bodyBalance moves it with the opposite leg's
  swing error (nmbb.rs:281-284); extras "arms' reach forward" is lean1 toward the upper limit
  (extras_fall.rs:31, 408-412); roll-up 1.7, foetal, flinch 1.0 (nmru.rs:155, nmbf.rs:89, nmfl.rs:323) [INFERRED hi].
- lean2 + = arm **lowers toward the body** (adduction), lean2 - = arm **raises** (abduction): fling and
  fall-over-wall sweep lean2 as `k*cos(x)` from about +1 down to -1.43 while the clavicle goes to full shrug
  (nmshot.rs:941-945, nmfow.rs:181-188); bodyBalance "arms out" only ever subtracts from lean2, floor -9.9
  (nmbb.rs:303-317, :55) [INFERRED hi].
- twist - = forearm of a bent elbow rotates **up/outward** (external rotation): every guard pose uses negative
  twist with bent elbows: -0.35 balance, -0.3 foetal, -1.0 roll-up, -1.5 flinch, -0.8 high-fall roll
  (nmbb.rs:285, nmbf.rs:88, nmru.rs:155, nmfl.rs:270/323, nmhf.rs:392) [INFERRED med; depends on elbow axis below].
- `p.shoulder` (1.0) and `p.elbow` (1.75) in bodyBalance are swing **gains** added to the current angle, not target
  angles (nmbb.rs:284-286).
- Limits **[PROVEN]**: lean1, lean2 need `lo < 0 < hi` (same lines as clavicle). Suggested for a 45 degree
  A-pose zero [low]: lean1 (-1.0, +1.8), lean2 (-1.5, +0.85), twist (-1.6, +1.0). The created (standing) pose must
  lie inside, because balance blends the arms back to it (nmbb.rs:322-325).

### Elbows 14 (left), 18 (right), hinges
- **[PROVEN] bent = positive, straight = 0 = zero pose.** Arm IK passes `bend = +1` and sets
  `angle = (pi - interior)*bend + off` (nmdbm.rs:686-687, 703); bodyBalance clamps `>= 0.7` (nmbb.rs:301);
  foetal 2.0, roll-up 1.5+ (nmbf.rs:90, nmru.rs:156). Knees use `bend = -1`.
- The `.min(6.0)` at nmbb.rs:301 is only a generic cap; the real ceiling is `mid + 1.6*half` then the hard limit.
- Axis **[PROVEN relation]**: the wrist code takes `fore x (shoulder - elbow)` of a bent arm as the wrist frame's y
  (nmshot.rs:1068-1073), and that vector equals the positive-flexion axis. So on **both** sides
  `elbow twist_axis = shoulder twist_axis x shoulder lean_axis` (the shoulder frame's raw y). With lean = forward
  this makes flexion carry the hand **forward** [INFERRED hi: it is also the only anatomically neutral choice, see
  hand axes]. Right = minus the mirror of left automatically.
- Limits: suggested (0.0, 2.4..2.6) [INFERRED med]. Windmill clamps to `[lo, hi]` (nmaw.rs:42-43, 94-97); extras use
  `mid - 0.3*half` as a mild bend (extras_fall.rs:221), about 0.85 rad with (0, 2.4).

### Wrists 15 (left), 19 (right)
Author left: `twist_axis` = along the forearm toward the hand, `lean_axis = (0,1,0)` (same frame as the shoulder
when the arm is straight). Right: X negated, flip [F,T,T].

- **[PROVEN relation]** wrist y (twist x lean) = elbow flexion axis; so lean axis = flexion direction
  (nmshot.rs:1068-1076 main branch vs fallback `(w.m.a, w.m.c x w.m.a, w.m.c)`).
- lean2 - = hand bends **back** (extension, palm toward a surface ahead), lean2 + = palm flexion: brace
  `[0.4,-0.4,1.0]`, catch fall `[0.3,-0.5,1.0]`, grab `set_relative(wrist,1,-1.0)`, roll-up `-0.8`
  (nmbr.rs:497, nmcf.rs:339, nmgr.rs:405, nmru.rs:199) [INFERRED hi].
- lean1 = bend in the elbow's flexion plane: pointing sets `wrist lean1 = -0.5 * elbow` (nmpa.rs:102) [INFERRED hi].
- twist = forearm roll; literal +1.0 while bracing, so hi >= 1.0.
- Suggested limits [low]: lean1 (-0.6, +0.6), lean2 (-1.2, +1.0), twist (-1.2, +1.2).

## 4. Zero pose of the arms

**Conclusion: arms out to the sides and angled down, about 45 degrees below horizontal (A-pose), elbows straight,
palms facing down-and-in.** Not hanging, and probably not a flat T. [INFERRED med for the angle; hi that it is not
arms-down.]

- Rest targets are lean2 = +0.5: bodyBalance `0.5 + 0.3*hip_lean2` (nmbb.rs:303) and pointArm's "zero pose when not
  pointing" `[0, 0.5, 0]` with elbow 0.5 (nmpa.rs:104-106). +0.5 rad of lowering from a 45 degree A-pose is a natural
  hang; from a T it leaves the arms 29 degrees below horizontal; from arms-down it would be inside the body.
- Windmill circles lean1/lean2 with radius 0.6 about (-0.3, 0) (nmaw.rs:84-87): a cone about the zero direction.
  That is a windmill only if the zero direction points out sideways, not down.
- Fall-over-wall and fling reach lean2 = -1.43 (arms thrown up) and start near +1.0 (arms at the sides).
- The project derives its part frames by snapping the **idle standing clip** to the asset pose within a quarter
  turn (`derive_links`, nmrs.rs:172-181; delirium-room/src/getup.rs:155-164). That only works if every part of the
  real asset pose is within about 45 degrees of standing idle, which rules out horizontal arms.
- Spine, neck, legs: straight upright stand (section 3).
For our own file any droop of 35-55 degrees works if limits are authored round it; use 45.

## 5. Arm IK (`limb_ik` / `leg_ik`, nmdbm.rs:648-715)

- Called with (shoulder, elbow, root = clavicle part, end = **hand part**), nmshot.rs:26-30. The IK end point is the
  hand part's origin, not the wrist joint (nmdbm.rs:678).
- **Every arm call: bend = +1.0; side = +1.0 left, -1.0 right.**

| caller | line | side | yaw |
|---|---|---|---|
| catch fall | nmcf.rs:307-314 | left ? 1 : -1 | `1 - forward` |
| flinch | nmfl.rs:287, 291, 298 | 1.0 / -1.0 | 0.05 or -0.1 |
| brace | nmbr.rs:494-495 | i==0 ? 1 : -1 | 0 or 1 |
| grab | nmgr.rs:392-395 | i==0 ? 1 : -1 | reach, capped |
| high fall | nmhf.rs:314-315 | right -1.0, left 1.0 | 0 |
| point arm | nmpa.rs:79-84 | left 1 / right -1 | `twist` 0.3 |
| roll up | nmru.rs:167, 197 | 1.0 / -1.0 | 0 |
| reach for wound | nmshot.rs:1052-1053 | i==0 ? 1 : -1 | `yaw + 0.1*side` |
| extras | extras_fall.rs:1076, 1161; extras_held.rs:626, 724, 981, 1083, 1166 | `1 - 2*i` | 0 or param |

  Legs use bend = -1.0 (nmdbm.rs:780, nmhf.rs:330-332, nmfow.rs:197, nmpd.rs:137, nmshot.rs:978).
- Frame requirements: shoulder +z from shoulder to elbow **[PROVEN]**; x and y are free for the IK itself (it works
  in the real frames), but flips must be as in section 2 **[PROVEN]**, and x = forward / y = "lowers" is what the
  literal targets assume (section 3). Elbow hinge axis as in section 3.
- Positive yaw is a right-handed turn of the arm about the shoulder-to-hand line on the left, mirrored on the right
  (nmdbm.rs:689-691): elbow swings **outward** for a hand held low in front. Cross-check on legs: balancer yaw is
  `turn - splay`, negative for toes-out (nmdbm.rs:1172-1178).
- Any kink between upper arm and forearm at angle 0 is measured and compensated (`off`, nmdbm.rs:678-680).

## 6. Part axes (`M34 {a,b,c}` = world directions of the part's local x, y, z)

**[PROVEN]** In the zero pose `a, b, c = ours(column 0, 1, 2 of the 3x3)`, i.e. `(frame[0][i], frame[1][i],
frame[2][i])` is local axis i in asset space; `frame[3]` is the position (nmrs.rs:328-332 with `rigid = true`,
:305-308; nmdbm.rs:895-906; same reading at nmrs.rs:205-214). Both stored matrices must be proper rotations
(nm_asset.rs:282-312, 415). With no links loaded (the JSON path, delirium-sdk/src/character.rs:162) the engine's
own part frame equals this frame.

| part | a (local x) | b (local y) | c (local z) | evidence |
|---|---|---|---|---|
| Spine0-3 (7-10) | **up** along the spine | **left** | **back** | head look: `a*len` reaches the head, visible test on `c`, pitch about `b` (nmhl.rs:76-84); balance frame `[a, -b, c]` ~ COM `[up, right, back]` (nmbb.rs:121-129); grab side angle `atan2(local.y, -local.z)` (nmgr.rs:331-336); roll-up `-2c + b*side` (nmru.rs:189); brace uses Spine2 `b` (nmbr.rs:313-317); pedal: Spine0 `a . up < -0.4` = upside down (nmpd.rs:114-122) [PROVEN for 9, 10; hi for 7; assumed for 8] |
| Neck (11) | **right** | **up** | **back** | `lean1 = -(n.c . v)`, `lean2 = -(n.a . v)` lean the head toward v (nmcf.rs:240-245, nmru.rs:161-165) [INFERRED hi] |
| Head (12) | **right** | **up** | **back** | right hand target at `+0.3*head.a`, left at `-0.3` (nmhf.rs:310-315); look-ahead point `d - 5c` (nmshot.rs:1132-1133); stance uses `head.c` (nmdbm.rs:1119); head look frame (side, up, back) (nmhl.rs:100-112) [hi] |
| Hands (16, 20) | **palm axis** | free | free | palm contact point `d - a*side*k` and `a*side` is turned onto the surface normal with side = -1 left, +1 right (nmgr.rs:247, 449-450, 473-479): left palm faces **+a**, right palm faces **-a**. Combined with the wrist code, `a` = the wrist frame's raw y = the elbow flexion axis on both sides [PROVEN relation] |
| Clavicles, upper arms, forearms | free | free | free | only `.m.d` and velocities are read (e.g. nmcf.rs:312, nmbr.rs:493) |

Anatomy check: left palm = +flexion axis and right palm = -flexion axis is exactly a neutral forearm (thumb
forward), which supports the elbow-axis rule.

Worked example, asset space, arm droop t below horizontal (use 45 degrees), s = sin t, c = cos t:
left arm direction `dL = (-c, 0, -s)`, right `dR = (c, 0, -s)`.

| joint | twist_axis | lean_axis | flip |
|---|---|---|---|
| 6-11 spine, neck, head | (0,0,1) | (0,1,0) | F,F,F |
| 12 / 16 clavicle | (-1,0,0) / (1,0,0) (bone direction) | (0,1,0) | F,F,F / F,T,T |
| 13 / 17 shoulder | dL / dR | (0,1,0) | F,F,F / F,T,T |
| 14 / 18 elbow (hinge) | (s,0,-c) / (s,0,c) | unused | none |
| 15 / 19 wrist | dL / dR | (0,1,0) | F,F,F / F,T,T |

Hand part column 0: left (s,0,-c), right (s,0,c). Spine part 3x3 rows: `[0,-1,0],[0,0,-1],[1,0,0]`.
Neck/head rows: `[1,0,0],[0,0,-1],[0,1,0]`. Keep `centred: true` on 3-axis joints (nmrs.rs:283-293).

## 7. Muscle numbers

- `Effector::new` copies `strength`, `damping`, `muscle_stiffness` (nmrs.rs:488-490); `reset` restores them
  (:509-511); behaviours almost always reset and then call `set_stiffness(s, d)` = `strength = s*s`,
  `damping = 2*s*d` (:492-498). So **asset strength is stiffness squared and asset damping is 2 x stiffness x ratio**
  [PROVEN]. Behaviour stiffness runs 5-16, ratio 0.5-1: a default of stiffness 10-12, ratio 1 means
  **strength 100-144, damping 20-24** [INFERRED med].
- The asset values are used directly when nothing overrides: before the first behaviour, wrists after
  `reset` in high-fall landing (nmhf.rs:316-320), `bodyRelax` (`strength*x^2`, `damping*x`, nmrs.rs:500-507,
  nm.rs:540-552), muscle-stiffness scaling (nm.rs:930-938).
- Drive (ragdoll.rs:2445-2481): acceleration `= strength*(target - angle) - damping*rate`, damping floored at 5.0
  (nmrs.rs:424, 734). `muscle_stiffness` only shapes the implicit blend
  `x = (8*damping + strength)*ms*dt/2`, `blend = max(6*dt, x/(x+1))` (nmrs.rs:735-736). Behaviours set 0.5-2
  (10-20 for gripping wrists and planted ankles) and roll-up multiplies the default by 0.75 (nmru.rs:69-71):
  **default about 1.0** [INFERRED med].
- `max_torque = [lean (and hinge), twist]`, in torque units, scaled by character strength and divided by
  `(1 - blend)` (nmrs.rs:743, ragdoll.rs:2446, 2465-2467, 2478). Too low makes a joint limp, too high is harmless.
  No magnitude hint in the code [unknown]; suggest generous: spine 400, neck 80, clavicle 150, shoulder 150,
  elbow 100, wrist 40, twist half of that.
- Other uses of strength: limit overshoot `1 + 20/strength` (nmrs.rs:545); gravity opposition is capped at
  `oppose_gravity * strength * 0.2` (nmdbm.rs:1437).

## 8. Self-collision pairs

- **[PROVEN]** `self_collision` lists the part pairs that **are** tested against each other; unlisted pairs never
  collide (nm.rs:430-434; ragdoll.rs:2837-2843, 2900).
- The code names two subsets it switches off at run time, so it expects them to be present:
  `LEG_PAIRS` (1,4) (1,5) (2,4) (2,5) (2,6) (3,5) (3,6) while the balancer holds, and
  `HAND_PAIRS` (20,16) (20,15) (19,16) while flinch has `hands_off` (nm.rs:391-397, 2165-2171).
- Order inside a pair does not change which pairs collide (`pair_on` uses min/max, nm.rs:395-397); leg pairs are
  normalised low-high, others kept as written, then sorted (nm.rs:403-407). Other expected pairs (arms vs trunk,
  hands vs legs, head vs hands) are not named anywhere [unknown]: add what the shapes need, never adjacent parts.
- Pairs that already overlap on a resized body are dropped at creation (nm.rs:433-434).

## 9. Open points, most important first

1. Arm droop of the zero pose (section 4) and therefore all shoulder limit numbers: inferred, not provable.
2. All limit magnitudes are estimates; only the sign constraints (`lo < 0 < hi`, non-zero width) are proven.
3. Shoulder twist sign and elbow axis rest on the wrist/palm relation plus anatomy, not on a direct test.
4. Clavicle flips have no IK proof, only symmetric literals.
5. Asset facing +Y is proven through the non-rigid `block()` path only; the pelvis has special quarter-turn
   handling (nmrs.rs:48-66, nmdbm.rs:67-70, 977) that this document does not cover.
6. Unknown table slots that set real poses: 231 (foetal shoulder lean1), 124/493 (flinch shoulder lean1),
   222 (windmill minimum elbow), 522 (spine twist limit factor), 506/507 (fall-over-wall elbows), 494-497.
7. `max_torque` magnitudes and the full self-collision list.
