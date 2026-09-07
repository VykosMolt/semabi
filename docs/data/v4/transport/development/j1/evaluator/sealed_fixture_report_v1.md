# J1 sealed generated-fixture construction report

Status: generated fixture prepared, with bounded model consistency checks passed.
This document contains held-out design and answer information and is evaluator-only
until first predictions and assessment are preserved. It is not a learned result.

The application has four transmitters, four receivers and eight visible patch
records. Each patch exposes one functional transmitter reference and one functional
receiver reference using ordinary labeled native selects. All source and target
alternatives remain in the document. Every source owns the same `Transmit` button;
each receiver owns a `Select receiver` radio and a visible `Received: yes/no` flag.
The primary handler supplies only the acted source name. The selected target comes
from the pre-state radio. No bridge parameter is sent by the primary click.

The implementation intersects the sets of bridge indices incident to the acted
source and selected target. The independent reference enumerates complete endpoint
pairs and selects those equal to the queried pair. Acceptance is nonempty
intersection, including two matching bridges. Success updates only the selected
receiver flag and emits `Transmission delivered: {source} → {target}.`; refusal
preserves every receiver flag and emits the corresponding blocked frame. Neither
frame names an intermediate. Model checks also premark the other three receivers
and confirm that those unrelated flags survive both outcomes.

The initial public graph is fixed. Every reset clears all flags and the message,
deselects the receiver, and returns that same graph. The public reset endpoint
accepts only the existing Browser optional seed field and never uses it to choose
a state. The application imports no oracle or learner; the server provides no
case installer. Public operation schemas reject extra arguments, including a
target attached to a primary transmission. All graph changes occur through the
visible endpoint controls. The receiver endpoint of each of eight patches is set
explicitly in every script, even when that public selection is a no-op. The left
endpoint controls are available and checked separately, but the allocation leaves
them at their fixed reset values. There is no extra representation calibration.

`oracle/cases_v1.json` freezes two disjoint two-source/two-target/four-bridge cells.
For each queried pair, three right-endpoint rewiring states give exactly zero,
one and two matching bridges. Names, member order, flags, selected target, action
owner, object counts, fixed left endpoints, endpoint-set facts and all endpoint
degrees are unchanged across that pair's matched primary pre-states. Every source
and target has degree two in those primary states. Sequential public endpoint
edits can transiently change target degrees; the claim does not extend to those
intermediate setup states. Their complete graphs are retained and audited in
`oracle/planned_exposure_v1.json`, rather than omitted from learner-visible history.

Training queries all eight within-cell endpoint combinations, each under the three
contrasts: 24 primary attempts, with eight zero-witness, eight one-witness and eight
two-witness occasions. Evaluation swaps the two cells' target sets and queries
eight endpoint combinations absent from training action queries, again with all
three contrasts: 24 attempts with the same witness histogram. Case order was
shuffled before execution using fixed allocation seeds independent of outcomes.
Case identifiers, contrast notation, oracle counts and expected results are not
rendered in the UI. Primary buttons are enabled by target selection only; their
enablement does not reveal graph truth.

The fixed-pair contrasts falsify both incidence-only competitors and a uniqueness
rule. Each of `source has any bridge`, `target has any bridge` and `exactly one
matching bridge` makes eight errors on each split; existential composition makes
zero. An answer depending only on the unchanged unary projection or a fixed
endpoint-pair lookup must predict one answer for all three states of a pair and
miss at least one per pair. This is discrimination in the generated raw task, not
proof that the learner's inferred vocabulary retains the same projection or even
the required bridge representation.

All four sources, four targets and eight bridge identities are declared visible
throughout training. Across training's primary and setup states, 16 distinct
bridge/source/target triples and eight source/target paths appear. Evaluation's
primary states contain 16 such triples; including its uniform reset and sequential
rewiring exposes 24 triples and 16 source/target paths. These exact sequences are
retained in the planned exposure ledger and reproduced by the model audit.
Evaluation necessarily shows its new paths during public setup before the primary
query. Novel queried pairs must not be reported as paths unobserved before their
evaluation action, or as an acquisition-policy result.

The separate invariance evaluation uses an independently chosen, disjoint opaque
alphabet for each entity collection and a nonidentity permutation of every member
list. Names in options, endpoint references, action targets, selection, flags and
event arguments are renamed consistently. Field labels, control labels, event
frames, semantic episode order, application bytes and route remain the same. Only
the presentation catalog changes when the separately owned service is restarted
on the same address. The mapping and evaluation scripts are frozen separately.
All 13 public-model snapshots of every evaluation episode equal their inverse-
renamed counterparts after removing member-list order. This checks the declared
transformation, not browser-level identity performance. The same frozen training
fit must score both evaluation copies without evidence admission or refitting.

The bounded audit ran under CPU 23, nice 19 and idle IO. It verified the pre-audit
input manifest before importing only the new model and reference. All 72 complete
scripts passed, with 6,380 assertions in 46 classes. Each split contains 288 public
scripted primitives and 312 explicit snapshots, plus 24 case resets. Public
scope resolution was simulated only against the model's declared visible groups.
The audit checked exact case/order alignment, uniform setup, degree and contrast
properties, independent oracle agreement, selected-target-only effects, event
arguments, source-only primary arguments, complete declared alternative counts,
renaming consistency, rejected invalid-operation nonmutation and Python source
compilation in memory. Source inspection checked the public control handlers,
absence of case/witness labels, absence of oracle/learner imports and fixed reset.
The invocation, stdout, detailed case results and snapshot hashes are retained.
These hashes identify public-model dictionaries, not raw learner observations.

No server was started. No browser, Recorder session, SemABI import, model fit,
learner prediction or learned scoring was executed. No claim is made yet about
actual accessibility-tree completeness, viewport visibility, control readiness,
scoped Browser dispatch, owner recovery, role inference, endpoint parsing, selected
target inference, chronology, paired reset accounting, identity, composition
learning or relational export. In particular, normal-desktop layout is an authored
intent that still requires a browser audit. The current retained T1 collector
ignores the new scope member and cannot be used as if it implemented the contract.
`collector_requirements.md` specifies the generic, separately reviewed resolver.

The modeled Recorder expectation is 313 charges per split: 288 script primitives,
24 case resets and one initial observed reload. That would produce 312 paired
interactions and one unpaired reset per split under the retained boundary. Those
are future accounting acceptance criteria, not observed counts from this audit.
The 48 primary training/evaluation attempts and 24 separate invariance attempts
remain distinct denominators, with unreachable setup or binding failures retained.

`exposure_v1.md` records the author's prior R1 exposure and knowledge from the
public JOIN brief. One separately tasked agent wrote both application and oracle;
their agreement provides generated-fixture self-consistency rather than external
validation. No learner feedback was read or used. The parent receives only a
metadata envelope and source inventory while these details remain sealed.

The pre-audit manifest binds all constructed inputs before the first model audit;
the final manifest binds that original input set, audit outputs, exposure, this
report and the separate invariance freeze. Further changes require a new version
with a retained change record; preserve these originals. Browser collection,
measurement/control review and the actual learner-source freeze remain separately
assigned work. Preparation does not authorize inventing successful measurements.
