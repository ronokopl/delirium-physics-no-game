# One-off: adds the stand-in clips (tools/notes/own_clips.rs.txt) to the room's getup.rs and wires them in.
import io
def rd(p): return io.open(p, encoding="utf-8", newline="").read()
def wr(p, t): io.open(p, "w", encoding="utf-8", newline="").write(t)

p = "crates/delirium-room/src/getup.rs"; t = rd(p)
if "fn own(build" not in t:
    wr(p, t + rd("tools/notes/own_clips.rs.txt"))

p = "crates/delirium/src/ragdoll.rs"; t = rd(p)
a = "    pub fn place(&self, pose: &[(Vec3, Quat)], body: Transform) -> Vec<Transform> {\n        let bones = pose_frames(&self.parents, pose, body);\n        self.build.parts.iter().map(|d| {"
a = a if a in t else a.replace("\n", "\r\n")
assert t.count(a) == 1
b = ("    /// MODIFIED (not in the original): a rig for a build that is its own skeleton (one bone per part, `bone` its index\n"
     "    /// and `offset` the part from its bone), for the stand-in clips with no game.\n"
     "    pub fn own(build: Build, parents: Vec<Option<usize>>) -> Rig {\n"
     "        let part_of = (0..build.parts.len()).map(Some).collect();\n"
     "        Rig { build, part_of, parents }\n"
     "    }\n\n")
if "pub fn own(build: Build" not in t:
    wr(p, t.replace(a, b + a))

p = "crates/delirium-room/src/main.rs"; t = rd(p)
a = "            (b, f, None)"
if "Clips::own(&b, &f)" not in t:
    assert t.count(a) == 1
    b = ("            // MODIFIED (not in the original): our own stand-in clips (get-up, idle, walk, run, sprint, gun, punch) where there were none\n"
         "            let clips = getup::Clips::own(&b, &f);\n"
         "            (b, f, Some(clips))")
    wr(p, t.replace(a, b))
print("done")
