"""Reachability for the berth allocation: the dev compile's types, every operator whose
acts touch the Allocate button with its parameters and referring queries, and the
abstract state around the button's owner at each allocation step.

Usage: join_reach.py <run_dir> <out_json> [chain reading]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/moloch/semabi")


def obj_row(o):
    return {"id": str(o.id), "tid": o.tid, "key": o.key, "attrs": o.attrs,
            "refs": {k: str(v) for k, v in o.refs.items()}, "parent": str(o.parent)}


def main():
    run, out = Path(sys.argv[1]), Path(sys.argv[2])
    from semabi.compiler.v4 import outcome as oc
    from semabi.compiler.v4.consequence import clicked_control
    reading = None
    if len(sys.argv) > 3 and sys.argv[3] == "search":
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from link_probe import settled_reading
        from semabi.compiler.v4 import consequence as csq
        reading = settled_reading(run)
        c = csq.fit(run, reading, split=0.999)
    elif len(sys.argv) > 4:
        from semabi.compiler.v4 import consequence as csq
        from semabi.eval.v4_consequence_run import _candidates
        reading = {c.name: c.reading for c in _candidates(Path(sys.argv[3]))}[sys.argv[4]]
        c = csq.fit(run, reading, split=0.999)
    else:
        from semabi.compiler.compile_v4 import compile_v4
        c = compile_v4(run, min_support=2, write_diagnostics=False)
    A, log, ind = c.abstractor, c.log, c.inducer
    types = {tid: {k: str(v)[:100] for k, v in vars(ti).items()} for tid, ti in getattr(A, "types", {}).items()}
    ops = []
    for op in ind.operators:
        how = " ".join(str(a) for a in op.acts)
        if "Allocate berth" not in how:
            continue
        q = ind.queries.get(op.name) or {}
        ops.append({"name": op.name, "how": how[:200], "support": op.support,
                    "core": [str(a) for a in op.core()],
                    "params": {k: v for k, v in op.params.items()},
                    "queries": {v: {"kind": getattr(x, "kind", None), "form": str(getattr(x, "form", None)),
                                    "given": str(getattr(x, "given", None))} for v, x in q.items()},
                    "pre": [str(l) for l in getattr(op, "pre", [])][:8],
                    "effs": [str(e) for e in op.effs][:6]})
    steps = []
    for s in log.steps:
        if s.action.kind != "click" or s.action.target is None:
            continue
        obs = log.obs(s.before)
        try:
            control = clicked_control(A, obs, s)
        except Exception as e:
            control = f"error {e}"
        if control != "button:Allocate berth":
            continue
        after = log.obs(s.after)
        status = next((n.name for n in after.nodes if n.role == "status"), None)
        state = A.abstract(obs)
        owner = oc._owner(A, obs, s)
        po = A.parsed(obs)
        by_node = {o.node: o for o in state.objs.values()}
        chain = []
        idx = po.node_instance.get(s.action.target)
        while idx is not None:
            inst = po.instances[idx]
            chain.append({"tid": inst.tid, "root": inst.root, "root_is_object": inst.root in by_node,
                          "id_slot": str(inst.slots.get("id")),
                          "object_by_key": str(state.objs.get((inst.tid, (inst.slots.get("id") or (None, None))[1])) is not None),
                          "slots": {k: str(v)[:40] for k, v in list(inst.slots.items())[:6]}})
            idx = inst.parent
        near = {"instance_chain": chain}
        if owner is not None:
            near[str(owner.id)] = obj_row(owner)
            for slot, tgt in owner.refs.items():
                o2 = state.objs.get(tgt)
                if o2 is not None:
                    near[f"{slot}->{tgt}"] = obj_row(o2)
                    for slot2, tgt2 in o2.refs.items():
                        o3 = state.objs.get(tgt2)
                        if o3 is not None:
                            near[f"{slot}->{slot2}->{tgt2}"] = obj_row(o3)
            for o2 in state.objs.values():
                if o2.parent == owner.id:
                    near[f"child {o2.id}"] = obj_row(o2)
        view = getattr(state, "view", None) or {}
        steps.append({"step": s.step, "status": status, "owner": str(owner.id) if owner else None,
                      "near": near, "view": {k: str(v)[:80] for k, v in view.items()},
                      "types_present": sorted({o.tid for o in state.objs.values()})})
    rec = {"run": str(run), "reading": reading.to_json() if reading is not None else None,
           "types": types, "allocate_operators": ops, "allocate_steps": steps}
    out.write_text(json.dumps(rec, indent=1, default=str))
    print(json.dumps({"types": types, "operators": [(o["name"], o["support"], o["core"]) for o in ops]}, indent=1, default=str)[:6000])
    for st in steps[-3:]:
        print(st["step"], st["status"], "owner", st["owner"])
        for link in st["near"]["instance_chain"]:
            print("    ", link)


if __name__ == "__main__":
    main()
