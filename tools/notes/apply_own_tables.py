# One-off: the other stand-ins that were missing with no game: more weapons, per-weapon shot settings, surface names
# with their own friction, and a plain punch for the Hero.
import io
def rd(p): return io.open(p, encoding="utf-8", newline="").read()
def wr(p, t): io.open(p, "w", encoding="utf-8", newline="").write(t)
def sub(t, a, b, n=1):
    if a not in t: a = a.replace("\n", "\r\n")
    assert t.count(a) == n, (t.count(a), a[:80])
    return t.replace(a, b)

p = "crates/delirium-room/src/main.rs"; t = rd(p)
if "own_melee" not in t:
    t = sub(t, '''         gun("SHOTGUN", "SHOTGUN", "SHOTGUN", 90.0, 5.0, 1200.0, 8, 0.1, 35.0)]''',
'''         gun("SHOTGUN", "SHOTGUN", "SHOTGUN", 90.0, 5.0, 1200.0, 8, 0.1, 35.0),
         // The rest are OUR OWN guesses, scaled against the SDK's four above (not the game's numbers): a heavy pistol
         // between the pistol and the rifle, a sniper rifle above the rifle, and what is swung or thrown.
         gun("DEAGLE", "HANDGUN", "PISTOL_LARGE", 40.0, 40.0, 350.0, 9, 0.5, 60.0),
         Weapon { accuracy_fps: 0.0, ..gun("SNIPERRIFLE", "SNIPER", "SNIPER", 70.0, 100.0, 400.0, 5, 0.0, 150.0) },
         Weapon { fire: "PROJECTILE".into(), damage_type: "EXPLOSIVE".into(), ..gun("RLAUNCHER", "HEAVY", "HEAVY", 50.0, 100.0, 1000.0, 1, 0.0, 100.0) },
         own_melee("UNARMED", &[], 30.0, 10.0),
         own_melee("BASEBALLBAT", &["MELEE_CLUB"], 60.0, 25.0),
         own_melee("KNIFE", &["MELEE_BLADE"], 25.0, 35.0),
         own_thrown("GRENADE", "EXPLOSIVE", 100.0),
         own_thrown("MOLOTOV", "FIRE", 20.0)]''')
    t = sub(t, '''pub static DECISIONS: std::sync::OnceLock<delirium_data::decision::Store>''',
'''/// MODIFIED (not in the original): a stand-in for something swung (see own_weapons).
fn own_melee(name: &str, flags: &[&str], force: f32, damage: f32) -> Weapon {
    Weapon { name: name.into(), fire: "MELEE".into(), slot: "MELEE".into(), group: "MELEE".into(), damage_type: "MELEE".into(),
             flags: flags.iter().map(|f| f.to_string()).collect(), force, damage, damage_fps: damage, between_shots: 600.0, clip: 1, ..Default::default() }
}
/// MODIFIED (not in the original): a stand-in for something thrown; its throw speed and fuse stay the room's own.
fn own_thrown(name: &str, kind: &str, damage: f32) -> Weapon {
    Weapon { name: name.into(), fire: "PROJECTILE".into(), slot: "THROWN".into(), group: "THROWN".into(), damage_type: kind.into(),
             flags: vec!["THROWN".into()], force: 50.0, damage, damage_fps: damage, between_shots: 1000.0, clip: 1, ..Default::default() }
}
pub static DECISIONS: std::sync::OnceLock<delirium_data::decision::Store>''')
    # surfaces: names and our own friction
    t = sub(t, '''    }).unwrap_or_else(|| ["DEFAULT", "BRICK_WALL", "CONCRETE"].iter().map(|n| (n.to_string(), 1.0, 0.1)).collect());''',
'''    }).unwrap_or_else(|| {
        // OUR OWN friction guesses (bounce 0.1 everywhere, the engine's fallback): wood a little slippier than stone, metal more.
        let own = [("DEFAULT", 1.0), ("BRICK_WALL", 1.0), ("CONCRETE", 1.0), ("WOOD", 0.8), ("METAL", 0.6)];
        *delirium::ragdoll::SURFACES.write().unwrap() = own.iter().map(|s| [s.1, 0.1]).collect();
        own.iter().map(|s| (s.0.to_string(), s.1, 0.1)).collect()
    });''')
    t = sub(t, "and the engine's own table is left empty.", "(1.0, 0.1) for stone; see below.")
    wr(p, t)

p = "crates/delirium-room/src/hero.rs"; t = rd(p)
if "own_punch" not in t:
    t = sub(t, "pub struct Hero {\n    pub feet: Vec3,", "pub struct Hero {\n    /// MODIFIED (not in the original): how far into the stand-in punch he is (no fight data).\n    own_punch: Option<f32>,\n    pub feet: Vec3,")
    t = sub(t, "let mut n = Hero { feet, yaw:", "let mut n = Hero { own_punch: None, feet, yaw:")
    t = sub(t, '''        let playing = self.fight.mv.as_ref().and_then(|m| Some((clips.fight_clip(m.key.as_deref()?)?.0, m.phase())));
        if let Some((c, phase)) = playing {''',
'''        let playing = self.fight.mv.as_ref().and_then(|m| Some((clips.fight_clip(m.key.as_deref()?)?.0, m.phase())));
        // MODIFIED (not in the original): with no fight data the attack button plays the stand-in punch; it lands
        // on Homer when he is within arm's reach as the arm comes out.
        let mut own = None;
        if let (None, Some(c)) = (fight.as_deref(), clips.own_punch()) {
            let bits = std::mem::take(&mut self.press) | self.keys | self.scripted;
            if bits & melee::ATTACK_BIT() != 0 && self.own_punch.is_none() {
                self.own_punch = Some(0.0);
            }
            if let Some(t) = self.own_punch {
                let (d, to) = (clips.duration(c), t + dt);
                if t < 0.24 && to >= 0.24 && homer.is_some_and(|(f, ..)| (f - self.feet).with_z(0.0).length() < 1.3) {
                    hit = Some(Hit::Swing(10.0, self.fist.0, self.facing() * MELEE_PUSH));
                }
                self.own_punch = (to < d).then_some(to);
                own = Some((c, (to / d).min(1.0)));
            }
        }
        if let Some((c, phase)) = own {
            (self.clip, self.phase, self.vel) = (c, phase, Vec3::ZERO);
        } else if let Some((c, phase)) = playing {''')
    wr(p, t)

p = "crates/delirium-room/src/taskparams-own.txt"; t = rd(p)
if "NMShot_Standing" not in t:
    t += '''
; How a shot plays out by weapon. OUR OWN guesses, set around the engine's fallbacks (stiffness 10.5, lean 0.3,
; 6 steps, looseness 1): the harder the weapon hits, the looser he goes, the further he leans and the fewer steps
; he manages. The plain set (*) is left to the engine's fallbacks.
NMShot_Standing POWERFUL_WEAPON {
	shotBodyStiffness 9.5
	shotLeanAmount 0.4
	shotMaxSteps 5
}
NMShot_Standing SNIPER_RIFLE {
	shotBodyStiffness 8.5
	shotLeanAmount 0.55
	shotMaxSteps 3
	shotLooseness 1
}
NMShot_Standing SHOTGUN {
	shotBodyStiffness 8.5
	shotLeanAmount 0.6
	shotMaxSteps 3
	shotLooseness 1
}
NMShot_Standing WEAK {
	shotBodyStiffness 9
	shotLeanAmount 0.4
	shotMaxSteps 4
}
NMShot_Standing WEAK_POWERFUL_WEAPON {
	shotBodyStiffness 8.5
	shotLeanAmount 0.5
	shotMaxSteps 3
}
NMShot_Standing WEAK_SNIPER_RIFLE {
	shotBodyStiffness 8
	shotLeanAmount 0.65
	shotMaxSteps 2
}
NMShot_Standing WEAK_SHOTGUN {
	shotBodyStiffness 8
	shotLeanAmount 0.7
	shotMaxSteps 2
}
NMShot_Standing MELEE {
	shotBodyStiffness 10.5
	shotLeanAmount 0.25
	shotMaxSteps 6
}
NMShot_Standing MELEE_BASEBALL {
	shotBodyStiffness 9.5
	shotLeanAmount 0.45
	shotMaxSteps 4
}
'''.replace("\n", "\r\n" if "\r\n" in t else "\n")
    wr(p, t)
print("done")
