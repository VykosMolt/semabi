Disposition: hold native execution until the following small source/plan
corrections are reviewed. No blocker was found in the supplied 2×2 construction
or the CURRENT/DIAGNOSTIC causal comparison.

1. `freeze.py` currently puts `taskset` and the frozen environment only inside
   the runner's child command. The outer `run_job.py` interpreter therefore
   starts without the promised CPU, hash seed, six thread limits or bytecode
   environment. Wrap the complete outer Python invocation with the same
   `taskset`/`env` prefix, retaining the child wrapper. Record both exact argv
   arrays and preserve the owned runner's launch/reap evidence.
2. `command_plan_v1.md` requires execution without a shell command string, but
   the available execution interface accepts a command string. Permit a safely
   quoted rendering of the exact recorded argv, for example `shlex.join`, with
   no added shell operations or substitutions. Retain both the literal argv
   and exact submitted string. This needs no new launcher framework.
3. Before the first native import, explicitly record and reject any existing
   `sys.modules` key equal to `semabi` or starting with `semabi.`. The current
   post-import origin hashes do not establish that native modules were absent
   at entry. Add the check after the stdlib source/input/runtime gates and
   before `run_native` imports. This finding was independently supplied by root
   and is confirmed by the import order in the reviewed source.
4. Change `pack`'s “lossless JSON” description to deterministic encoding of this
   known diagnostic schema. It converts tuples and sets to arrays and omits
   dataclass `parsed` fields; parsed associations are recorded separately.
   This is a reporting-precision correction, not a requested serialization
   redesign.

The first two findings are the launcher issues root identified before this
review. Item three and the wording correction consolidate root's parallel
source review. Only those bounded corrections are requested; no native policy,
invented input, objective arithmetic or full test suite change is required.

The instrument constructs real native observations, graph-derived unit templates
and parsed units, derives slot statistics, supplies the declared calibration key,
and calls the actual persistence method. PROMOTED selects two unambiguous
same-key retained-widget pairs; TRANSIENT selects two same-key changed-widget
pairs from the identical graph. NONE withholds the key only after that native
promotion attempt. `_build_entity_types`, `V4Abstractor`, the native tracker,
`diff`, `objective.evaluate` and `Behaviour.better_than` remain real calls.
The in-memory `EvidenceLog` construction matches its native analysis-view
pattern and contains exactly the scored select Step; calibration Steps are
retained separately.

All eight A/H/G/log instances are freshly constructed and kept alive. The raw
evidence hashes must agree across conditions; candidate, state and delta
fingerprints must agree across each condition's two arms. The diagnostic
predicate preserves the original non-widget calculation and adds raw widget
state only through a parsed owner's actually promoted slot. It changes only
the objective module's imported predicate, with exact restoration in both the
per-row and enclosing `finally` blocks. Actual `Behaviour` fields, per-step
verdicts, observable delta signatures, deltas and pairwise native comparisons
are recorded. Predictions are read only for comparisons after native results
are recorded; they are not assigned to observed result fields. Failed controls
and exceptions retain their own rows and prevent a PASS disposition.

The freezer's explicit reviewed hashes, current commit gate, complete native
and tracked-test Python inventories, exclusive output identities, Python
executable pin, and child pre/postflight checks are otherwise appropriate for
this bounded invented instrument. Hashing tests is custody, not a test run.
Root's later preservation must still bind final report bytes, the final process
record and exact launch/reap receipts; the diagnostic cannot seal those itself.

This is a source-only review. No freezer, diagnostic, native function, Fit,
query or application was executed, and no implementation was edited. Expected
score changes remain hypotheses until the authorized native run. A supported
W2 result would isolate how this candidate-dependent predicate treats an already
represented widget delta; it would not earn J1 identity, natural persistence,
field attachment, endpoint references or receiver naming.

Reviewed initial SHA-256 values:

- `contract_v1.md`: `66b7308e3a4da5efb45be7dd821949b3784dac9b855cc6a506bb32f4d0ac01d3`
- `diagnostic.py`: `9a9d5159d46cd4da805090ea8ea8695160ca486ae9f4f2ae77267f83f7da378f`
- `freeze.py`: `ac544fc5a737be8a23f91e8169449a6522977c9c20d5086af7cc970ef29b9e60`
- `invented_inputs_v1.json`: `6a78e73ec7459cc88217c2a1a3f3fb894b077347e59d0ad0042c9afbafd34fb6`
- `command_plan_v1.md`: `b2cc265b204cc074992845d4b1a809e5f3b486af4508cff9b8df966bf1618af6`
