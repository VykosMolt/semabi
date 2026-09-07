Chronology normalization audit, 2026-09-07. Development diagnostic, before G1.

Changing only a future outcome changes the page representation supplied to an
already delimited prefix model. A five-node synthetic page gains two section
containers under both `FROZEN_PREFIX` and `CAUSAL_PREQUENTIAL`. This establishes
operative representation leakage. The minimal witness learns zero entity types
and zero operators in either branch; it does **not** establish a learned-rule or
task-score change.

The executable diagnostic is [audit.py](audit.py), with retained output in
[results_before_g1.json](results_before_g1.json). It reads compiler code and
generates its own temporary evidence logs. It reads no application source,
transport fixture, oracle, reserved case, or retained evaluation outcome. No
learner or test source was changed. The diagnostic uses one process and pins
numerical libraries to one thread.

Run from `/home/moloch/semabi`:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=0 PYTHONPATH=. .venv/bin/python docs/data/v4/transport/development/chronology_audit/audit.py --output /tmp/semabi-chronology-audit-results.json
```

The retained run passed every assertion, including eight actual
`consequence.fit` calls for the chronology witness and two actual fits for the
independent runtime witness. Initial execution without `PYTHONPATH=.` failed at
import before any experiment; the command above is the corrected, executed
command, with a disposable output destination.

The chronological path is:

1. `consequence.fit`, lines 714–719, loads the whole log and chooses
   `through(cut)` or `before_action(cut)` as the allowed view.
2. Line 725 calls `_normalise_sections(full, stats_from=slice_at(cut))` **before**
   the compile view is sliced. The intended reason is to remap every step
   signature consistently when sections add containers.
3. `compile_v4._normalise_sections`, lines 45–50, creates an `ObsGraph`, adds
   allowed observations, then adds every remaining observation. The graph's
   default `learning` is `True`, and nothing changes it between those loops.
   The comment “contributing no statistics” does not describe execution.
4. `ObsGraph.add` consequently updates variation templates, observed vocabulary,
   and other corpus statistics for the future page. `sections.candidates` uses
   these statistics in `collapsed_template` and span fillings.
5. The helper normalizes all pages using that probe and remaps all `before` and
   `after` signatures. `fit` then slices the already transformed prefix. A later
   `build_hypotheses` normalization pass does not undo appended containers.
6. Only after compilation, at `consequence.fit` line 732, does `A.freeze()` stop
   the fitted graph from learning. That cannot undo the earlier representation
   decision.

The exact minimal pages are:

| Index | Parent | Role | P text | Q text |
| --- | --- | --- | --- | --- |
| 0 | -1 | group | empty | empty |
| 1 | 0 | heading | Alpha | Delta |
| 2 | 0 | button | Go | Go |
| 3 | 0 | heading | Beta Gamma | Epsilon Zeta |
| 4 | 0 | button | Go | Go |

Both logs contain two successful clicks on index 2, with the same episode,
action descriptor and typed-token list. Step 0 is `P → P` in both. Step 1 is
`P → P` in the baseline and `P → Q` in the variant. At cut 1 the complete raw
prefix and the complete raw pre-action frontier are byte-for-byte equivalent
under canonical JSON. Only the outcome of the action being predicted differs.

P's two heading strings initially occupy separate token-pattern templates:
one word and two words. Neither template varies, so their words are labels and
the two heading/button spans have different templates. Q supplies a second
string for each token pattern. All six heading words then become data. P's
headings both collapse to `heading[_]`, producing the two accepted spans
`[1, 2]` and `[3, 4]`. This is a concrete use of future evidence in an earlier
object-boundary decision.

| Actual fit at cut 1 | Baseline prefix | Changed-future prefix |
| --- | --- | --- |
| `FROZEN_PREFIX`, current helper | 5 nodes, `449a49ca0ec5f6c7` | 7 nodes, `547fdeee25e0bb29` |
| `CAUSAL_PREQUENTIAL`, current helper | 5 nodes, `449a49ca0ec5f6c7` | 7 nodes, `547fdeee25e0bb29` |
| Either regime, frozen-probe control | 5 nodes, `449a49ca0ec5f6c7` | 5 nodes, `449a49ca0ec5f6c7` |

In the seven-node page, parents become `[-1, 5, 5, 6, 6, 0, 0]`.
Original indices 0–4 retain their full `Node.key()` values; click target 2 is
still the same `Go` button. The suffix also changes: raw Q has signature
`53baf924978d00c4`, while the current helper's normalized Q has signature
`4c1dcb3b961676e7`. Every observation dictionary key equals the corresponding
structural signature, and every step reference resolves in all tested branches.
No dangling-signature failure was demonstrated here. The leak operates through
validly remapped representations, not a stale pointer.

The smallest supported chronology repair is to set `probe.learning = False`
immediately after adding `source.observations` and before adding other
observations. The diagnostic creates exactly this one-line variant in memory
using the helper's inspected source. It does not patch a production file. This
control removes the prefix dependence in both actual fit regimes. It also
preserves the exact whole-log normalized observations and steps when
`stats_from=None`, for both synthetic logs. This establishes the required
all-evidence behavior on these cases, not a general equivalence proof. A focused
regression belongs in an existing chronology or sections test file.

A separate runtime witness establishes that fixing the probe alone does not
make live and offline parsing equivalent. Its prefix page consists of two flat
spans, each `heading Item / text number / button Go`, with numbers `1` and `2`.
The future page substitutes `3` and `4`. A pinned reading is constructed solely
from the prefix hypothesis, with family
`group[_](heading[_],text[_],button[_])` keyed by `text#0`.

| Same future page, same frozen model | Nodes | Objects |
| --- | --- | --- |
| Offline page returned in `Fit.log` | 9 | `(0, '3')`, `(0, '4')` |
| Raw page passed to `A.ensure` / `A.abstract` | 7 | none |

The offline signature is `1215d243d030caaa`; the raw signature remains
`a45ea27fb78776a2`. `A.G is A.H.G` is true throughout this witness. Frozen graph
corpus statistics are unchanged by the runtime reads. The discrepancy remains
under the frozen-probe control. This is therefore independent of both the
chronology leak and G1 graph ownership.

The relevant runtime source is `V2Abstractor.ensure`, lines 240–245: it hashes
and adds the received page directly, then calls emissions learning, which is a
no-op after freeze. `V4Abstractor` does not override it. No section normalization
occurs. Offline fitting, by contrast, passes the normalized suffix stored in
`Fit.log` to scoring.

An appropriate separate runtime repair would retain a per-model normalizer
fitted only on the allowed **raw** observations and use that same frozen
normalizer at offline and live observation boundaries. The normalized graph
used for units is not automatically an equivalent normalizer: inserted groups
change role paths and indexed positions even though they add no text. The raw
probe should therefore have explicit model ownership and a frozen lifetime,
with future pages admitted only for per-observation descriptors.

Keep raw observations immutable and their original signatures intact. A
derived canonical observation should receive its own recomputed signature and
a per-model raw-to-canonical mapping. Appending groups preserves every raw
action/feature index. All structural readers and caches must receive the same
canonical observation for that canonical signature, including parsing,
control-family assignment, completeness, grounding, and correspondence when
it traverses synthesized spans. Raw text checks at original indices retain
their original evidence coordinates. Synthetic roots must never be indexed
into the shorter raw node array. Merely normalizing inside `ensure` is
insufficient: `parsed` currently passes its original `obs` to `_parse`,
`control_family` passes it to `controls.assign`, and `complete_types`
recomputes its signature directly. This is a bounded design direction and
acceptance requirement, not an implemented or fully verified repair.

The next chronology change can be limited to the one-line probe freeze and a
regression covering both regime cuts, stable original node indices, consistent
signature remapping, and unchanged all-evidence normalization. Treat runtime
normalization parity as a separate change with the numbered-page witness as an
acceptance case. Neither finding justifies changing G1, entity selection,
operator learning, or frozen T1 results.

The retained JSON records SHA-256 hashes of all ten relevant source files at
the start and end of the run; these were identical. Key pre-G1 hashes are:

| Source | SHA-256 |
| --- | --- |
| `semabi/compiler/compile_v4.py` | `670b8dfefcd729d3ee971d5fdf97c2e595d360f47fd06678579b565844814ef3` |
| `semabi/compiler/v4/search.py` | `76da44ce22accd7498e728f5efd7fbf899659feb6e63b7e5dbfe785637d4bdec` |
| `semabi/compiler/v4/consequence.py` | `158551f35160a79d9c165c767486b63579564dccc3e99febf45d4d714ef0791b` |
| `semabi/compiler/v2/graph.py` | `f601fb6bd56d8728a01fdc404c6a0d80636cb2ccba98dab09cd26abf5c425b2a` |
| `semabi/compiler/v2/sections.py` | `4bd39bf7e067a94ec19f6ad6c23c098d13ac01efdabafe2f6e15eb213003ba02` |

The inspected `_normalise_sections` function alone hashes to
`9b806ec69d75dad61ea9599cca038c804a5b357e9a8858a9f1bc0139fffdf981`.
This report intentionally retains the pre-G1 run and makes no post-G1 execution
claim. The source audit found no reason for the two G1 construction-line edits
to affect either mechanism, but that is source reasoning rather than a rerun.
