Independent source review of [join_design_v1.md](../join_design_v1.md), 2026-09-07.
Prepared micro-control only; no JOIN execution or capability result is claimed.

The design correctly separates native conjunctive semantics, representation,
variable/query production, and learning. The eight-object example is a suitable
small discriminator for supplied-state semantics. Its G/N/D tables preserve
two incident bridges per source and per target while producing zero, one, or
two common witnesses. The proposed micro-control is **O-REP plus oracle
formula**; it does not instantiate the design's inferred-state rung 1, because
there are no inferred states or raw-visible mapping checks in this control.

Source reviewed is main-checkout G1 at
`5ac0e11852dde513f4beb4e4ab1fbec0bc2318aa`. The relevant facts are:

| Boundary | Source finding | Interpretation |
| --- | --- | --- |
| Formula evaluation | `binding.holds`, lines 166–218, compares native typed reference targets. `solve`, lines 236–332, enumerates typed unsupplied parameters and checks all supplied literals together. | A supplied shared m can express the conjunction. All four candidate m assignments must be retained to distinguish a real join from two independent nonemptiness checks. |
| Assignment versus target | `Bindings.denotations` and `effect_target`, lines 120–151, project onto selected effect parameters. | Two m assignments may agree on z. Assignment ambiguity and target determinacy are different results. The script records both, including typed identities. |
| Normal variable production | `Inducer.lift`, lines 734–927, introduces objects reached through action owners/arguments, effects, and emitted arguments. `_literals`, lines 1348–1395, relates objects already in `tr.binding`. | The binder's ability to range over a supplied m does not establish that ordinary lifting introduces a precondition-only m. Adding m to a hand-authored operator would assume that missing step. |
| Referring queries | `referring.ground`, lines 420–506, searches effect, output, and enabling variables. `_relation_queries`, lines 201–229, proposes individual edges; `_resolves`, lines 232–252, requires one intended object on each positive. | Already wanted intermediates can form unique chains. An otherwise precondition-only witness is not added to `wanted`. No existing query form intersects two plural inverse denotations. `Grounding.witnesses`/`roles()` also do not explicitly distinguish enabling variables, so a future diagnostic must retain the caller's enabling set separately. |
| Outcome roles | `Role.denotation` evaluates one edge and `ControlOutcome.bind` accepts singleton denotations. `_canon` recursively names query anchors with a depth bound. | Grounding a short unique chain is not a claim about plural-intermediate outcome roles or outcome-model learning. |
| Export | `model._lit` exports a supported ref conjunction. `relmodel.unique_binding` requires one complete assignment. | Multi-witness agreement in the V4 binder does not establish that an exported planner will execute the action. No exported-planner result is planned. |

The forward-chain control uses the real `OperatorHyp`, `EffT`, `AbsObj`, and
`AbstractState` types. Two supplied before/after pairs change flags on m and z;
native `diff` records those changes. Real `referring.ground` receives those
effect bindings with x as its only action-bound variable. The native query
evaluator then resolves m and z from x alone. Both types have two visible
alternatives, and the pass criterion requires forward-relation queries.
The property callback is permissive and disclosed. This is query production
under supplied representation and supervision, not normal operator learning.
No formula is provided to `ground`; a separate oracle formula scores its
returned bindings afterwards.

The normal-role-production diagnostic is deferred. A fabricated operator with
only x/z would mechanically omit m; a fabricated operator with m would supply
the disputed witness. Neither establishes what the actual observation-to-
transition pipeline produces. A later raw-trace diagnostic should retain the
actual lifted `Transition.binding`, operator parameters/effects, enabling set,
grounding basis, query forms, and outcome roles before classifying that boundary.

The O-ID seam is correctly placed before `objs[(tid,key)]` admission/merging,
but that placement cannot recover every earlier loss. In `_parse`, lines
407–468, templates without an entity-type assignment are skipped; identity is
computed before object admission; attributes/reference slots are already
assembled; reference slots are named by target type (`rel:{tid}`), and multiple
source slots feeding that same target type can overwrite each other. A token
remap at `abstract`, lines 598–674, cannot split a merged type, restore a lost
slot, or recover a visible association whose provenance was discarded earlier.

Before implementing O-ID, freeze these eligibility details:

1. Distinguish wrong nonempty identity keys/collisions from empty-id instances
   excluded by `abstract`. State explicitly whether admitting an empty-id
   instance is permitted identity assistance or separately classified object
   admission assistance; it must not be hidden inside a collision count.
2. Retain an independently audited mapping from each existing identity/reference
   slot to its raw mention. A resolved `None` must be distinguished from a
   visible recognized reference that failed association and from an absent or
   unrecognized slot. Repairing the last category exceeds O-ID.
3. Preserve inferred types and reference-slot inventory. Two endpoint roles
   already collapsed into one slot, or endpoints merged into one type, remain
   representation failures in the matched arms.
4. Keep parsed identity values, admitted object keys, typed references, owner
   recovery, and selection values consistent while preserving raw pointers.
   `Query.denotation` uses `startswith`, so canonical identity tokens must not
   become prefixes of one another. Preserve nonidentity selection suffixes and
   never rewrite outcome/status prose as a pre-state identity cue.
5. Replay the same intervention during fitting and scoring, retain its
   per-mention map, and disclose all ineligible cases in the planned denominator.
   A correct graph supplied directly remains O-REP, not successful O-ID.

No O-ID adapter is implemented here. These details limit what an eventual
matched intervention could establish; the semantic micro-result should precede
that larger diagnostic.

A separate source concern warrants the approved bounded-search reproduction.
In `binding.solve`, the local `truncated` flag can become true when enumeration
hits a limit, but the `len(out) == 1` return constructs `Bindings(UNIQUE, ...)`
without passing that flag. `effect_target` subsequently treats the result's
default false flag as complete. The prepared diagnostic supplies x0 alone in G:
the full space has `(m0,z0)` and `(m1,z1)`, then `limit=1` deliberately prevents
enumerating both. It records the exact native limited result and whether it
claims false assignment uniqueness or target determinacy. This is a source
prediction until execution. The 12 primary cases retain unchanged default
limits, and no binding implementation is repaired.

The micro-control directly consumes supplied states and calls binding/referring;
it does not normalize observations or fit across a chronological cut. The
parent therefore authorized it on frozen G1. The design's requirement to
integrate G2 still applies to a later full observation/learner trace.

Prepared files are `contract.md`, `contract.json`, `control.py`, this review,
and `freeze.json` with source snapshots. Only a syntax parse and JSON/file/hash
checks are permitted during preparation; no native diagnostic call has run.
The proposed command is:

```bash
.venv/bin/python -B docs/data/v4/transport/run_job.py docs/data/v4/transport/development/join_native_control/jobs/v1 -- .venv/bin/python -B docs/data/v4/transport/development/join_native_control/control.py --out docs/data/v4/transport/development/join_native_control/run_v1/result.json
```

Run from `/home/moloch/semabi` after root review. The runner provides one-thread
limits, a fixed Python hash seed, process provenance, and termination records.
The script preserves all results before returning a failed primary/positive-
control check, and reports the bounded-search defect independently.
