# Makes get-up motions with NVIDIA's Kimodo and turns them into clips the no-game Playroom can try. NOT part of the original.
# Needs: Kimodo installed at E:/AI/claude/assets/kimodo (see docs/no-game.md) and a Hugging Face login that has been
# given access to meta-llama/Meta-Llama-3-8B-Instruct (Kimodo's text model; about 16 GB, downloaded on first use).
# usage: python tools/kimodo_getups.py [front|back|both] [--samples 4] [--seed 1] [--seconds 5] [--hf-home <folder for the downloads>]
# Writes run/kimodo/<front|back>/..._NN.npz and ..._NN.txt. Try one in the Playroom without rebuilding:
#   set DELIRIUM_GETUP_FRONT=run/kimodo/front/front_00.txt   (or DELIRIUM_GETUP_BACK)
# Keep one by copying it over crates/delirium-room/src/getup-front-kimodo.txt (or -back-) and rebuilding.
import glob, os, subprocess, sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
kimodo = os.environ.get("KIMODO", "E:/AI/claude/assets/kimodo")
a = sys.argv[1:]
def opt(name, default):
    if name in a:
        i = a.index(name); v = a[i + 1]; del a[i:i + 2]; return v
    return default
samples, seed, seconds, hf = opt("--samples", "4"), opt("--seed", "1"), opt("--seconds", "5"), opt("--hf-home", "")
which = a[0] if a else "both"
PROMPTS = {"front": "A person is lying face down on the floor, then pushes up with their hands, gets up and stands still.",
           "back": "A person is lying on their back on the floor, then sits up, gets up and stands still."}
env = dict(os.environ, TEXT_ENCODER_MODE="local", TEXT_ENCODER_DEVICE="cpu")   # the text model on the CPU: it does not fit in 8 GB of video memory
if hf: env["HF_HUB_CACHE"] = hf   # only the model files; the login stays where it is
scripts = os.path.join(kimodo, ".venv", "Scripts")
for side in (["front", "back"] if which == "both" else [which]):
    d = os.path.join(root, "run", "kimodo", side); os.makedirs(d, exist_ok=True)
    r = subprocess.run([os.path.join(scripts, "kimodo_gen.exe"), PROMPTS[side], "--duration", seconds, "--num_samples", samples, "--seed", seed,
                        "--output", os.path.join(d, side)], env=env, cwd=kimodo)
    if r.returncode: sys.exit(f"Kimodo failed for {side} (exit {r.returncode})")
    for npz in sorted(glob.glob(os.path.join(d, "**", "*.npz"), recursive=True)):
        subprocess.run([os.path.join(scripts, "python.exe"), os.path.join(root, "tools", "kimodo_to_clip.py"), npz, npz[:-4] + ".txt",
                        "--note", f"Kimodo prompt: {PROMPTS[side]} seed {seed}"], env=env, check=True)
