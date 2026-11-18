# One-off: hand and foot planting for the recorded (Kimodo) get-ups, a speed in the clip text, and a start that
# carries the landed pose into the clip. Also adds the contact marks to tools/kimodo_to_clip.py.
import io
def rd(p): return io.open(p, encoding="utf-8", newline="").read()
def wr(p, t): io.open(p, "w", encoding="utf-8", newline="").write(t)
def patch(p, pairs):
    t = rd(p).replace("\r\n", "\n")
    for a, b in pairs:
        assert t.count(a) == 1, (p, t.count(a), a[:70])
        t = t.replace(a, b)
    wr(p, t)

patch("tools/kimodo_to_clip.py", [
('''#   <kimodo>/.venv/Scripts/python tools/kimodo_to_clip.py <motion.npz> <out.txt> [--from FRAME] [--to FRAME] [--note TEXT]
# The text: "fps hip-height", then each of Homer's 21 parts' bone direction in Kimodo's T-pose, then one line per frame:
# each part's turn from that T-pose (x y z w) and where the hips are on the floor. Axes: x right, y forward, z up.''',
'''#   <kimodo>/.venv/Scripts/python tools/kimodo_to_clip.py <motion.npz> <out.txt> [--from FRAME] [--to FRAME] [--speed 1.0] [--note TEXT]
# The text: "fps hip-height speed", then each of Homer's 21 parts' bone direction in Kimodo's T-pose, then one line per frame:
# each part's turn from that T-pose (x y z w), where the hips are on the floor, and four 0/1 marks: left foot, right foot,
# left hand, right hand resting on the floor (a foot: low and not moving; a hand: low). Axes: x right, y forward, z up.'''),
('first, last, note = opt("--from"), opt("--to"), opt("--note", "")', 'first, last, note, speed = opt("--from"), opt("--to"), opt("--note", ""), float(opt("--speed", "1"))'),
('''lo, hi = int(first or 0), int(last or T - 1)
''', '''lo, hi = int(first or 0), int(last or T - 1)

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
'''),
('f"30 {hips:.4f}"', 'f"30 {hips:.4f} {speed:g}"'),
('''    lines.append(" ".join(f"{v:.5f}" for v in row) + f" {at[0]:.4f} {at[1]:.4f}")''',
 '''    lines.append(" ".join(f"{v:.5f}" for v in row) + f" {at[0]:.4f} {at[1]:.4f} " + " ".join(str(int(m[f])) for m in marks))'''),
])

patch("crates/delirium-room/src/getup.rs", [
# the start: carry the landed pose into the moving clip
('''        (r.t <= d || r.hold).then(|| {
            let k = (r.t / RISE_BLEND()).min(1.0);''', '''        (r.t <= d || r.hold).then(|| {
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
            let k = (r.t / RISE_BLEND()).min(1.0);'''),
('''const OWN_FPS: f32 = 30.0;''', '''const OWN_FPS: f32 = 30.0;
/// How long the pose he lay in takes to fade out of a stand-in get-up.
const OWN_BLEND: f32 = 0.6;
/// The limbs that can be planted in a recorded get-up: (upper part, lower part, end part) of each leg and arm.
const LIMBS: [(usize, usize, usize); 4] = [(1, 2, 3), (4, 5, 6), (14, 15, 16), (18, 19, 20)];'''),
('''            let (r, h, boxed) = self.shape[k];
            low = low.min(match boxed {
                Some(b) => f.translation.z - (f.rotation * Vec3::X).z.abs() * b.x - (f.rotation * Vec3::Y).z.abs() * b.y - (f.rotation * Vec3::Z).z.abs() * b.z,
                None => f.translation.z - (f.rotation * Vec3::Y).z.abs() * h - r,
            });
            out.push(f);
        }
        (out, low)
    }
''', '''            low = low.min(self.low_of(k, &f));
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
'''),
('''    /// the last moments ease into this body's own standing pose. None if the text is empty or does not fit this body.''',
 '''    /// the last moments ease into this body's own standing pose. None if the text is empty or does not fit this body.
    /// Hands and feet the recording marks as resting on the floor are planted: a resting foot holds the whole body in
    /// place (so it does not slide when his proportions differ from the recording's), and each resting hand or foot is
    /// bent onto its own spot on the floor, stepping to a new spot when the motion carries it too far away.'''),
('''        let scale = (self.stand[0].translation.z + 1.0) / hips;
        let mut all: Vec<(Vec<Quat>, Vec3)> = Vec::new();
        for l in lines {
            let v = nums(l);
            if v.len() != n * 4 + 2 {
                return None;
            }''', '''        let scale = (self.stand[0].translation.z + 1.0) / hips;
        let speed = head.get(2).copied().filter(|s| *s > 0.0).unwrap_or(1.0);
        let mut all: Vec<(Vec<Quat>, Vec3, [bool; 4])> = Vec::new();
        for l in lines {
            let v = nums(l);
            if v.len() != n * 4 + 2 && v.len() != n * 4 + 6 {
                return None;
            }'''),
('''            all.push((d, Vec3::new(v[n * 4] * scale, v[n * 4 + 1] * scale, 0.0)));
        }
        if all.len() < 2 {
            return None;
        }''', '''            let on: [bool; 4] = std::array::from_fn(|j| LIMBS.iter().all(|l| l.2 < n) && v.get(n * 4 + 2 + j).is_some_and(|&c| c > 0.5));
            all.push((d, Vec3::new(v[n * 4] * scale, v[n * 4 + 1] * scale, 0.0), on));
        }
        if all.len() < 2 {
            return None;
        }'''),
('''        let start = all[0].1;
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
        Some(self.bake(name, last as f32 / fps, poses, 0.0))''', '''        let eased = |f: usize| { let u = (1.0 - (last - f) as f32 / ease as f32).clamp(0.0, 1.0); u * u * (3.0 - 2.0 * u) };
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
        Some(self.bake(name, last as f32 / fps / speed, poses, 0.0))'''),
])
print("done")
