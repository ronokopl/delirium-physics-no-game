# usage: python -I ctx.py <slot> [<slot> ...]   prints how a number slot is stored and every line that uses it
import json, sys, os
slots = {int(k): v for k, v in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "slots.json"))).items()}
for a in sys.argv[1:]:
    s = slots[int(a)]
    print(f"## slot {a} [{s['kind']}{' negated' if s['neg'] else ''}] {len(s['uses'])} uses" + (f"  KNOWN whole={s['whole']} f32={s['f32']!r}" if s["kind"] == "known" else ""))
    for rel, n, ty, ctx in s["uses"]: print(f"  {rel}:{n}: {ctx}")
