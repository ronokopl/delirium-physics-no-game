# Corrections and a strong new source (read after BRIEF.md)

## A source that states values outright
The "extras" behaviours declare their parameters as
`Param { name: "leanHipsMaxF", kind: Kind::Float, used: true, doc: "hip lean going forward, of the joint range (0.3)" }`
and the same file reads them as `p.f("leanHipsMaxF", kv!(24))`. The number in brackets at the end of the doc text IS
the default, so kv!(24) = 0.3. Use this wherever a slot on your sheet is a parameter default (extras.rs,
extras_fall.rs, extras_held.rs and any other file with `Param { ... doc: "... (value)" }`). Doc comments elsewhere
(`///` lines, messages printed with `say(...)`, usage/help text in delirium-room) state values the same way.

## Values pinned this way (decimals; these override the brief)
5 = 3.0, 9 = 0.15 (the brief's 0.3 was WRONG), 11 = 40.0, 12 = 1.5, 17 = 0.25, 19 = 0.95, 20 = 0.8, 21 = 12.0,
24 = 0.3, 25 = 20.0, 27 = 30.0, 28 = 0.9, 30 = 15.0, 31 = 10.0, 32 = 7.0, 35 = 6.0, 60 = 0.2, 64 = 5.0, 65 = 8.0,
68 = 0.05, 74 = 0.7, 78 = 0.1, 84 = 4.0, 112 = 0.07, 116 = 0.4, 117 = 11.0, 119 = 0.6, 123 = pi (doc says 3.14),
126 = 14.0, 136 = 1.2, 138 = 1.1, 140 = 0.35, 141 = 2.25, 142 = 0.18.
Still standing from the brief: 10 = 0.45, 13 = 1.75, 63 = 80.0, 79 = 50.0, 137 = 9.0, 179 = 1.4, 192 = 1.9,
193 = 0.125, 491 = 1.6, 586 = 1.72, 588 = 1.63, 584 = 55.0, 585 = 77.0, 46 = 110.0, 569 = 64.0, 587 = 125.0,
589 = 88.0.

Consequence: later games' documented defaults are a weak guide here (fallOverWall magOfForce is kv!(9) = 0.15,
not 0.3). Prefer what this source says about itself.
