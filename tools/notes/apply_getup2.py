# One-off: the stand-in get-up clips reworked to move less like a robot: more joints in play (roll, turn, legs apart,
# trunk twist), a smooth curve through the key poses instead of stop-start, one planted foot, and uneven sequences.
import io
def rd(p): return io.open(p, encoding="utf-8", newline="").read()
def wr(p, t): io.open(p, "w", encoding="utf-8", newline="").write(t)
p = "crates/delirium-room/src/getup.rs"; t = rd(p).replace("\r\n", "\n")
def sub(a, b):
    global t
    assert t.count(a) == 1, (t.count(a), a[:70])
    t = t.replace(a, b)

sub('''struct Key {
    t: f32,
    pitch: f32,''', '''struct Key {
    t: f32,
    pitch: f32,
    /// roll: leaning to his right; yaw: turned to his left; apart: thigh out to the side; twist: trunk turned to his left.
    roll: f32,
    yaw: f32,
    apart: [f32; 2],
    twist: f32,''')

sub('''        let mut e = vec![Quat::IDENTITY; self.parents.len()];
        e[0] = rx(-k.pitch);
        for (side, leg, arm) in [(0, 1, 13), (1, 4, 17)] {
            e[leg] = rx(k.hip[side]);''', '''        let mut e = vec![Quat::IDENTITY; self.parents.len()];
        e[0] = Quat::from_rotation_z(k.yaw.to_radians()) * rx(-k.pitch) * Quat::from_rotation_y(k.roll.to_radians());
        for (side, leg, arm) in [(0, 1, 13), (1, 4, 17)] {
            e[leg] = rx(k.hip[side]) * Quat::from_rotation_y((if side == 0 { 1.0 } else { -1.0 } * k.apart[side]).to_radians());''')
sub('''            e[s] = rx(-k.spine / 4.0);''', '''            e[s] = Quat::from_rotation_z((k.twist / 4.0).to_radians()) * rx(-k.spine / 4.0);''')

# smooth curve through the keys, one planted foot
sub('''            let u = if b.t > a.t { ((t - a.t) / (b.t - a.t)).clamp(0.0, 1.0) } else { 0.0 };
            let u = if feet { u * u * (3.0 - 2.0 * u) } else { u };
            let e: Vec<Quat> = self.turns(a).into_iter().zip(self.turns(b)).map(|(x, y)| x.slerp(y, u)).collect();
            let (parts, low) = self.posed(&e);
            let mid = (parts[3].translation + parts[6].translation) * 0.5;''', '''            let u = if b.t > a.t { ((t - a.t) / (b.t - a.t)).clamp(0.0, 1.0) } else { 0.0 };
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
            let mid = parts[6].translation;   // get-ups: the right foot stays planted''')

sub('''struct OwnRig {''', '''impl Key {
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

struct OwnRig {''')

a = t[t.index("        let squat = Key { pitch: 40.0"):t.index("        let mut clips = vec![rig.clip(\"get_up_fast\", &front")]
b = '''        // From his front: head and chest come up on the hands, back onto hands and knees, the left foot is brought
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
'''
t = t.replace(a, b)
wr(p, t)
print("done")
