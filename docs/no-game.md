# Running Delirium with no game files (this modified copy)

This folder is a **modified copy** of Delirium Physics 0.7.0 (GPL-3.0-only, source from
github.com/PVCPC/delirium-physics, commit 41db26f). The change: the Playroom starts **with no game assets**.
Everything else is Delirium's own: its engine, its Playroom, its stage, taxi, textures, sky, sounds and panels.

Start it with `Play Delirium (no game).bat`.

## What the original takes from the game, and what stands in for it here

| The original reads | From | Here |
|---|---|---|
| 706 numbers (the source says `kv!(13)` where a number goes) | the game's program file | `crates/delirium-data/src/kv-own.txt` |
| The character: joint axes, limits, muscle strengths, part frames, masses | `fred.xrt` | `crates/delirium-room/src/homer-own.json` |
| The body's shapes and standing pose | the game's ped model and idle clip | the same file's `build` section |
| Weapons (push, damage, clip, rate) | `weaponinfo.xml` | the four weapons the SDK ships as its defaults (pistol, SMG, rifle, shotgun); the rest hit with a flat 50 N s |
| Settings for the shot, flinch, blast, fire and vehicle tasks | `taskparams.txt` | the code's own fallbacks where it has them; `crates/delirium-room/src/taskparams-own.txt` for the sets it has none for |
| Get-up, walk and gun clips, surface materials | the game's archives | plain stand-ins made in the code; fight moves are still missing |

**None of these stand-ins are the game's data.** No game file was read to make them. They were worked out from
Delirium's own source, docs, maps and pictures:

- **Numbers.** Each slot is used in many places, so one value has to fit them all. Sources, surest first:
  the source's own parameter docs (`doc: "... (0.3)"` beside `p.f("name", kv!(24))`), the project's docs
  (body presets, the Brawler body), constants left as literals elsewhere, standard algorithms (the random number
  generator, Bullet's 42-direction table, maths helpers), flag and id sequences, physics (gravity, 1/60 s), and
  the two map files' own structure:
  - two slots read from one place hold one number;
  - one stretch of the PC program is a list of decimals sorted by value, which brackets every slot in it;
  - the PC program stores each decimal once, so two slots at different places hold different numbers
    (`python tools/notes/dups.py` lists the ones that still break this: all are guesses that need another look);
  - a few slots the PC map reads from the program are written out in the disc map.
  What is left is a guess that keeps the code sensible. Every line of `kv-own.txt` says how sure it is and why:
  170 pinned, 107 high, 83 medium, 189 low; 157 slots that only matter when a game file is parsed are left at 0.
- **Character.** Measured from Delirium's own pictures of the real Homer (`docs/playroom.png`, which draws his
  skeleton, and `docs/homer-wave.gif`, which shows every part's shape): joint positions, part sizes, foot and hand
  boxes, how the arms hang. Laid out to the conventions the engine's code assumes (which way each part's axes
  point, what each joint angle means and its sign, which side is mirrored, the zero pose), which are proven from
  the code. The masses, joint limits and muscle strengths are NOT visible in any picture and are estimates.
  `tools/make_character.py` writes the file; change the body there.

## So how close is it?

It is the real Delirium code running, on a body that matches the real one's outline to about a centimetre.
Checked beside Delirium's own demo clips, filmed from the same side (`python tools/versus.py`):

- **Matches in kind:** standing height and feet resting about 1 cm in the floor, drunk, stagger (hunches and holds,
  but less deeply than the real one), electrocute (a standing tremor), being thrown by a blast (about 10 m/s up
  from a blast at his feet, as the real RPG clip shows), arms windmill with the slab pushing from behind (same
  rhythm, then he walks upright ahead of the slab; ours swings its arms about 15 degrees lower at the peaks),
  flinch, and ice.
- **What the flinch and ice clips really show** (worked out by reading the real frames one by one):
  - FLINCH is two shots that miss him (the tracer lines are in the clip): one past his chest, which makes him guard
    with his arms, then one past the back of his head, which makes him duck with his hands over his head. He never
    turns round. Ours does the same when shot at the same way (`!gun 0.3,0.1,0.0` then `!gun 0.25,0.25,0.35`); it
    bends forward less. The Flinch button alone (a threat straight ahead) only raises the arms, in both.
  - ICE: the ice floor works (a nudged Homer slides to a stop at the 0.05 friction the room sets), but ice alone
    leaves him standing still. The real clip shows him step first, then slip and fall on his front. Ice + Drunk does
    exactly that here. What the authors pressed is not known: this trigger is a guess.
- **The authors' own pass/fail checks hold:** he stands; a 60 N s push at the chest does not floor him; a 200 N s
  push does; a fatal head shot leaves him limp; a pistol shot takes health (25 at the chest by the SDK's table; a hit on the arm took 18.8).
- **Cannot match without the game:** how each weapon's shot plays out, because those settings are in
  `taskparams.txt`; anything that plays a game clip.
- **Not looked at:** grab, climb, the taxi, stages other than the default one, Hero mode.

It is **not** exactly the real thing and cannot be shown to be: about 270 numbers are medium or low confidence,
and the masses, joint limits and muscle strengths are estimates.

To get the real thing, point Delirium at your own copy of the game as the original's README says (`--game <folder>`): this copy still
does that, and then uses the game's numbers, character, weapons and settings instead of the stand-ins.

## How he and the room look

The pictures to go by are Delirium's own: `docs/playroom.png` and `docs/homer-wave.gif` (see-through body, grey
sky, black shadows) and the demo clips such as `docs/moves.gif` (solid body, dark "void" look, soft light).

- **Trunk.** The solid body of the clips shows what the see-through pictures hide: under the chest there are four
  even rolls of one width (Spine2, Spine1, Spine0, pelvis), the sides nearly straight, and the shoulders are small
  round caps mostly inside the chest. The trunk in `tools/make_character.py` is laid out to that. (The first fit, from
  the see-through pictures alone, had a pot belly under a narrow waist: the joints were right, the outline was not.)
- **Wall colour.** The room paints blocks whose surface is called BRICK_WALL orange. The names come from the game's
  materials file, so with no game the back wall was grey. This copy gives the room the three names it asks for
  (DEFAULT, BRICK_WALL, CONCRETE) with the same friction and bounce as before (1.0, 0.1).
- **Light.** With no game this copy starts with the plain grey sky and the hard sun (black shadows) of the docs
  pictures, where the original starts with its drawn sky and soft fill light. Both are ordinary settings
  (Graphics / Camera), and saved settings win. The demo clips were made with the soft light on.
- **Still different:** the real blue is greyer in the see-through pictures; the real one stands with knees a little
  bent and feet apart when balancing, ours stands straighter.

## What stands in for the game's clips, weapons and surfaces

All of these are OUR OWN, plain stand-ins. None is the game's data, and none was checked against the real thing
(there is no picture of it in the repo to check against).

- **Get-up, idle, walk, run, sprint, gun and punch clips** (`Clips::own` at the end of
  `crates/delirium-room/src/getup.rs`). The original reads them from the game's archives. Here each is a handful of
  hand-written key poses (how far each joint is bent), turned into a clip on a skeleton made from the stand-in body.
  The get-ups run a smooth curve through their key poses with the right foot planted, and are uneven on purpose (from the front: up on the hands, onto hands and knees, left foot forward, push off the knee; from the back: sit up propped on one hand, tuck the feet, rock forward, stand). So: knocked down, Homer lies still 2 s and then gets up from his front or his back and balances again; Hero mode
  has a body that stands, walks, runs and sprints, holds a gun out, and throws a plain right punch that pushes
  Homer when he is within arm's reach. The Hero's speeds (1.4, 3.6 and 6 m/s) are our choice.
- **Get-ups from Kimodo.** The two get-up clips now come from a motion made with NVIDIA's
  Kimodo (github.com/nv-tlabs/kimodo, a text-to-motion model; code Apache-2.0, model under the NVIDIA Open Model
  License), installed beside this folder at `E:\AI\claude\assets\kimodo` (its own `.venv`, PyTorch with CUDA, its C++
  helper built with Visual Studio's 14.29 tools). `python tools/kimodo_getups.py` generates front and back get-ups and
  converts them (`tools/kimodo_to_clip.py`) to text clips; `DELIRIUM_GETUP_FRONT=<file>` / `DELIRIUM_GETUP_BACK=<file>`
  try one without rebuilding; copying one over `crates/delirium-room/src/getup-front-kimodo.txt` (or `-back-`) and
  rebuilding keeps it. Empty files fall back to the key poses. In use now: sample 3 of each prompt at seed 1, trimmed of its
  lying-still start (`run/kimodo/front-pick.txt`, `back-pick.txt`; filmed in `run/getup-kimodo.mp4`). Kimodo's text
  model is Meta's Llama 3 (8B): it needs a Hugging Face login that Meta has approved, about 16 GB in the Hugging Face
  cache on C:, and runs on the CPU here (8 GB of video memory is too little). The motions are Kimodo's output, not the
  game's animation; licence terms for using them are NVIDIA's (Open Model License) and Meta's (Llama 3).
  Planting (`OwnRig::recorded`): the converter marks each frame's resting feet (low and still) and hands (low); a
  resting foot holds the whole body in place, and each resting hand or foot is bent onto its own floor spot, stepping
  to a new one past 10 cm (feet) / 15 cm (hands). `--speed` in the converter plays a clip faster (1.15 in use). At the
  start, the pose he lay in fades out of the moving clip over 0.6 s (`OWN_BLEND`). Filmed in `run/getup-planted.mp4`;
  checked on frame sheets only, the remaining slide was not measured.
- **Weapons** (`own_weapons` in the room's `main.rs`). The SDK's four, plus our guesses scaled against them for the
  heavy pistol, sniper rifle, rocket launcher, bat, knife, fists, grenade and fire bottle. The taser and flamethrower
  keep the room's built-in values.
- **How a shot plays out by weapon** (`NMShot_Standing` sets in `taskparams-own.txt`): our guesses around the
  engine's fallbacks; harder-hitting weapons make him looser, lean further and take fewer steps.
- **Surfaces**: five names (DEFAULT, BRICK_WALL, CONCRETE, WOOD, METAL) with our own friction (stone 1.0, wood 0.8,
  metal 0.6). The default room only has stone, so nothing there changed.

## What is still missing without the game

- The game's own animation: the stand-in clips are simple and stiff beside it.
- Fighting moves: blocks, kicks, combos, holds and Homer fighting back all come from the game's fight tables and
  clips. Only the one plain punch is here.
- Swimming clips, and the learned get-up (`getup.net`), which was trained on the real body and numbers.

## Working on it

- `DELIRIUM_NUMBERS=<file>` and `DELIRIUM_CHARACTER=<file>` make the room read another table or character
  without rebuilding.
- `delirium-room --headless 300 > out.txt` then `python tools/heights.py out.txt` prints how high the pelvis,
  chest, head, feet and hands are over time (a quick "is he standing").
- `python tools/film.py <name> "<seconds> <script line>;..." [seconds]` films a scripted scene to
  `run/film/<name>/` and a contact sheet `run/film/<name>.jpg`.
- `python tools/versus.py <name> <folder of real frames> <first> <last> "<seconds> <script line>"` films ours at the
  same frame times as a stretch of one of Delirium's demo GIFs and puts real over ours on one sheet. Film from the
  front (`--cam "-1.57 0.2 3.6 0.9"`): the demo clips are.
- `python tools/versus_video.py` films all six demo moves at EVERY frame time and writes `run/compare.mp4`, real on
  the left and ours on the right. Watch this rather than the sheets: every fourth frame hid the windmill ending.
  The demo's clips are frames 0-37 ice, 38-82 drunk, 83-127 flinch, 128-164 electrocute, 165-209 stagger,
  210-247 windmill; the clips do not say when each move was triggered, so the start times are set by eye.
- `TP=<file>` replaces the stand-in task settings. `!shoot` takes a part NUMBER (chest 10, head 12).
- `tools/notes/`: the reasoning sheets, `pool.py` / `dups.py` / `order.py` (what the maps say about the numbers),
  `apply.py` (apply a sheet of corrections to `kv-own.txt`).

## The SDK (delirium_physics.dll) with no game

The SDK can start with no game too, the same way the room does:

- `nm_unlock_own(numbers)`: opens the number table from our own stand-in numbers (`kv-own.txt`, built in; pass a
  path to read another file, or NULL) and loads the stand-in task settings (`taskparams-own.txt`, built in). Returns
  how many parse-only slots stay empty (0 once a table is open). Call it instead of `nm_unlock`.
- `nm_own_character(buf, len)`: the stand-in character (`homer-own.json`, built in), for `nm_init_character` and
  `nm_build_from_character`. Like the other string getters: call with NULL / 0 for the length.

Build: `cargo build --release -p delirium-sdk --offline` (with `CARGO_HOME` set to the folder's `.cargo-home`); the
DLL is `target/release/delirium_physics.dll`. PhysicsPlayer uses it for its Euphoria mode (engine Delirium).

## What was changed in the source

- `crates/delirium-data/src/kv.rs`: `unlock_own`, `own` (open the table from `kv-own.txt`); new `kv-own.txt`.
- `crates/delirium-room/src/main.rs`: with no game, open our own numbers and load `homer-own.json` instead of
  asking for the game; fall back to the SDK's four default weapons and to `taskparams-own.txt`; new
  `homer-own.json`, `taskparams-own.txt`. Also with no game: the three surface names the room asks for, and the
  plain sky and hard sun as the starting look.
- `crates/delirium-sdk/src/lib.rs`: `nm_unlock_own` and `nm_own_character` (above); the original is beside it as
  `lib.rs.orig`.
- New: `tools/`, this file, `Play Delirium (no game).bat`.

Delirium's licence applies to this copy too (GPL-3.0-only, see LICENSE): if you pass it on, pass the source on
with it and say it is modified.
