"""Is the frozen model invariant under a consistent renaming of the values that only identify?

A name that functions as identity should carry no meaning in its spelling: behaviour should
be unchanged if every key value were spelled differently but consistently. Fits a model,
renames every key value the model reads on a second history's pages, and compares verdicts
before and after. A verdict that changes is a place where the model read the spelling.

``fresh`` renames every key to one the fitting corpus never saw (open-world: a new seed).
``permute`` cycles keys of the same type among themselves (closed-world: any difference means
a name was treated as a word).
"""
from __future__ import annotations

import argparse
import json
import random
import re
import shutil
from collections import Counter
from dataclasses import replace
from pathlib import Path

from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v2.graph import TOKEN_RE
from semabi.compiler.v4 import consequence as csq
from semabi.compiler.v4 import outcome as oc

FRESH = "fresh"
PERMUTE = "permute"


def _shape(text: str) -> str:
    return "".join("N" if t[0].isdigit() else "a" if t[0].isalnum() else "p"
                   for t in TOKEN_RE.findall(text))


def _keys_on(A, log) -> dict[int, set[str]]:
    """Every key value of every type the frozen model reads on this history's pages."""
    out: dict[int, set[str]] = {}
    for sig in list(log.observations):
        state = A.abstract(log.obs(sig))
        for (tid, key), obj in state.objs.items():
            if not key or not isinstance(key, str):
                continue
            if "|" in key or re.match(r"T\d+:", key) or key.endswith(("#2", "#3")):
                continue      # composite and link keys are made of other keys
            if key[0].isdigit():
                continue      # a number is an amount as often as a name; left alone
            out.setdefault(tid, set()).add(key)
    return out


def _fresh_token(token: str, rng: random.Random, taken: set[str]) -> str:
    consonants, vowels = "bdfgklmnprstvz", "aeiou"
    for _ in range(1000):
        chars = []
        for k, c in enumerate(token):
            if c.isdigit():
                chars.append(str(rng.randrange(10)))
            elif c.isalpha():
                pool = vowels if k % 2 else consonants
                ch = rng.choice(pool)
                chars.append(ch.upper() if c.isupper() else ch)
            else:
                chars.append(c)
        out = "".join(chars)
        if out not in taken and out != token:
            taken.add(out)
            return out
    raise RuntimeError(f"no fresh name for {token!r}")


def renaming(keys: dict[int, set[str]], mode: str, seen: set[str], seed: int) -> dict[str, str]:
    """Key value -> its new spelling. Injective; longest keys are applied first."""
    rng = random.Random(seed)
    out: dict[str, str] = {}
    if mode == FRESH:
        taken = set(seen)
        token_map: dict[str, str] = {}
        for tid in sorted(keys):
            for key in sorted(keys[tid]):
                parts = []
                for t in TOKEN_RE.findall(key):
                    if not t[0].isalnum() or t[0].isdigit():
                        parts.append(t)      # punctuation, and numbers: a `12` is not a name
                        continue
                    if t not in token_map:
                        token_map[t] = _fresh_token(t, rng, taken)
                    parts.append(token_map[t])
                out[key] = _rejoin(key, parts)
        return out
    if mode == PERMUTE:
        # Only keys that contain no other key are permuted as strings; a key that mentions
        # another follows the renaming of the key it mentions, to stay consistent.
        every = {k for ks in keys.values() for k in ks}
        pat = {k: re.compile(r"(?<![A-Za-z0-9])" + re.escape(k) + r"(?![A-Za-z0-9])")
               for k in every}
        atomic = {k for k in every if not any(o != k and pat[o].search(k) for o in every)}
        for tid in sorted(keys):
            by_shape: dict[str, list[str]] = {}
            for key in sorted(keys[tid]):
                if key in atomic and key not in out:
                    by_shape.setdefault(_shape(key), []).append(key)
            for group in by_shape.values():
                if len(group) < 2:
                    continue
                rng.shuffle(group)
                for a, b in zip(group, group[1:] + group[:1]):
                    out[a] = b
        return out
    raise ValueError(mode)


def _rejoin(original: str, parts: list[str]) -> str:
    """Put the renamed tokens back with the original's spacing."""
    out, pos = [], 0
    for m, part in zip(TOKEN_RE.finditer(original), parts):
        out.append(original[pos:m.start()])
        out.append(part)
        pos = m.end()
    out.append(original[pos:])
    return "".join(out)


def _substituter(mapping: dict[str, str]):
    if not mapping:
        return lambda s: s
    keys = sorted(mapping, key=len, reverse=True)
    pattern = re.compile(r"(?<![A-Za-z0-9])(" + "|".join(re.escape(k) for k in keys)
                         + r")(?![A-Za-z0-9])")
    return lambda s: pattern.sub(lambda m: mapping[m.group(1)], s) if s else s


def _declaration_nodes(nodes: list[dict]) -> set[int]:
    """Cells of each table's first row: the interface's declarations, not values.

    A renamed column header is a changed grammar: the parse names columns by it, and
    every row under it would stop instantiating. A token that identifies is renamed
    where it identifies, and left alone where the interface declares it."""
    children: dict[int, list[int]] = {}
    role = {n["i"]: n["role"] for n in nodes}
    parent = {n["i"]: n["parent"] for n in nodes}
    for n in nodes:
        children.setdefault(n["parent"], []).append(n["i"])
    out: set[int] = set()
    for table in (n["i"] for n in nodes if n["role"] == "table"):
        rows = []
        stack = [table]
        while stack:
            x = stack.pop()
            for c in children.get(x, ()):
                if role.get(c) == "row":
                    rows.append(c)
                stack.append(c)
        if not rows:
            continue
        first = min(rows)
        stack = [first]
        while stack:
            x = stack.pop()
            out.add(x)
            stack.extend(children.get(x, ()))
    return out


def rename_run(src: Path, dst: Path, mapping: dict[str, str]) -> None:
    """A copy of a run with every text renamed: pages, actions, typed values.

    Except the declarations; see `_declaration_nodes`."""
    sub = _substituter(mapping)
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for f in src.iterdir():
        if f.name not in ("observations.jsonl", "steps.jsonl") and f.is_file():
            shutil.copy(f, dst / f.name)
    with (src / "observations.jsonl").open() as fin, (dst / "observations.jsonl").open("w") as fout:
        for line in fin:
            d = json.loads(line)
            declared = _declaration_nodes(d["obs"]["nodes"])
            for n in d["obs"]["nodes"]:
                if n["i"] in declared:
                    continue
                for k in ("name", "value", "placeholder"):
                    if isinstance(n.get(k), str):
                        n[k] = sub(n[k])
                if n.get("options"):
                    n["options"] = [sub(o) for o in n["options"]]
            fout.write(json.dumps(d) + "\n")
    with (src / "steps.jsonl").open() as fin, (dst / "steps.jsonl").open("w") as fout:
        for line in fin:
            d = json.loads(line)
            act = d.get("action") or {}
            for k in ("text", "value", "option"):
                if isinstance(act.get(k), str):
                    act[k] = sub(act[k])
            desc = act.get("target_desc") or {}
            if isinstance(desc.get("name"), str):
                desc["name"] = sub(desc["name"])
            if d.get("typed_tokens"):
                d["typed_tokens"] = [sub(t) for t in d["typed_tokens"]]
            fout.write(json.dumps(d) + "\n")


def _verdicts(model, log) -> list[dict]:
    m = replace(model, log=log, cut=0)
    out = []
    for step in log.steps:
        if step.action.kind != "click" or step.action.target is None:
            continue
        vs = oc.score_step_admissible(m, step, corroborated=True, hypothesis=oc.RULE)
        ls = oc.score_step(m, step)
        out.append({"step": step.step, "control": vs.get("control"),
                    "verdict": vs["verdict"], "admissible": vs.get("admissible"),
                    "observed": vs.get("observed"), "list": ls["verdict"],
                    "predicted": ls.get("predicted")})
    return out


def _ledger(model, log) -> dict[int, list]:
    """The durable-effect layer's verdicts at every held-out step, by the rule that made
    them. A rule whose precondition names a spelling fires differently once renamed, and
    this is where it shows."""
    m = replace(model, log=log, cut=0)
    out: dict[int, list] = {}
    for p in csq.score(m).predictions:
        out.setdefault(p.step, []).append((p.operator, p.kind, str(p.slot), p.verdict))
    return {k: sorted(v) for k, v in out.items()}


def compare(run_dir: Path, chain: Path, reading_name: str, score_on: Path, *,
            mode: str = FRESH, seed: int = 0, split: float = 1.0,
            workdir: Path | None = None) -> dict:
    from semabi.eval.v4_consequence_run import _candidates

    readings = {c.name: c.reading for c in _candidates(chain)}
    model = csq.fit(Path(run_dir), readings[reading_name], split=split)
    A = model.abstractor
    log = EvidenceLog(Path(score_on))
    keys = _keys_on(A, log)
    seen = set(A.G._seen)
    for sig in log.observations:
        for n in log.obs(sig).nodes:
            seen.update(TOKEN_RE.findall(n.name or ""))
            seen.update(TOKEN_RE.findall(n.value or ""))
    mapping = renaming(keys, mode, seen, seed)
    workdir = Path(workdir or (Path(score_on).parent / f"{Path(score_on).name}_renamed_{mode}"))
    rename_run(Path(score_on), workdir, mapping)
    renamed = EvidenceLog(workdir)

    before = _verdicts(model, log)
    after = _verdicts(model, renamed)
    ledger_before, ledger_after = _ledger(model, log), _ledger(model, renamed)
    ledger_diffs = [{"step": k, "before": ledger_before.get(k, []), "after": ledger_after.get(k, [])}
                    for k in sorted(set(ledger_before) | set(ledger_after))
                    if ledger_before.get(k) != ledger_after.get(k)]
    assert [b["step"] for b in before] == [a["step"] for a in after]
    sub = _substituter(mapping)
    same = Counter()
    diffs = []
    for b, a in zip(before, after):
        control_same = b["control"] == a["control"]
        space_same = b["verdict"] == a["verdict"] and b["admissible"] == a["admissible"]
        list_same = b["list"] == a["list"] and b["predicted"] == a["predicted"]
        same["controls"] += control_same
        same["version space"] += space_same
        same["decision list"] += list_same
        if not (control_same and space_same and list_same):
            diffs.append({"step": b["step"], "control": (b["control"], a["control"]),
                          "verdict": (b["verdict"], a["verdict"]),
                          "admissible": (b["admissible"], a["admissible"]),
                          "list": (b["list"], a["list"]),
                          "observed": (b["observed"], a["observed"])})
    return {"run": Path(run_dir).name, "reading": reading_name, "scored_on": Path(score_on).name,
            "mode": mode, "seed": seed, "keys_renamed": sum(len(v) for v in keys.values()),
            "types": {str(t): len(v) for t, v in keys.items()},
            "sample": dict(list(mapping.items())[:12]),
            "clicks": len(before), "same": dict(same),
            "verdicts_before": dict(Counter(b["verdict"] for b in before)),
            "verdicts_after": dict(Counter(a["verdict"] for a in after)),
            "differences": diffs[:80], "n_differences": len(diffs),
            "ledger_steps": len(set(ledger_before) | set(ledger_after)),
            "ledger_same": len(set(ledger_before) | set(ledger_after)) - len(ledger_diffs),
            "ledger_differences": ledger_diffs[:40], "n_ledger_differences": len(ledger_diffs)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--chain", required=True)
    ap.add_argument("--reading", required=True)
    ap.add_argument("--score-on", required=True)
    ap.add_argument("--mode", default=FRESH, choices=(FRESH, PERMUTE))
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--split", type=float, default=1.0)
    ap.add_argument("--workdir", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    r = compare(Path(a.run), Path(a.chain), a.reading, Path(a.score_on), mode=a.mode,
                seed=a.seed, split=a.split, workdir=Path(a.workdir) if a.workdir else None)
    print(f"\n{r['run']}  {r['reading']!r}  scored on {r['scored_on']}  renamed {r['mode']}")
    print(f"  {r['keys_renamed']} keys renamed over types {r['types']}")
    for k, v in r["sample"].items():
        print(f"    {k!r} -> {v!r}")
    print(f"  {r['clicks']} clicks; identical: {r['same']}")
    print(f"  version space before: {r['verdicts_before']}")
    print(f"  version space after:  {r['verdicts_after']}")
    for d in r["differences"][:20]:
        print(f"    step {d['step']}: control {d['control']}  verdict {d['verdict']}  "
              f"admissible {d['admissible']}  list {d['list']}")
    print(f"  durable ledger: {r['ledger_same']} of {r['ledger_steps']} steps identical, "
          f"{r['n_ledger_differences']} differ")
    for d in r["ledger_differences"][:12]:
        print(f"    step {d['step']}: {[x for x in d['before'] if x not in d['after']]}  ->  "
              f"{[x for x in d['after'] if x not in d['before']]}")
    if a.out:
        Path(a.out).write_text(json.dumps(r, indent=1, default=str))
        print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
