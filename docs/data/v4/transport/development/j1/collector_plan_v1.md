# J1 scoped collector adapter plan

Status: implemented for independent review; no browser collection or native fit
has run. This public plan contains generic instrument behavior and invented-data
checks only. Application identities, layout, cases and answers remain sealed.

`collect.py` reuses the retained collector's unchanged `Recorder`, `collect_script`
and `main`, and its normal Browser observation/settling path. During one script
invocation it temporarily replaces only that imported module's `resolve` function
and restores the original function in `finally`. The command-line argument list
is also restored. Acquisition mode is rejected before native modules load. There
is no replacement of Browser, EvidenceLog, fitting, freeze policy or normal
collection code in the production adapter.

An unscoped action delegates directly to the retained resolver, using the original
observation and action objects. A scoped targeted primitive has this syntax:

```json
{"kind":"click","role":"button","name":"<public control name>","exact":true,
 "scope":{"role":"group","name":"<public ancestor group name>","exact":true}}
```

Scoped `click`, `type` and `select` operations require the exact three-field scope
shown above and exact target role/name matching. The scope must identify exactly
one observed group, and the target must identify exactly one strict descendant
of that group. Partial names, extra scope keys, other scope roles, missing exact
flags and scoped global operations are rejected. There is no global, ordinal,
hidden-attribute or guessed-node fallback. Native observation visibility defines
the available nodes; this resolver does not provide a separate viewport audit.

The adapter validates integer node indices against their unchanged positions and
checks bounded parent references and cycles before following ancestry. It filters
the original node objects directly and preserves the original target index. It
does not create a subset Observation, renumber nodes, change parents, alter raw
fields or recover an owner using fixture metadata. A malformed parent graph
causes a failed attempted primitive. A group itself is not its own descendant.

Within those descendants, the retained `spinbutton` to `textbox` alias applies
only when no exact-role match exists. The ordinary successful-target precedence
is `value`, then `text`; an explicitly present empty value or `null` keeps the
retained behavior. On an unresolved target, the retained failure Primitive keeps
`value` only. The alias annotation and the scope-resolution diagnostics remain in
the evaluator's `requested` decision record. Successful Primitives contain the
normal kind, original raw node target and public text. Failed Primitives contain
only the normal control descriptor and public value. Scope, case and oracle data
are never added to a Primitive, observation or learner-visible error. A failed
scope uses one generic error string without its name or diagnostic details.

The existing Recorder receives every failed scoped resolution through its ordinary
`error` argument. It charges one attempt, records a failed paired Step against the
existing observation, and performs no guessed Browser action or extra observation.
The script continues using the retained behavior. Evaluator-side failure reasons
distinguish malformed scope/target/ancestry and missing or nonunique scope/control;
none of these failures may disappear from the planned denominator.

The new J1 instrument freeze must have a `verification_files` SHA-256 mapping
containing exactly these paths:

- `docs/data/v4/transport/development/j1/collect.py`
- `scripts/transport_collect.py` (including Recorder and the original resolver)
- `semabi/compiler/browser.py`
- `semabi/compiler/observation.py`
- `semabi/compiler/evidence.py`

The adapter authenticates every listed file and its own bytes before importing the
retained collector. It rechecks the same files and the entire manifest bytes after
invocation, including exceptional exits. Missing, extra, noncanonical or changed
paths and malformed hashes fail closed. The added section permits no application,
oracle or sealed evaluator payload. It does not change `base.verify_freeze`: the
ordinary `files` section remains subject to that exact retained runtime allowlist,
and `sealed_evaluator_files` remains unopened by that verifier.

For a newly created retained run, the adapter writes a separate
`collector_verification.json` with before/after hashes and any collection or
verification error. It preserves `run.json`. A post-run verification failure raises
and records `ERROR`; a caller must require exit code zero, the retained terminal
record and `collector_verification.json` status `PASS`, and must not infer source
validity from `run.json` alone. Script setup failures remain a separate measured
quantity even when source verification passes. A preflight rejection creates no
run, and rejection of an already existing output directory does not add a record
to that prior run. The future execution wrapper must check both records.

Planned invocation, with a new instrument freeze and unused run directory:

```text
taskset -c <assigned-cpu> python -B docs/data/v4/transport/development/j1/collect.py script --url <public-url> --reset-url <public-reset-url> --script <sealed-script-path> --fixture <split-key> --freeze <new-j1-instrument-freeze> --out <unused-run-directory> --seed <frozen-seed>
```

The actual job must use the separately reviewed experiment wrapper and granted
worker slot. This is planned syntax, not an executed browser command. The adapter
does not select a case, split, service profile, seed, learned model or budget.
Apply the parent's current resource allocation, hash seed zero and one numerical
thread per process. The user lifted the temporary one-core restriction during
adapter construction; the small synthetic check uses only CPU 12 at normal
priority. This plan does not revise any previously frozen fixture record or its
historical resource commands.

The planned per-split totals remain **UNMEASURED**: 313 charged actions, 312 paired
interactions and one unpaired reset, including the initial observed reload, all
public setup and every failed attempt. The real browser must establish complete
visibility, readiness, exact dispatch and those totals. Synthetic checks cannot
establish fixture reachability, native settle behavior or learner eligibility.

`review_evidence/collector_checks_v1.py` uses tiny invented public observations to
check repeated-label success, missing/ambiguous groups and controls, nested and
outside ancestry, malformed indices/cycles, exact-scope validation, alias precedence,
text/value precedence, raw-state preservation, evaluator metadata isolation,
unscoped delegation and restoration after errors. It also checks pre/post source
authentication and acquisition rejection. For a tiny accounting example, it
executes the unchanged retained function/class AST bodies with a fake Browser and
ordinary invented observations, avoiding SemABI/Playwright imports and native
fits. A fake Browser's behavior is not evidence about the real browser. The
separate result records identify source hashes, synthetic counts and these limits.
The first checker run stopped on an overly broad leakage assertion that excluded
an ordinary requested public control name when it matched a group name. The
production adapter bytes did not change. The original checker/plan bytes and
failed log are preserved; source-manifest/result version 2 uses the corrected
assertion over allowed Primitive fields and the requested control descriptor.
