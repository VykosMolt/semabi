# Frozen bounded V4 widget observation-evidence contract: revision 3

W2's accepted diagnostic isolates a scoring omission for an already represented
persistent widget value. W3 adds a necessary negative control: identity changes
can create widget attribute deltas without changing any rendered widget value.
Neither study establishes the candidate's identity as true. Both are disclosed
development evidence. Root freezes this mechanism after independent source review. Earlier designs
and their reviews remain retained; no repair execution has occurred. Reviews
identified overwritten source fields, partially promoted payloads and reference
resolution from another span as false-credit paths. This first repair is scoped
to emitted attributes; references earn no added widget observation credit.

Keep V2's existing predicate and V4's scoring order. In V4, combine the existing
non-widget observation check with a narrowly eligible persistent-widget change
check. Do not use canonical object IDs, emitted attribute deltas, global bags
of widget values, or the existence of any widget change as the new evidence.

For each side of a scored step, use the actual native parsed units, active
slots and node bindings. The widget field must be present in both `ui.slots`
and `ui.slot_nodes`, with an effective `(template, slot)` persistence marker.
Its logical owner must correspond to a unique actual parsed entity instance
at that unit root and the expected type, with a usable selected key. A frame
whose `slots` were cleared cannot provide support via leftover node bindings.
The field must be represented by that owner as an emitted attribute. A reference
or widget view slot is ineligible for this added channel. The mapping must have a unique active
source: several source slots can overwrite the same emitted attribute name. Conservatively exclude such collisions, including collisions
with non-widget sources. A losing source cannot borrow the surviving field.
Record/mention transformations whose exact contributing source is unavailable
likewise earn no added widget credit. Check the actual emitted owner and attribute source. Merely finding a matching
field name is insufficient. `_resolve_slot` can expand a reference token or
resolve another span from the same node; no unique reference-contributor
witness is available here, so exclude all reference slots from this new check. This remains candidate dependent:
it tests whether a represented persistent field has observed change evidence.

Pair owners through a unique raw rendered witness for the selected own key,
before any aliases, observation-specific overrides or positional suffixes.
Build a composite witness from each component's bound raw node and text, not
from canonicalized `ui.slots`. Use `node_text` for a key witness; `leaf_value`
returns only `True` for a button and would collapse distinct button names.
Neither root offsets nor page ordinals enter the cross-observation witness.
Require that witness to be unique within its template on each participating
page. Duplicate rendered keys, positional copies, absent key components and
non-unique owner mappings provide no new evidence.

Compare the same active field separately for each matched raw owner. Use its
exact native data span from the raw-key parse, before key associations, with
its node binding held. `G.data_tokens` splits numeric and word runs: if only
the numeric field in `4 red` is persistent, `4 red` to `4 blue` must contribute
no evidence for that field. Comparing the entire `leaf_value` would incorrectly
credit the unmodeled word change. The native raw span is still interpreted by
the candidate's token/field rules, not an oracle or a whole-payload identity claim.
Limit the added channel to combobox/textbox value spans. The current parser
uses checkbox/radio names rather than their checked state for these fields;
checked-state changes cannot be credited until that modeled channel exists.
Field identity and raw owner witness stay separate so exchanging
values between two owners or two fields remains observable even when their
global value multiset is unchanged. A collection reordering or alias-only
identity revision with the same raw values must contribute no widget evidence.

Use the native parser's W3 raw-key mode if its eventual accepted API provides
the required semantics without mutating the normal parse cache. Otherwise a
small local helper may read the raw key nodes directly. No second independent
parser or broad source-provenance framework is proposed.

The smallest supported carrier scope is an active field whose logical owner
also bears its persistence marker, including the parser's inherited frame slots.
An explicit attachment whose support exists only on another source template
needs an authenticated source-to-target ownership witness before it can earn
credit. Do not reconstruct that provenance by arbitrary ancestor guesses or
silently treat `attached:` spelling as evidence. Tests should establish that
such an unsupported carrier cannot borrow credit from its former frame. If the
existing native representation offers a compact exact witness, extend this
scope explicitly after source review; otherwise retain the omission as a
bounded follow-up. Empty-token or missing-field cases likewise cannot create
earned field support solely from the raw widget's existence.

Required tests belong in existing `tests/test_v4_objective.py`: W2's represented
change becomes EXPLAINED; unkeyed/transient interpretations remain unsupported;
two-owner and two-field swaps are detected; collection reordering is inert;
consistent and observation-local key revisions with unchanged raw values earn
no new evidence; duplicate keys cannot be disambiguated by position; key-name
buttons stay distinct; stale frame nodes and unsupported attachment carriers
cannot count; configured supported own fields are eligible; an overwritten widget and a
partially promoted multi-span value cannot count when only their unrepresented
portion changes; a changing widget span whose slot resolves a reference through
an unchanged fallback span cannot count; normal reload/view
contradiction and churn handling remain unchanged. Include whole `evaluate`
verdicts for the positive, identity-induced and partially promoted negative
cases, not just helper
booleans. Test failures must preserve their actual cause rather than changing
expected outcomes to get a clean run.

The score remains step-level: an observed qualifying change can support the
step's existing domain-delta classification. This does not prove every emitted
delta atom matches the same field, fix non-widget evidence pooling, infer
correct identities, or recover J1's missing patch and receiver bindings. Implementation owns only `semabi/compiler/v4/objective.py` and the existing
`tests/test_v4_objective.py`, plus versioned development records in an isolated
worktree. Keep the shared V2 objective unchanged. Reuse W3 raw-key parsing after
its source is accepted; do not implement a second parser. Run focused tests, independent
source/result review, the canonical full suite and all five dedicated corpora
before adoption. W3's persistence repair and its preserved results stay separate.
