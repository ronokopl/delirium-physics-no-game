# One-off: lets the stand-in get-up clips come from a recorded motion file (made with NVIDIA's Kimodo by
# tools/kimodo_to_clip.py) instead of the hand-written key poses. An empty file keeps the key poses.
import io
def rd(p): return io.open(p, encoding="utf-8", newline="").read()
def wr(p, t): io.open(p, "w", encoding="utf-8", newline="").write(t)
p = "crates/delirium-room/src/getup.rs"; t = rd(p).replace("\r\n", "\n")
def sub(a, b):
    global t
    assert t.count(a) == 1, (t.count(a), a[:70])
    t = t.replace(a, b)

# 1. split clip(): the per-frame poses, then the baking into tracks
sub('''        let mut rot = vec![vec![vec![0.0f32; frames]; 4]; n];
        let mut pos = vec![vec![0.0f32; frames]; 3];
        let mut mover = vec![vec![0.0f32; frames]; 3];
        for f in 0..frames {
            let t = duration * f as f32 / (frames - 1) as f32;''', '''        let mut poses = Vec::with_capacity(frames);
        for f in 0..frames {
            let t = duration * f as f32 / (frames - 1) as f32;''')
sub('''            let root = if feet { Vec3::new(-mid.x, -mid.y, -1.0 - low) } else { Vec3::new(0.0, 0.0, -1.0 - low) };
            for k in 0..n {''', '''            let root = if feet { Vec3::new(-mid.x, -mid.y, -1.0 - low) } else { Vec3::new(0.0, 0.0, -1.0 - low) };
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
            for k in 0..n {''')
sub('''            mover[1][f] = travel * f as f32 / (frames - 1) as f32;''', '''            mover[1][f] = travel * f as f32 / (frames - 1).max(1) as f32;''')

# 2. a clip from a recorded motion
sub('''    /// One stride of a walk, run or sprint:''', '''    /// A clip from a recorded motion (`tools/kimodo_to_clip.py` writes the text): every frame gives each part's turn
    /// from the recording's own T-pose, in the clips' axes, and where the hips are over the floor. The turns are put on
    /// this body by matching bone directions; the height comes from this body's lowest point, so he stays on the floor;
    /// the last moments ease into this body's own standing pose. None if the text is empty or does not fit this body.
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
        let mut all: Vec<(Vec<Quat>, Vec3)> = Vec::new();
        for l in lines {
            let v = nums(l);
            if v.len() != n * 4 + 2 {
                return None;
            }
            let d: Vec<Quat> = (0..n).map(|k| (Quat::from_xyzw(v[k * 4], v[k * 4 + 1], v[k * 4 + 2], v[k * 4 + 3]).normalize() * fix[k]).normalize()).collect();
            all.push((d, Vec3::new(v[n * 4] * scale, v[n * 4 + 1] * scale, 0.0)));
        }
        if all.len() < 2 {
            return None;
        }
        // ease into standing, facing the way he ends up facing
        let last = all.len() - 1;
        let ahead = all[last].0[0] * Vec3::Y;
        let facing = Quat::from_rotation_z(ahead.y.atan2(ahead.x) - std::f32::consts::FRAC_PI_2);
        let ease = ((0.5 * fps) as usize).clamp(1, last);
        let start = all[0].1;
        let poses = all.into_iter().enumerate().map(|(f, (mut d, at))| {
            let u = (1.0 - (last - f) as f32 / ease as f32).clamp(0.0, 1.0);
            let u = u * u * (3.0 - 2.0 * u);
            for q in d.iter_mut() {
                *q = q.slerp(facing, u);
            }
            let e: Vec<Quat> = (0..n).map(|k| match self.parents[k] { None => d[k], Some(p) => d[p].inverse() * d[k] }).collect();
            let low = self.posed(&e).1;
            (e, Vec3::new(at.x - start.x, at.y - start.y, -1.0 - low))
        }).collect::<Vec<_>>();
        Some(self.bake(name, last as f32 / fps, poses, 0.0))
    }

    /// One stride of a walk, run or sprint:''')

sub('''        let mut clips = vec![rig.clip("get_up_fast", &front, true, 0.0), rig.clip("get_up_fast", &back, true, 0.0),''',
'''        // a recorded get-up where there is one (made with Kimodo, see docs/no-game.md), else the key poses above
        let mut clips = vec![rig.recorded("get_up_fast", include_str!("getup-front-kimodo.txt")).unwrap_or_else(|| rig.clip("get_up_fast", &front, true, 0.0)),
                             rig.recorded("get_up_fast", include_str!("getup-back-kimodo.txt")).unwrap_or_else(|| rig.clip("get_up_fast", &back, true, 0.0)),''')
wr(p, t)
for f in ("front", "back"):
    q = f"crates/delirium-room/src/getup-{f}-kimodo.txt"
    try: open(q).close()
    except OSError: open(q, "w").close()
print("done")
