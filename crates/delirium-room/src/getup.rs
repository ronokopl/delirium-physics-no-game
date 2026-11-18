use bevy::prelude::*;
use delirium_data::{anim, img, model, archive_key::ArchiveKey, resource, rpf, skeleton};
use delirium::ragdoll::Build;
use std::io::{Read, Seek, SeekFrom};
use std::path::Path;

pub const DOWN_SECS: f32 = 2.0;
#[allow(non_snake_case)]
#[inline]
fn RISE_BLEND() -> f32 { delirium_data::kv!(17) }
pub const IDLE: usize = 2;
#[allow(non_snake_case)]
#[inline]
pub fn WALK() -> usize { delirium_data::kv!(0 int) }

pub const GUN_CLIPS: [&str; 7] = ["gun@handgun", "gun@deagle", "gun@mp5k", "gun@ak47", "gun@rifle", "gun@shotgun", "gun@rocket"];

#[derive(Clone)]
pub struct Clips {
    parents: Vec<Option<usize>>,
    bind: Vec<(Vec3, Quat)>,
    clips: Vec<(anim::Animation, Vec<Option<usize>>)>,
    pub hero: Option<std::rc::Rc<delirium::ragdoll::Rig>>,
    pub guns: Vec<Option<(usize, usize)>>,
    names: Vec<String>,
    ids: Vec<u16>,
    pub fight: Option<(std::rc::Rc<crate::melee::Data>, std::collections::HashMap<String, usize>)>,
    fight_from: usize,
    pub swim: Option<usize>,
    parts: Vec<(usize, Transform)>,
    chest: usize,
    pub(crate) scale: (Vec<f32>, Vec<f32>),
    /// MODIFIED (not in the original): for the stand-in clips, how far each part reaches below its centre lying down.
    own_low: Vec<f32>,
}

pub struct Rise {
    clip: usize,
    hold: bool,
    pub t: f32,
    body: Transform,
    lay: Vec<Transform>,
}

const PS3_KEYS_SRC: &str = "https://raw.githubusercontent.com/RPCS3/rpcs3/b8ca6d953f734900c23f2cfbe79a36e598171553/rpcs3/Crypto/key_vault.cpp";

fn ps3_keys() -> Result<Vec<delirium_data::sce::AppKey>, String> {
    let f = config_dir().join("ps3keys.txt");
    let fail = "couldn't get the keys that open EBOOT.BIN (they're fetched from the internet the first time: check the connection)";
    let src = match std::fs::read_to_string(&f) {
        Ok(s) => s,
        Err(_) => {
            let out = std::process::Command::new("curl").args(["-sSfL", PS3_KEYS_SRC]).output().map_err(|_| fail)?;
            let s = String::from_utf8_lossy(&out.stdout).into_owned();
            let _ = std::fs::create_dir_all(config_dir()).and_then(|_| std::fs::write(&f, &s));
            s
        }
    };
    Some(delirium_data::sce::app_keys(&src)).filter(|k| !k.is_empty()).ok_or(fail.into())
}

fn ps3_program(dir: &Path) -> Result<Vec<u8>, String> {
    if let Ok(d) = std::fs::read(dir.join("eboot.elf")) {
        return Ok(d);
    }
    let raw = std::fs::read(dir.join("EBOOT.BIN")).map_err(|e| format!("EBOOT.BIN: {e}"))?;
    let elf = delirium_data::sce::decrypt(&raw, &ps3_keys()?).map_err(|e| format!("EBOOT.BIN: {e}"))?;
    let _ = std::fs::write(dir.join("eboot.elf"), &elf);
    Ok(elf)
}

pub use delirium_data::xex::{config_dir, fetched_key as xex_key};

static PS3: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);
static PC: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);

pub fn pc() -> bool {
    PC.load(std::sync::atomic::Ordering::Relaxed)
}

pub fn plat(s: &str) -> String {
    let to = if pc() {
        [("xbox360", "pc"), (".xrt", ".art"), (".xft", ".wft"), (".xad", ".wad"), (".xtd", ".wtd"), (".xdr", ".wdr")]
    } else if PS3.load(std::sync::atomic::Ordering::Relaxed) {
        [("xbox360", "ps3"), (".xrt", ".prt"), (".xft", ".cft"), (".xad", ".cad"), (".xtd", ".ctd"), (".xdr", ".cdr")]
    } else {
        return s.into();
    };
    to.iter().fold(s.into(), |s, (a, b)| s.replace(a, b))
}

pub fn key(dir: &Path) -> Result<ArchiveKey, String> {
    static KEY: std::sync::OnceLock<Result<[u8; 32], String>> = std::sync::OnceLock::new();
    PS3.store(dir.join("ps3.rpf").is_file(), std::sync::atomic::Ordering::Relaxed);
    PC.store(dir.join("GTAIV.exe").is_file(), std::sync::atomic::Ordering::Relaxed);
    delirium_data::LE.store(pc(), std::sync::atomic::Ordering::Relaxed);
    let k = KEY.get_or_init(|| {
        if pc() {
            let exe = std::fs::read(dir.join("GTAIV.exe")).map_err(|e| format!("GTAIV.exe: {e}"))?;
            let mut head = vec![0; 0x810];
            let rpf = dir.join("pc/models/cdimages/playerped.rpf");
            std::fs::File::open(rpf).and_then(|mut f| f.read_exact(&mut head)).map_err(|e| format!("playerped.rpf: {e}"))?;
            return ArchiveKey::find_by_trial(&exe, &head).map(|(_, k)| k).ok_or_else(|| "no archive key in GTAIV.exe".into());
        }
        if dir.join("ps3.rpf").is_file() {
            let elf = ps3_program(dir)?;
            let mut head = vec![0; 0x810];
            std::fs::File::open(dir.join("ps3.rpf")).and_then(|mut f| f.read_exact(&mut head)).map_err(|e| format!("ps3.rpf: {e}"))?;
            return ArchiveKey::find_by_trial(&elf, &head).map(|(_, k)| k).ok_or_else(|| "no archive key in eboot.elf".into());
        }
        let xex = std::fs::read(dir.join("default.xex")).map_err(|e| format!("default.xex: {e}"))?;
        let xex = delirium_data::xex::XexImage::parse_with_key(&xex, &xex_key()?).map_err(|e| format!("default.xex: {e}"))?;
        let mut head = vec![0; 0x810];
        std::fs::File::open(dir.join("xbox360.rpf")).and_then(|mut f| f.read_exact(&mut head)).map_err(|e| format!("xbox360.rpf: {e}"))?;
        ArchiveKey::find_by_trial(&xex.image, &head).map(|(_, k)| k).ok_or_else(|| "no archive key in default.xex".into())
    });
    k.clone().map(|k| ArchiveKey::from_bytes(&k))
}

fn img_open(path: &Path, key: &ArchiveKey) -> Result<(Vec<img::Entry>, std::fs::File), String> {
    let path = &std::path::PathBuf::from(plat(&path.to_string_lossy()));
    let name = path.file_name().map_or(String::new(), |n| n.to_string_lossy().into_owned());
    let mut f = std::fs::File::open(path).map_err(|e| format!("{name}: {e}"))?;
    let mut head = vec![];
    (&mut f).take(delirium_data::kv!(1 int) << delirium_data::kv!(127 int)).read_to_end(&mut head).map_err(|e| e.to_string())?;
    Ok((img::read_table(&head, Some(key))?, f))
}

pub fn vehicle_xft(game: &str, name: &str) -> Result<resource::Resource, String> {
    let dir = Path::new(game);
    let (table, mut f) = img_open(&dir.join("xbox360/models/cdimages/vehicles.img"), &key(dir)?)?;
    img_read(&table, &mut f, &format!("{name}.xft"))
}

fn img_read(table: &[img::Entry], f: &mut std::fs::File, name: &str) -> Result<resource::Resource, String> {
    let name = &plat(name);
    let e = table.iter().find(|e| e.name.eq_ignore_ascii_case(name)).ok_or(format!("{name} not found"))?;
    let mut raw = vec![];
    f.seek(SeekFrom::Start(e.offset)).map_err(|e| e.to_string())?;
    f.take(e.used_blocks as u64 * delirium_data::kv!(722 int)).read_to_end(&mut raw).map_err(|e| e.to_string())?;
    resource::parse(&raw)
}

static LINKS: [std::sync::OnceLock<Vec<Quat>>; 2] = [const { std::sync::OnceLock::new() }; 2];

pub fn links(nm: usize) -> &'static [Quat] {
    LINKS[nm].get().map_or(&[], |l| l.as_slice())
}

pub fn homer(game: &str, model: &str, nm: usize) -> Result<Build, String> {
    let b = homer_links(game, model, nm)?;
    let _ = LINKS[nm].set(b.links.clone());
    Ok(b)
}

fn homer_links(game: &str, model: &str, nm: usize) -> Result<Build, String> {
    let b = homer_build(game, model, nm, LINKS[nm].get().cloned().unwrap_or_else(|| delirium::nmdbm::asset_links(nm)))?;
    if !b.links.is_empty() {
        return Ok(b);
    }
    let clips = Clips::load(game, &b)?;
    let idle: Vec<Quat> = clips.place(&clips.pose(IDLE, 0.0), Transform::from_rotation(Quat::from_rotation_z(-std::f32::consts::FRAC_PI_2))).iter().map(|f| f.rotation).collect();
    match delirium::nmrs::derive_links(&b, &idle) {
        Some(l) => homer_build(game, model, nm, l),
        None => Ok(b),
    }
}

fn homer_build(game: &str, model: &str, nm: usize, links: Vec<Quat>) -> Result<Build, String> {
    let dir = Path::new(game);
    let (table, mut f) = img_open(&dir.join("xbox360/models/cdimages/componentpeds.img"), &key(dir)?)?;
    let frag = img_read(&table, &mut f, &format!("{model}.xft"))?;
    let bones = skeleton::read(&frag, model::fragment_root(&frag)?)?;
    let parts = delirium_data::ragdoll::read(&frag)?;
    let parents: Vec<Option<usize>> = bones.iter().map(|b| b.parent).collect();
    let bind: Vec<(Vec3, Quat)> = bones.iter().map(|b| (Vec3::from(b.translation), Quat::from_array(b.rotation).normalize())).collect();
    delirium::ragdoll::Rig::linked(&parts, &parents, &bind, &bones, nm, links).map(|r| r.build).ok_or(format!("{model}.xft: no ragdoll"))
}

impl Clips {
    pub fn load(game: &str, build: &Build) -> Result<Clips, String> {
        let dir = Path::new(game);
        let rd = |p: &str| std::fs::read(dir.join(p)).map_err(|e| format!("{p}: {e}"));
        let key = key(dir)?;
        let peds = if pc() {
            rd("pc/models/cdimages/playerped.rpf")?
        } else {
            let platform = rd(&plat("xbox360.rpf"))?;
            let toc = rpf::read_toc(&platform, &key)?;
            let nested = toc.iter().find(|e| e.path.eq_ignore_ascii_case("models/cdimages/playerped.rpf")).ok_or("playerped.rpf not found")?;
            rpf::read(&platform, nested)?
        };
        let inner = rpf::read_toc(&peds, &key)?;
        let e = inner.iter().find(|e| e.path.eq_ignore_ascii_case(&plat("player.xft"))).ok_or("player.xft not in playerped.rpf")?;
        let frag = resource::parse(&rpf::read(&peds, e)?)?;
        let bones = skeleton::read(&frag, model::fragment_root(&frag)?)?;
        let (table, mut f) = img_open(&dir.join("xbox360/anim/anim.img"), &key)?;
        let mut clip = |dict: &str, name: &str| -> Result<(anim::Animation, Vec<Option<usize>>), String> {
            let a = anim::read_dictionary(&img_read(&table, &mut f, dict)?)?.into_iter().find(|a| a.name.eq_ignore_ascii_case(name))
                .ok_or(format!("no {name} in {dict}"))?;
            let map = a.tracks.iter().map(|t| bones.iter().position(|b| b.id == t.bone).filter(|&b| b != 0)).collect();
            Ok((a, map))
        };
        let mut clips = vec![clip("get_up.xad", "get_up_fast")?, clip("get_up_back.xad", "get_up_fast")?];
        for c in ["idle", "walk", "run", "sprint"] {
            clips.push(clip("move_player.xad", c)?);
        }
        let mut guns = vec![];
        for d in GUN_CLIPS {
            let pair = clip(&format!("{d}.xad"), "fire").and_then(|f| Ok((f, clip(&format!("{d}.xad"), "reload")?))).ok();
            guns.push(pair.map(|(f, r)| {
                clips.extend([f, r]);
                (clips.len() - 2, clips.len() - 1)
            }));
        }
        let swim = ["idle", "walk", "run", "sprint"].map(|c| clip("swimming.xad", c)).into_iter().collect::<Result<Vec<_>, _>>()
            .map_err(|e| eprintln!("swimming: {e}")).ok().map(|s| {
                clips.extend(s);
                clips.len() - delirium_data::kv!(1 int)
            });
        let mut fight_from = clips.len();
        let fight = (|| -> Result<crate::melee::Data, String> {
            let (c, toc) = if pc() { (vec![], vec![]) } else { let c = rd("common.rpf")?; let t = rpf::read_toc(&c, &key)?; (c, t) };
            let f = |p: &str| if pc() { rd(&format!("common/{p}")) } else {
                toc.iter().find(|e| e.path.eq_ignore_ascii_case(p)).and_then(|e| rpf::read(&c, e).ok()).ok_or(format!("no {p} in common.rpf"))
            };
            match delirium_data::decision::Store::load(|n| f(&format!("data/decision/{n}")).ok().and_then(|b| String::from_utf8(b).ok())) {
                Ok(s) => drop(crate::DECISIONS.set(s)),
                Err(e) => eprintln!("decisions: {e}"),
            }
            Ok(crate::melee::load(&f("data/meleeanims.dat")?, &f("data/action_table.csv")?, &f("data/pedpersonality.dat")?,
                &f("data/animgrp.dat")?, &f("data/ambient.dat")?, (0, &[])))
        })().map_err(|e| eprintln!("fights: {e}")).ok().map(|d| {
            let (mut at, mut dicts) = (std::collections::HashMap::new(), std::collections::HashMap::<String, Vec<anim::Animation>>::new());
            let stance: Vec<String> = (*crate::melee::STANCE_IDS()).iter().filter_map(|&id| d.stance_key(-1, id)).collect();
            let homer = d.ped(crate::HOMER_MODEL).groups;
            let his = d.table.results.iter().filter(|r| homer.contains(&r.anim_group)).filter_map(|r| d.clip(r));
            for (n, k) in stance.iter().cloned().chain(d.clip_keys()).chain(his).enumerate() {
                if n == stance.len() {
                    fight_from = clips.len();
                }
                let Some((dict, name)) = k.split_once('/') else { continue };
                let list = dicts.entry(dict.to_string())
                    .or_insert_with(|| img_read(&table, &mut f, &format!("{dict}.xad")).and_then(|r| anim::read_dictionary(&r)).unwrap_or_default());
                if let (None, Some(a)) = (at.get(&k), list.iter().find(|a| a.name.eq_ignore_ascii_case(name))) {
                    let map = a.tracks.iter().map(|t| bones.iter().position(|b| b.id == t.bone).filter(|&b| b != 0)).collect();
                    clips.push((a.clone(), map));
                    at.insert(k, clips.len() - 1);
                }
            }
            (std::rc::Rc::new(d), at)
        });
        let parts = build.parts.iter().map(|p| bones.iter().position(|b| b.name == p.name).map(|b| (b, p.offset)).ok_or(format!("no bone {}", p.name)))
            .collect::<Result<_, _>>()?;
        let chest = build.parts.iter().position(|d| d.parent == Some(0) && !d.lower).unwrap_or(0);
        Ok(Clips { scale: Default::default(), own_low: vec![],
            parents: bones.iter().map(|b| b.parent).collect(),
            bind: bones.iter().map(|b| (Vec3::from(b.translation), Quat::from_array(b.rotation).normalize())).collect(),
            hero: delirium_data::ragdoll::read(&frag).ok().and_then(|p| {
                let bind: Vec<(Vec3, Quat)> = bones.iter().map(|b| (Vec3::from(b.translation), Quat::from_array(b.rotation).normalize())).collect();
                delirium::ragdoll::Rig::new(&p, &bones.iter().map(|b| b.parent).collect::<Vec<_>>(), &bind, &bones, delirium::nmrs::HOMER)
            }).map(std::rc::Rc::new),
            clips, parts, chest, guns, names: bones.iter().map(|b| b.name.clone()).collect(), ids: bones.iter().map(|b| b.id).collect(), fight, fight_from, swim,
        })
    }

    pub fn pose(&self, c: usize, phase: f32) -> Vec<(Vec3, Quat)> {
        let (a, map) = &self.clips[c];
        let mut bind = self.bind.clone();
        bind[0] = (Vec3::ZERO, Quat::IDENTITY);
        let mut out = delirium::ragdoll::sample(&bind, a, map, phase);
        out[0] = delirium::ragdoll::root(a, phase);
        out
    }

    pub fn play(&self, c: usize, phase: f32) -> Vec<(Vec3, Quat)> {
        if c >= self.fight_from {
            return self.play_fight(c, phase);
        }
        let mut out = self.pose(c, phase);
        let a = &self.clips[c].0;
        let x = phase.clamp(0.0, 1.0) * (a.frames - 1) as f32;
        let (i, f) = (x.floor() as usize, x.fract());
        let q = |v: &[f32]| Quat::from_xyzw(v[0], v[1], v[2], v[delirium_data::kv!(0 int)]).normalize();
        let roots: Vec<&anim::Track> = a.tracks.iter().filter(|t| t.bone == 0).collect();
        let identity = |t: &anim::Track| t.kind == anim::BONE_ROTATION
            && (0..a.frames).all(|k| { let v = t.sample(k); v[0].abs() < delirium_data::kv!(134) && v[1].abs() < delirium_data::kv!(134) && v[2].abs() < delirium_data::kv!(134) });
        out[0] = self.bind[0];
        if !roots.iter().any(|t| identity(t)) {
            for t in roots {
                match t.kind {
                    anim::BONE_ROTATION => out[0].1 = q(&t.sample(i)).slerp(q(&t.sample(i + 1)), f),
                    anim::BONE_TRANSLATION => out[0].0 = Vec3::from_slice(&t.sample(i)).lerp(Vec3::from_slice(&t.sample(i + 1)), f),
                    _ => {}
                }
            }
        }
        out
    }

    fn play_fight(&self, c: usize, phase: f32) -> Vec<(Vec3, Quat)> {
        let mut out = self.pose(c, phase);
        let a = &self.clips[c].0;
        let x = phase.clamp(0.0, 1.0) * (a.frames - 1) as f32;
        let (i, f) = (x.floor() as usize, x.fract());
        let q = |v: &[f32]| Quat::from_xyzw(v[0], v[1], v[2], v[delirium_data::kv!(0 int)]).normalize();
        let (mut at, mut turn) = (Vec3::ZERO, Quat::IDENTITY);
        for t in a.tracks.iter().filter(|t| t.bone == 0) {
            match t.kind {
                anim::BONE_ROTATION => turn = q(&t.sample(i)).slerp(q(&t.sample(i + 1)), f),
                anim::BONE_TRANSLATION => at = Vec3::from_slice(&t.sample(i)).lerp(Vec3::from_slice(&t.sample(i + 1)), f),
                _ => {}
            }
        }
        let start = a.tracks.iter().find(|t| t.kind == anim::MOVER_TRANSLATION).map_or(Vec3::ZERO, |t| Vec3::from_slice(&t.sample(0)));
        let start_turn = a.mover_rotation.as_ref().map_or(Quat::IDENTITY, |t| q(&t.sample(0)));
        let turn = start_turn * turn;
        out[0] = if turn.xyz().length() > delirium_data::kv!(134) { (start + start_turn * at, turn) } else { self.bind[0] };
        out
    }

    pub fn bone(&self, pose: &[(Vec3, Quat)], body: Transform, name: &str) -> Option<(Vec3, Quat)> {
        let i = self.names.iter().position(|n| n == name)?;
        Some(delirium::ragdoll::pose_frames(&self.parents, pose, body)[i])
    }

    pub fn bend(&self, pose: &mut [(Vec3, Quat)], body: Transform, axis: Vec3, angle: f32) {
        let world = delirium::ragdoll::pose_frames(&self.parents, pose, body);
        let q = Quat::from_axis_angle(axis, angle / delirium_data::kv!(5));
        for name in ["Char_Spine1", "Char_Spine2", "Char_Spine3"] {
            let Some(i) = self.names.iter().position(|n| n == name) else { continue };
            let Some(p) = self.parents[i] else { continue };
            let wp = world[p].1;
            pose[i].1 = (wp.inverse() * q * wp * pose[i].1).normalize();
        }
    }

    pub fn point_bone(&self, pose: &mut [(Vec3, Quat)], body: Transform, name: &str, next: &str, dir: Vec3) -> bool {
        let at = |n: &str| self.names.iter().position(|b| b == n);
        let (Some(i), Some(j)) = (at(name), at(next)) else { return false };
        let world = delirium::ragdoll::pose_frames(&self.parents, pose, body);
        let r = Quat::from_rotation_arc((world[j].0 - world[i].0).normalize_or(dir), dir.normalize());
        let parent = self.parents[i].map_or(body.rotation, |p| world[p].1);
        pose[i].1 = (parent.inverse() * r * world[i].1).normalize();
        true
    }

    pub fn names(&self) -> &[String] {
        &self.names
    }

    pub fn points<'n>(&self, parts: impl Iterator<Item = &'n str> + Clone, frames: &[Transform]) -> [Option<Vec3>; 5] {
        (*crate::melee::POINT_BONES()).map(|tag| {
            let name = &self.names[self.ids.iter().position(|&i| i == tag)?];
            frames.get(parts.clone().position(|p| p == name)?).map(|f| f.translation)
        })
    }

    pub fn world(&self, pose: &[(Vec3, Quat)], body: Transform) -> Vec<(Vec3, Quat)> {
        delirium::ragdoll::pose_frames(&self.parents, pose, body)
    }

    pub fn tagged(&self, world: &[(Vec3, Quat)], tag: u16) -> Option<Vec3> {
        world.get(self.ids.iter().position(|&i| i == tag)?).map(|b| b.0)
    }

    pub fn fight_clip(&self, key: &str) -> Option<(usize, &anim::Animation)> {
        let &c = self.fight.as_ref()?.1.get(key)?;
        Some((c, &self.clips[c].0))
    }

    pub fn mover(&self, c: usize, phase: f32) -> Vec3 {
        let a = &self.clips[c].0;
        let x = phase.clamp(0.0, 1.0) * (a.frames - 1) as f32;
        let (i, f) = (x.floor() as usize, x.fract());
        a.tracks.iter().find(|t| t.kind == anim::MOVER_TRANSLATION)
            .map_or(Vec3::ZERO, |t| Vec3::from_slice(&t.sample(i)).lerp(Vec3::from_slice(&t.sample(i + 1)), f))
    }

    pub fn duration(&self, c: usize) -> f32 {
        self.clips[c].0.duration
    }

    pub fn grow(&mut self, len: &[f32], root: f32) {
        self.scale = self.grown(len, root);
    }

    pub fn grown(&self, len: &[f32], root: f32) -> (Vec<f32>, Vec<f32>) {
        let owner = |b: usize| self.parts.iter().position(|p| p.0 == b);
        let bones = (0..self.parents.len()).map(|i| {
            let mut at = self.parents[i];
            while let Some(b) = at {
                if let Some(k) = owner(b) {
                    return len[k];
                }
                at = self.parents[b];
            }
            root
        }).collect();
        (bones, len.to_vec())
    }

    pub fn place(&self, pose: &[(Vec3, Quat)], body: Transform) -> Vec<Transform> {
        let mut bones: Vec<(Vec3, Quat)> = Vec::with_capacity(pose.len());
        for (i, &(t, r)) in pose.iter().enumerate() {
            let (pt, pr) = self.parents[i].map_or((body.translation, body.rotation), |p| bones[p]);
            bones.push((pt + pr * t * self.scale.0.get(i).copied().unwrap_or(1.0), pr * r));
        }
        self.parts.iter().enumerate().map(|(k, &(b, o))| {
            let (bt, br) = bones[b];
            Transform::from_translation(bt + br * o.translation * self.scale.1.get(k).copied().unwrap_or(1.0)).with_rotation(br * o.rotation)
        }).collect()
    }

    pub fn start(&self, lay: Vec<Transform>) -> Rise {
        let yaw = |q: Quat| { let a = q * Vec3::Y; a.y.atan2(a.x) };
        let ch = self.chest;
        let (_, clip, body) = (0..IDLE).map(|c| {
            let first = self.place(&self.pose(c, 0.0), Transform::IDENTITY);
            let turn = Quat::from_rotation_z(yaw(lay[ch].rotation) - yaw(first[ch].rotation));
            let body = Transform::from_translation(lay[0].translation - turn * first[0].translation).with_rotation(turn);
            ((turn * first[ch].rotation).angle_between(lay[ch].rotation), c, body)
        }).min_by(|a, b| a.0.total_cmp(&b.0)).expect("a get-up clip");
        // MODIFIED (not in the original): the stand-in clips have their floor 1 m under the body's origin; put it on
        // the floor he is lying on, so he does not end up standing above or in it.
        let mut body = body;
        if let Some(floor) = lay.iter().zip(&self.own_low).map(|(f, r)| f.translation.z - r).reduce(f32::min) {
            body.translation.z = floor + 1.0;
        }
        Rise { clip, hold: false, t: 0.0, body, lay }
    }

    pub fn stand(&self, lay: Vec<Transform>, world: &delirium::collision::Collision) -> Rise {
        let yaw = |q: Quat| { let a = q * Vec3::Y; a.y.atan2(a.x) };
        let first = self.place(&self.pose(IDLE, 0.0), Transform::IDENTITY);
        let turn = Quat::from_rotation_z(yaw(lay[0].rotation) - yaw(first[0].rotation));
        let mut body = Transform::from_translation(lay[0].translation - turn * first[0].translation).with_rotation(turn);
        let at = lay[0].translation;
        if let Some((h, _)) = world.segment(at, at - Vec3::Z * delirium_data::kv!(136)) {
            let up = Vec3::new(h.x, h.y, h.z + 1.0);
            let r = Vec3::splat(delirium_data::kv!(78));
            let tris: Vec<[Vec3; 3]> = world.tris_near(up - Vec3::Z * delirium_data::kv!(80) - r, up + r).into_iter().map(|t| t.0).collect();
            body.translation.z = delirium::collision::sphere_down(&tris, up, delirium_data::kv!(78), delirium_data::kv!(80)).map_or(h.z, |s| s.1.z) + 1.0;
        }
        Rise { clip: IDLE, hold: true, t: 0.0, body, lay }
    }

    pub fn stand_up(&self, build: &mut Build) -> Vec<Transform> {
        let mut frames = self.place(&self.pose(IDLE, 0.0), Transform::from_rotation(Quat::from_rotation_z(-std::f32::consts::FRAC_PI_2)));
        for (p, f) in build.parts.iter_mut().zip(&frames) {
            p.bind = f.rotation;
        }
        delirium::nmrs::asset_layout(build, &mut frames);
        frames
    }

    pub fn frames(&self, r: &Rise) -> Option<Vec<Transform>> {
        let d = self.clips[r.clip].0.duration;
        (r.t <= d || r.hold).then(|| {
            // MODIFIED (not in the original): with the stand-in clips, how he lay is carried into the moving clip and
            // fades out smoothly, instead of each part being pulled in a straight line to the clip.
            if !self.own_low.is_empty() && !r.hold {
                let k = (r.t / OWN_BLEND).min(1.0);
                let k = 1.0 - k * k * (3.0 - 2.0 * k);
                let first = self.place(&self.pose(r.clip, 0.0), r.body);
                return self.place(&self.pose(r.clip, r.t / d), r.body).into_iter().zip(first).zip(&r.lay)
                    .map(|((n, f), l)| Transform::from_translation(n.translation + (l.translation - f.translation) * k)
                        .with_rotation(Quat::IDENTITY.slerp(l.rotation * f.rotation.inverse(), k) * n.rotation))
                    .collect();
            }
            let k = (r.t / RISE_BLEND()).min(1.0);
            self.place(&self.pose(r.clip, if r.hold { (r.t / d).fract() } else { r.t / d }), r.body).into_iter().zip(&r.lay)
                .map(|(n, l)| Transform::from_translation(l.translation.lerp(n.translation, k)).with_rotation(l.rotation.slerp(n.rotation, k)))
                .collect()
        })
    }

    pub fn standing(r: &Rise) -> bool {
        r.hold
    }

    pub fn end(&self, r: &Rise) -> Vec<Transform> {
        self.place(&self.pose(r.clip, 1.0), r.body)
    }
}


// MODIFIED (not in the original): stand-in clips for running with NO game (docs/no-game.md). The original reads the
// get-up, idle, walk, run, sprint and gun clips from the game's archives. These are made here from the stand-in body
// alone: a few hand-written key poses per clip, given as how far each joint is bent. They are our own and plain; they
// are not the game's animation.
const OWN_FPS: f32 = 30.0;
/// How long the pose he lay in takes to fade out of a stand-in get-up.
const OWN_BLEND: f32 = 0.6;
/// The limbs that can be planted in a recorded get-up: (upper part, lower part, end part) of each leg and arm.
const LIMBS: [(usize, usize, usize); 4] = [(1, 2, 3), (4, 5, 6), (14, 15, 16), (18, 19, 20)];
/// One key pose, in degrees. pitch: the whole body tipped forward (90: face down, -90: on his back). hip: thigh forward;
/// knee, elbow: bent; ankle: toes up; spine, neck: bent forward; arm: upper arm forward; out: upper arm away from the side.
/// Sides are [left, right].
#[derive(Clone, Copy, Default)]
struct Key {
    t: f32,
    pitch: f32,
    /// roll: leaning to his right; yaw: turned to his left; apart: thigh out to the side; twist: trunk turned to his left.
    roll: f32,
    yaw: f32,
    apart: [f32; 2],
    twist: f32,
    hip: [f32; 2],
    knee: [f32; 2],
    ankle: [f32; 2],
    spine: f32,
    neck: f32,
    arm: [f32; 2],
    out: [f32; 2],
    elbow: [f32; 2],
}

impl Key {
    const N: usize = 23;
    fn channels(&self) -> [f32; Key::N] {
        [self.pitch, self.roll, self.yaw, self.apart[0], self.apart[1], self.twist, self.hip[0], self.hip[1], self.knee[0], self.knee[1], self.ankle[0], self.ankle[1],
         self.spine, self.neck, self.arm[0], self.arm[1], self.out[0], self.out[1], self.elbow[0], self.elbow[1], 0.0, 0.0, 0.0]
    }
    fn of(t: f32, c: &[f32; Key::N]) -> Key {
        Key { t, pitch: c[0], roll: c[1], yaw: c[2], apart: [c[3], c[4]], twist: c[5], hip: [c[6], c[7]], knee: [c[8], c[9]], ankle: [c[10], c[11]],
              spine: c[12], neck: c[13], arm: [c[14], c[15]], out: [c[16], c[17]], elbow: [c[18], c[19]] }
    }
}

struct OwnRig {
    parents: Vec<Option<usize>>,
    stand: Vec<Transform>,
    origin: Vec<Vec3>,
    shape: Vec<(f32, f32, Option<Vec3>)>,
}

impl OwnRig {
    /// Every part's turn from standing, as a quaternion in the standing body's axes (x right, y forward, z up).
    fn turns(&self, k: &Key) -> Vec<Quat> {
        let rx = |deg: f32| Quat::from_rotation_x(deg.to_radians());
        let mut e = vec![Quat::IDENTITY; self.parents.len()];
        e[0] = Quat::from_rotation_z(k.yaw.to_radians()) * rx(-k.pitch) * Quat::from_rotation_y(k.roll.to_radians());
        for (side, leg, arm) in [(0, 1, 13), (1, 4, 17)] {
            e[leg] = rx(k.hip[side]) * Quat::from_rotation_y((if side == 0 { 1.0 } else { -1.0 } * k.apart[side]).to_radians());
            e[leg + 1] = rx(-k.knee[side]);
            e[leg + 2] = rx(k.ankle[side]);
            let away = if side == 0 { 1.0 } else { -1.0 };
            e[arm + 1] = rx(k.arm[side]) * Quat::from_rotation_y((away * k.out[side]).to_radians());
            e[arm + 2] = rx(k.elbow[side]);
        }
        for s in 7..11 {
            e[s] = Quat::from_rotation_z((k.twist / 4.0).to_radians()) * rx(-k.spine / 4.0);
        }
        e[11] = rx(-k.neck / 2.0);
        e[12] = rx(-k.neck / 2.0);
        e
    }

    /// Where each part is with these turns (pelvis at the origin), and the lowest point of the body.
    fn posed(&self, e: &[Quat]) -> (Vec<Transform>, f32) {
        let n = self.parents.len();
        let (mut d, mut at) = (vec![Quat::IDENTITY; n], vec![Vec3::ZERO; n]);
        let mut out = Vec::with_capacity(n);
        let mut low = f32::MAX;
        for k in 0..n {
            match self.parents[k] {
                None => (d[k], at[k]) = (e[k], Vec3::ZERO),
                Some(p) => (d[k], at[k]) = (d[p] * e[k], at[p] + d[p] * (self.origin[k] - self.origin[p])),
            }
            let f = Transform::from_translation(at[k] + d[k] * (self.stand[k].translation - self.origin[k])).with_rotation(d[k] * self.stand[k].rotation);
            low = low.min(self.low_of(k, &f));
            out.push(f);
        }
        (out, low)
    }

    /// The lowest point of part `k` when it is at `f`.
    fn low_of(&self, k: usize, f: &Transform) -> f32 {
        let (r, h, boxed) = self.shape[k];
        match boxed {
            Some(b) => f.translation.z - (f.rotation * Vec3::X).z.abs() * b.x - (f.rotation * Vec3::Y).z.abs() * b.y - (f.rotation * Vec3::Z).z.abs() * b.z,
            None => f.translation.z - (f.rotation * Vec3::Y).z.abs() * h - r,
        }
    }

    /// A clip from key poses. `feet`: keep the feet where they are (get-ups) instead of the pelvis over the origin.
    /// `travel`: metres moved forward over the clip (walks). The floor is 1 m under the body's origin, as in the game's clips.
    fn clip(&self, name: &str, keys: &[Key], feet: bool, travel: f32) -> (anim::Animation, Vec<Option<usize>>) {
        let n = self.parents.len();
        let duration = keys.last().map_or(1.0, |k| k.t).max(0.05);
        let frames = ((duration * OWN_FPS).round() as usize).max(1) + 1;
        let mut poses = Vec::with_capacity(frames);
        for f in 0..frames {
            let t = duration * f as f32 / (frames - 1) as f32;
            let i = keys.iter().rposition(|k| k.t <= t).unwrap_or(0).min(keys.len().saturating_sub(2));
            let (a, b) = (&keys[i], &keys[(i + 1).min(keys.len() - 1)]);
            let u = if b.t > a.t { ((t - a.t) / (b.t - a.t)).clamp(0.0, 1.0) } else { 0.0 };
            let e: Vec<Quat> = if feet {
                // a smooth curve through the key poses (no stop at each one), joint by joint
                let (before, after) = (&keys[i.saturating_sub(1)], &keys[(i + 2).min(keys.len() - 1)]);
                let (ca, cb, c0, c1) = (a.channels(), b.channels(), before.channels(), after.channels());
                let (h, u2, u3) = (b.t - a.t, u * u, u * u * u);
                let mut c = [0.0f32; Key::N];
                for j in 0..Key::N {
                    let ma = if i == 0 { 0.0 } else { (cb[j] - c0[j]) / (b.t - before.t).max(1e-3) };
                    let mb = if i + 2 > keys.len() - 1 { 0.0 } else { (c1[j] - ca[j]) / (after.t - a.t).max(1e-3) };
                    c[j] = (2.0 * u3 - 3.0 * u2 + 1.0) * ca[j] + (u3 - 2.0 * u2 + u) * h * ma + (-2.0 * u3 + 3.0 * u2) * cb[j] + (u3 - u2) * h * mb;
                }
                self.turns(&Key::of(t, &c))
            } else {
                self.turns(a).into_iter().zip(self.turns(b)).map(|(x, y)| x.slerp(y, u)).collect()
            };
            let (parts, low) = self.posed(&e);
            let mid = parts[6].translation;   // get-ups: the right foot stays planted
            let root = if feet { Vec3::new(-mid.x, -mid.y, -1.0 - low) } else { Vec3::new(0.0, 0.0, -1.0 - low) };
            poses.push((e, root));
        }
        self.bake(name, duration, poses, travel)
    }

    /// A clip from every frame's pose: each part's turn from standing (see `turns`) and where the body's origin is.
    fn bake(&self, name: &str, duration: f32, poses: Vec<(Vec<Quat>, Vec3)>, travel: f32) -> (anim::Animation, Vec<Option<usize>>) {
        let n = self.parents.len();
        let frames = poses.len();
        let mut rot = vec![vec![vec![0.0f32; frames]; 4]; n];
        let mut pos = vec![vec![0.0f32; frames]; 3];
        let mut mover = vec![vec![0.0f32; frames]; 3];
        for (f, (e, root)) in poses.into_iter().enumerate() {
            for k in 0..n {
                let q = match self.parents[k] {
                    None => e[0] * self.stand[0].rotation,
                    Some(p) => self.stand[p].rotation.inverse() * e[k] * self.stand[k].rotation,
                }.normalize();
                for (c, v) in [q.x, q.y, q.z, q.w].into_iter().enumerate() {
                    rot[k][c][f] = v;
                }
            }
            for (c, v) in root.to_array().into_iter().enumerate() {
                pos[c][f] = v;
            }
            mover[1][f] = travel * f as f32 / (frames - 1).max(1) as f32;
        }
        let mut tracks: Vec<anim::Track> = rot.into_iter().enumerate().map(|(k, values)| anim::Track { kind: anim::BONE_ROTATION, bone: k as u16, values }).collect();
        tracks.push(anim::Track { kind: anim::BONE_TRANSLATION, bone: 0, values: pos });
        if travel != 0.0 {
            tracks.push(anim::Track { kind: anim::MOVER_TRANSLATION, bone: 0, values: mover });
        }
        let map = tracks.iter().map(|t| Some(t.bone as usize).filter(|&b| b != 0)).collect();
        (anim::Animation { name: name.into(), hash: 0, frames, duration, tracks, mover_rotation: None, events: vec![] }, map)
    }

    /// A clip from a recorded motion (`tools/kimodo_to_clip.py` writes the text): every frame gives each part's turn
    /// from the recording's own T-pose, in the clips' axes, and where the hips are over the floor. The turns are put on
    /// this body by matching bone directions; the height comes from this body's lowest point, so he stays on the floor;
    /// the last moments ease into this body's own standing pose. None if the text is empty or does not fit this body.
    /// Hands and feet the recording marks as resting on the floor are planted: a resting foot holds the whole body in
    /// place (so it does not slide when his proportions differ from the recording's), and each resting hand or foot is
    /// bent onto its own spot on the floor, stepping to a new spot when the motion carries it too far away.
    fn recorded(&self, name: &str, text: &str) -> Option<(anim::Animation, Vec<Option<usize>>)> {
        let n = self.parents.len();
        let mut lines = text.lines().filter(|l| !l.trim().is_empty() && !l.starts_with('#'));
        let nums = |l: &str| l.split_whitespace().filter_map(|v| v.parse::<f32>().ok()).collect::<Vec<f32>>();
        let head = nums(lines.next()?);
        let (fps, hips) = (*head.first()?, *head.get(1)?);
        let dirs = nums(lines.next()?);
        if dirs.len() != n * 3 || fps <= 0.0 || hips <= 0.0 {
            return None;
        }
        // each part's turn from this body's standing pose to the recording's T-pose, by its bone's direction
        let fix: Vec<Quat> = (0..n).map(|k| {
            let (mine, theirs) = (self.stand[k].translation - self.origin[k], Vec3::new(dirs[k * 3], dirs[k * 3 + 1], dirs[k * 3 + 2]));
            if mine.length() < 1e-4 || theirs.length() < 1e-4 { Quat::IDENTITY } else { Quat::from_rotation_arc(mine.normalize(), theirs.normalize()) }
        }).collect();
        let scale = (self.stand[0].translation.z + 1.0) / hips;
        let speed = head.get(2).copied().filter(|s| *s > 0.0).unwrap_or(1.0);
        let mut all: Vec<(Vec<Quat>, Vec3, [bool; 4])> = Vec::new();
        for l in lines {
            let v = nums(l);
            if v.len() != n * 4 + 2 && v.len() != n * 4 + 6 {
                return None;
            }
            let d: Vec<Quat> = (0..n).map(|k| (Quat::from_xyzw(v[k * 4], v[k * 4 + 1], v[k * 4 + 2], v[k * 4 + 3]).normalize() * fix[k]).normalize()).collect();
            let on: [bool; 4] = std::array::from_fn(|j| LIMBS.iter().all(|l| l.2 < n) && v.get(n * 4 + 2 + j).is_some_and(|&c| c > 0.5));
            all.push((d, Vec3::new(v[n * 4] * scale, v[n * 4 + 1] * scale, 0.0), on));
        }
        if all.len() < 2 {
            return None;
        }
        // ease into standing, facing the way he ends up facing
        let last = all.len() - 1;
        let ahead = all[last].0[0] * Vec3::Y;
        let facing = Quat::from_rotation_z(ahead.y.atan2(ahead.x) - std::f32::consts::FRAC_PI_2);
        let ease = ((0.5 * fps) as usize).clamp(1, last);
        let eased = |f: usize| { let u = (1.0 - (last - f) as f32 / ease as f32).clamp(0.0, 1.0); u * u * (3.0 - 2.0 * u) };
        for (f, (d, _, _)) in all.iter_mut().enumerate() {
            for q in d.iter_mut() {
                *q = q.slerp(facing, eased(f));
            }
        }
        let local = |d: &[Quat]| -> Vec<Quat> { (0..n).map(|k| match self.parents[k] { None => d[k], Some(p) => d[p].inverse() * d[k] }).collect() };
        // a resting foot holds the body in place: move the whole body back by however far the recording's (rescaled)
        // path would drag that foot
        let mut shift = Vec::with_capacity(all.len());
        let (mut s, mut before): (Vec3, Option<(Vec<Vec3>, [bool; 4])>) = (Vec3::ZERO, None);
        for (d, at, on) in &all {
            let parts = self.posed(&local(d)).0;
            let ends: Vec<Vec3> = LIMBS.iter().map(|l| parts.get(l.2).map_or(Vec3::ZERO, |p| p.translation) + *at).collect();
            if let Some((was, was_on)) = &before {
                let held: Vec<Vec3> = (0..2).filter(|&j| on[j] && was_on[j]).map(|j| was[j] - ends[j]).collect();
                if !held.is_empty() {
                    let m = held.iter().sum::<Vec3>() / held.len() as f32;
                    s += Vec3::new(m.x, m.y, 0.0);
                }
            }
            shift.push(s);
            before = Some((ends, *on));
        }
        let start = all[0].1 + shift[0];
        // each resting hand and foot: `moved` is how far it is held away from where the recording puts it
        let (mut moved, mut spot, mut stepping) = ([Vec3::ZERO; 4], [None::<Vec3>; 4], [0.0f32; 4]);
        let poses = all.into_iter().enumerate().map(|(f, (mut d, at, on))| {
            let at = at + shift[f];
            let (parts, low) = self.posed(&local(&d));
            for (j, &(upper, lower, end)) in LIMBS.iter().enumerate() {
                if end >= n {
                    continue;
                }
                let p = parts[end].translation + at;
                let flat = |v: Vec3| Vec3::new(v.x, v.y, 0.0);
                if !on[j] {
                    (spot[j], stepping[j]) = (None, 0.0);
                } else if stepping[j] > 0.0 {
                    if flat(moved[j]).length() < 0.02 {
                        (spot[j], stepping[j]) = (Some(p + moved[j]), 0.0);
                    }
                } else if spot[j].is_none() {
                    spot[j] = Some(p + moved[j]);
                }
                let mut goal = Vec3::ZERO;
                if let (Some(q), true) = (spot[j], stepping[j] == 0.0) {
                    // on its spot, and down onto the floor
                    goal = Vec3::new(q.x - p.x, q.y - p.y, -(self.low_of(end, &parts[end]) - low).clamp(0.0, 0.25));
                    let far = flat(goal).length();
                    if far > if j < 2 { 0.10 } else { 0.15 } {
                        (spot[j], stepping[j], goal) = (None, far, Vec3::ZERO);   // too far: step to a new spot
                    }
                }
                moved[j] += (goal - moved[j]).clamp_length_max(0.03);
                let lift = if stepping[j] > 0.0 { let r = (flat(moved[j]).length() / stepping[j]).min(1.0); 1.4 * stepping[j] * r * (1.0 - r) } else { 0.0 };
                let off = (moved[j] + Vec3::Z * lift) * (1.0 - eased(f));
                if off.length() < 1e-4 {
                    continue;
                }
                // bend the limb so its end is `off` away: first the knee or elbow, then the whole limb from the hip or shoulder
                let joint = |k: usize| parts[k].translation - d[k] * (self.stand[k].translation - self.origin[k]);
                let (a, b, c) = (joint(upper), joint(lower), joint(end));
                let (l1, l2, t) = ((b - a).length(), (c - b).length(), c + off);
                if l1 < 1e-4 || l2 < 1e-4 {
                    continue;
                }
                let want = (t - a).length().clamp((l1 - l2).abs() + 1e-3, l1 + l2 - 1e-3);
                let (cur, des) = ((a - b).angle_between(c - b), ((l1 * l1 + l2 * l2 - want * want) / (2.0 * l1 * l2)).clamp(-1.0, 1.0).acos());
                let cross = (c - b).cross(a - b);
                let axis = if cross.length() > 0.05 * l1 * l2 { cross.normalize() } else {
                    // nearly straight: the way a knee or an elbow bends
                    let (h, bone) = (d[upper] * if j < 2 { -Vec3::X } else { Vec3::X }, (c - b).normalize());
                    (h - bone * h.dot(bone)).normalize_or_zero()
                };
                if axis == Vec3::ZERO {
                    continue;
                }
                let bend = Quat::from_axis_angle(axis, cur - des);
                let c1 = b + bend * (c - b);
                let swing = Quat::from_rotation_arc((c1 - a).normalize(), (t - a).normalize());
                d[upper] = (swing * d[upper]).normalize();
                d[lower] = (swing * bend * d[lower]).normalize();
            }
            let e = local(&d);
            let low = self.posed(&e).1;
            (e, Vec3::new(at.x - start.x, at.y - start.y, -1.0 - low))
        }).collect::<Vec<_>>();
        Some(self.bake(name, last as f32 / fps / speed, poses, 0.0))
    }

    /// One stride of a walk, run or sprint: `swing` hips, `knee` lift, `arms` swing, `lean` forward, elbows held at `elbow`.
    #[allow(clippy::too_many_arguments)]
    fn stride(&self, name: &str, secs: f32, travel: f32, swing: f32, knee: f32, arms: f32, lean: f32, elbow: f32) -> (anim::Animation, Vec<Option<usize>>) {
        let keys: Vec<Key> = (0..=16).map(|i| {
            let ph = i as f32 / 16.0 * std::f32::consts::TAU;
            let (s, c) = ph.sin_cos();
            Key { t: secs * i as f32 / 16.0, pitch: lean, hip: [swing * s + lean, -swing * s + lean], knee: [knee * c.max(0.0) + 6.0, knee * (-c).max(0.0) + 6.0],
                  ankle: [0.0; 2], spine: lean * 0.3, neck: -lean, arm: [-arms * s, arms * s], out: [0.0; 2], elbow: [elbow; 2], ..Key::default() }
        }).collect();
        self.clip(name, &keys, false, travel)
    }
}

impl Clips {
    /// The stand-in clips for a body that did not come from the game: `stand` is how its parts are when it stands.
    pub fn own(build: &Build, stand: &[Transform]) -> Clips {
        let n = build.parts.len();
        let half_turn = Quat::from_rotation_z(std::f32::consts::PI);
        let p0 = stand[0].translation;
        // the standing body in the clips' space: facing +y, the floor at z = -1, the pelvis over the origin
        let g: Vec<Transform> = stand.iter().map(|f| Transform::from_translation(half_turn * (f.translation - Vec3::new(p0.x, p0.y, 1.0))).with_rotation(half_turn * f.rotation)).collect();
        let parents: Vec<Option<usize>> = build.parts.iter().map(|p| p.parent).collect();
        let origin: Vec<Vec3> = (0..n).map(|k| if parents[k].is_some() { g[k].translation + g[k].rotation * build.parts[k].anchor } else { g[k].translation }).collect();
        let rig = OwnRig { parents: parents.clone(), stand: g.clone(), origin: origin.clone(), shape: build.parts.iter().map(|p| (p.radius, p.half, p.boxed)).collect() };
        let z = Key::default();
        // From his front: head and chest come up on the hands, back onto hands and knees, the left foot is brought
        // forward and planted, he pushes off that knee with a hand, and straightens as the right foot comes under him.
        let front = [
            Key { t: 0.0, pitch: 90.0, ankle: [-55.0; 2], neck: -10.0, arm: [5.0; 2], out: [25.0; 2], elbow: [100.0; 2], ..z },
            Key { t: 0.35, pitch: 84.0, ankle: [-55.0; 2], spine: -14.0, neck: -32.0, arm: [18.0, 14.0], out: [28.0; 2], elbow: [92.0, 96.0], ..z },
            Key { t: 0.85, pitch: 76.0, roll: -3.0, hip: [68.0, 72.0], knee: [84.0, 88.0], ankle: [-58.0; 2], spine: 6.0, neck: -24.0, arm: [80.0, 78.0], out: [10.0; 2], elbow: [8.0, 12.0], apart: [6.0; 2], ..z },
            Key { t: 1.3, pitch: 46.0, roll: 5.0, yaw: 7.0, hip: [108.0, 44.0], knee: [70.0, 96.0], ankle: [4.0, -48.0], spine: 16.0, neck: -8.0, arm: [62.0, 44.0], out: [4.0, 14.0], elbow: [34.0, 10.0], apart: [12.0, 4.0], twist: -6.0, ..z },
            Key { t: 1.75, pitch: 36.0, roll: -2.0, yaw: 4.0, hip: [84.0, 58.0], knee: [62.0, 78.0], ankle: [10.0, 12.0], spine: 14.0, neck: 0.0, arm: [34.0, 20.0], out: [6.0; 2], elbow: [40.0, 24.0], apart: [8.0, 5.0], twist: 4.0, ..z },
            Key { t: 2.2, pitch: 13.0, hip: [24.0, 18.0], knee: [26.0, 20.0], ankle: [4.0; 2], spine: 9.0, neck: 4.0, arm: [6.0, -6.0], elbow: [22.0, 16.0], apart: [3.0; 2], ..z },
            Key { t: 2.55, pitch: -1.5, hip: [-2.0; 2], spine: -2.0, neck: 0.0, arm: [-4.0, 3.0], elbow: [8.0; 2], ..z },
            Key { t: 2.9, ..z },
        ];
        // From his back: chin to the chest and knees up, he sits up propped on the right hand, tucks the feet in under
        // him and rocks forward over them with the arms out ahead, then stands out of the squat.
        let back = [
            Key { t: 0.0, pitch: -90.0, ankle: [-30.0; 2], elbow: [10.0; 2], out: [12.0; 2], ..z },
            Key { t: 0.4, pitch: -84.0, roll: 4.0, hip: [38.0, 22.0], knee: [64.0, 38.0], ankle: [-20.0; 2], spine: 16.0, neck: 26.0, arm: [-6.0, -16.0], out: [14.0, 22.0], elbow: [24.0, 30.0], ..z },
            Key { t: 0.95, pitch: -34.0, roll: 11.0, yaw: -8.0, hip: [86.0, 70.0], knee: [98.0, 62.0], ankle: [-6.0, -14.0], spine: 26.0, neck: 12.0, arm: [34.0, -42.0], out: [8.0, 22.0], elbow: [44.0, 8.0], apart: [8.0, 6.0], twist: 8.0, ..z },
            Key { t: 1.45, pitch: 6.0, roll: 4.0, yaw: -3.0, hip: [122.0, 116.0], knee: [128.0, 120.0], ankle: [14.0, 10.0], spine: 26.0, neck: 6.0, arm: [44.0, 18.0], out: [6.0, 12.0], elbow: [30.0, 14.0], apart: [10.0; 2], ..z },
            Key { t: 1.9, pitch: 38.0, hip: [122.0, 118.0], knee: [120.0, 116.0], ankle: [22.0, 20.0], spine: 16.0, neck: -6.0, arm: [56.0, 50.0], out: [6.0; 2], elbow: [24.0, 28.0], apart: [10.0; 2], ..z },
            Key { t: 2.35, pitch: 18.0, hip: [44.0, 38.0], knee: [42.0, 36.0], ankle: [8.0; 2], spine: 10.0, neck: 2.0, arm: [16.0, 10.0], elbow: [20.0; 2], apart: [4.0; 2], ..z },
            Key { t: 2.7, pitch: -1.5, hip: [-2.0; 2], spine: -2.0, arm: [-5.0, -2.0], elbow: [8.0; 2], ..z },
            Key { t: 3.05, ..z },
        ];
        // a recorded get-up where there is one (made with Kimodo, see docs/no-game.md), else the key poses above
        let mut clips = vec![rig.recorded("get_up_fast", &std::env::var("DELIRIUM_GETUP_FRONT").ok().and_then(|f| std::fs::read_to_string(f).ok()).unwrap_or_else(|| include_str!("getup-front-kimodo.txt").into())).unwrap_or_else(|| rig.clip("get_up_fast", &front, true, 0.0)),
                             rig.recorded("get_up_fast", &std::env::var("DELIRIUM_GETUP_BACK").ok().and_then(|f| std::fs::read_to_string(f).ok()).unwrap_or_else(|| include_str!("getup-back-kimodo.txt").into())).unwrap_or_else(|| rig.clip("get_up_fast", &back, true, 0.0)),
                             rig.clip("idle", &[z, Key { t: 1.0, ..z }], false, 0.0),
                             rig.stride("walk", 1.0, 1.4, 24.0, 45.0, 18.0, 3.0, 15.0),
                             rig.stride("run", 0.66, 2.4, 38.0, 80.0, 38.0, 9.0, 80.0),
                             rig.stride("sprint", 0.5, 3.0, 48.0, 100.0, 52.0, 14.0, 90.0)];
        // guns: the right arm held out to fire, bent to reload
        let aim = Key { arm: [0.0, 85.0], elbow: [0.0, 8.0], ..z };
        let load = Key { arm: [35.0, 40.0], elbow: [80.0, 95.0], ..z };
        clips.push(rig.clip("fire", &[aim, Key { t: 0.08, arm: [0.0, 92.0], ..aim }, Key { t: 0.25, ..aim }], false, 0.0));
        clips.push(rig.clip("reload", &[aim, Key { t: 0.3, ..load }, Key { t: 0.9, ..load }, Key { t: 1.2, ..aim }], false, 0.0));
        let guns = vec![Some((clips.len() - 2, clips.len() - 1)); GUN_CLIPS.len()];
        // a plain right punch, for the Hero with no fight data
        let wind = Key { arm: [20.0, 10.0], elbow: [70.0, 120.0], spine: 5.0, ..z };
        clips.push(rig.clip("punch", &[Key { t: 0.0, ..z }, Key { t: 0.12, ..wind }, Key { t: 0.24, arm: [10.0, 88.0], elbow: [60.0, 5.0], spine: 10.0, ..z }, Key { t: 0.5, ..z }], false, 0.0));
        let bind: Vec<(Vec3, Quat)> = (0..n).map(|k| match parents[k] {
            None => (g[0].translation, g[0].rotation),
            Some(p) => (g[p].rotation.inverse() * (origin[k] - origin[p]), g[p].rotation.inverse() * g[k].rotation),
        }).collect();
        let parts: Vec<(usize, Transform)> = (0..n).map(|k| (k, Transform::from_translation(g[k].rotation.inverse() * (g[k].translation - origin[k])))).collect();
        let mut body = build.clone();
        for (k, p) in body.parts.iter_mut().enumerate() {
            (p.bone, p.offset) = (k, parts[k].1);
        }
        let chest = build.parts.iter().position(|d| d.parent == Some(0) && !d.lower).unwrap_or(0);
        Clips { scale: Default::default(), own_low: build.parts.iter().map(|p| p.boxed.map_or(p.radius, |b| b.min_element())).collect(), bind, hero: Some(std::rc::Rc::new(delirium::ragdoll::Rig::own(body, parents.clone()))), parents,
                fight_from: clips.len(), clips, parts, chest, guns, names: build.parts.iter().map(|p| p.name.clone()).collect(),
                ids: (0..n as u16).collect(), fight: None, swim: None }
    }

    /// The stand-in punch clip, when these are the stand-in clips (no fight data).
    pub fn own_punch(&self) -> Option<usize> {
        (self.fight.is_none() && self.clips.last().is_some_and(|c| c.0.name == "punch")).then(|| self.clips.len() - 1)
    }
}
