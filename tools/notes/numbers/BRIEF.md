# Working out Delirium's missing numbers

Delirium Physics (GPL-3 Rust source in `E:\AI\claude\assets\delirium\DeliriumNoGame`) is a port of the Euphoria
active-ragdoll engine. In its public source almost every numeric literal has been replaced by a lookup `kv!(N)`
into a table of 1,096 slots, and the released program fills that table from the user's own GTAIV.exe. The user has
no GTA IV, so we are writing our own table so the program can run without it. For each slot on your sheet, work out
the most plausible value from how the code uses it.

## How the table works
- One slot is one distinct number. The same slot is used everywhere that number occurs, in quite unrelated places
  (a body-part index, a default stiffness, a wall's width...). So ONE value has to make sense in ALL of a slot's uses.
  Two different slots of the same kind have different values.
- Kinds: `decimal` (an f32), `double` (f64), `whole` (an integer). `kv!(N)` is read as f32; `kv!(N int)`,
  `kv!(N usize)` and so on as a whole number. A few slots are read both ways. "negated" only describes storage:
  give the value as the code uses it.
- The source keeps these literals as they are, so NO slot has these values: decimals 0.0, 0.5, 1.0, 2.0 and whole
  numbers 0, 1, 2. Anything else (0.1, 3.0, 10.0, 0.25, 3, 4, 100...) is a slot.
- `sheet_known.txt` lists the 390 slots whose value is already known (columns: slot, whole value, f32 value, uses).
  Whole-number slots there are body part and joint indices, flags and so on. A slot on your sheet does not repeat
  the value of a known slot of the same kind.
- `python -I ctx.py N [M ...]` (in this folder) prints every use of any slot, known or not. Use it for neighbours.

## Anchors already established (decimals)
5 = 3.0, 9 = 0.3, 10 = 0.45, 12 = 1.5, 13 = 1.75, 17 = 0.25, 21 = 12.0, 31 = 10.0, 60 = 0.2, 63 = 80.0,
74 = 0.7, 78 = 0.1, 79 = 50.0, 136 = 1.2, 137 = 9.0, 179 = 1.4, 192 = 1.9, 193 = 0.125,
491 = 1.6, 586 = 1.72, 588 = 1.63, 584 = 55.0, 585 = 77.0, 46 = 110.0, 569 = 64.0, 587 = 125.0, 589 = 88.0.
How: bodyBalance defaults damping 0.7 / bodyStiffness 9 / elbowAngleOnContact 1.9, angVelThreshold (1.2, 3, 1.2);
setStiffness 12; headLook stiffness 10; leanInDirection 0.2; bodyRelax 50; stayUpright 3; fallOverWall magOfForce
0.3 and maxDistanceFromPelToHitPoint 0.25; a running average `(x * kv!(137) + v) * kv!(78)`; and two tables the
docs spell out: the Brawler body "0.45, 0.7, 1, 1.4, 1.5, 1, 80" (ragdoll.rs BRAWLER_BODY) and the body presets
"small 1.60 m / 55 kg, medium 1.75 / 77, large 1.90 / 110, lanky 1.90 / 64, fat 1.72 / 125, stocky 1.63 / 88"
(ragdoll.rs PROFILES: name, height, kg, a third factor). Note what that shows: a value from the docs pinned
kv!(13) = 1.75, which is also bodyBalance's default `elbow`, so this game's defaults are NOT always the ones later
games document. Trust cross-checks between a slot's own uses over remembered defaults. If your evidence
contradicts an anchor, say so in your final message.

## Evidence to use
- Named Euphoria / NaturalMotion message parameters and their documented defaults (the GTA IV, GTA V and RDR
  message lists; the `brace...`, `shot...`, `balance...`, `hf...` names are GTA IV taskparams). Use what you know.
  Careful: the "extras" behaviours (extras*.rs) were written by this project and their defaults need not match
  later games.
- The project's own prose, which states some real values: `docs/modding.md`, `docs/how-it-works.md`,
  `crates/delirium-sdk/include/delirium_physics.h`, `CHANGELOG.md`, binding READMEs and doc comments in the code.
- Physical sense: metres, kilograms, seconds, radians, Z up; gravity 9.81; pi and its fractions; degree/radian
  factors; 1/60 and 1/30 steps; small epsilons; "infinite" sentinels.
- Structure: running averages whose weights sum to 1, clamp(lo, hi) ordering, ascending tables, powers of two for
  flags, consecutive enum values, loop bounds and array sizes that must not go out of range.
- Read the surrounding code in the source file whenever the one line is not enough. Sheet paths are relative to
  `E:\AI\claude\assets\delirium\DeliriumNoGame\crates\`.

## Rules
- Do not edit anything under DeliriumNoGame and do not run cargo there (a build is running).
- Do not download anything and do not look for GTA IV files or copies of its numbers online. Reasoning, the
  repository and general knowledge only.
- Give every slot on your sheet a value. If it really cannot be told, give a best guess that keeps the code safe
  (sensible magnitude, no division by zero, no out-of-range index) and mark it low.

## Output
Write `numbers/part_K.tsv` (K = your sheet number), one line per slot, tab separated:
`slot <TAB> value <TAB> high|medium|low <TAB> one-line reason`
Whole numbers as plain integers (hex allowed as 0x...), decimals as decimals.
Your final message: how many high / medium / low, any anchors you think are wrong, and any slots OUTSIDE your
sheet whose value you became confident of along the way (slot = value, why).
