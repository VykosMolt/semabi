# Proposed V4 observation-evidence repair after W3

W2's accepted diagnostic isolates a scoring omission for an already represented
persistent widget value. W3 adds a necessary negative control: identity changes
can create widget attribute deltas without changing any rendered widget value.
Neither study establishes the candidate's identity as true. Both are disclosed
development evidence. This is a source-grounded design for review, not frozen
implementation or a new execution authorization.

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
The field must be represented by that owner as an attribute or reference,
not merely retained as a widget view slot. This remains candidate dependent:
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

Compare the same active field separately for each matched raw owner. Obtain
the state from `leaf_value`: `value` for combobox/textbox and `checked` for
checkbox/radio. Field identity and raw owner witness stay separate so exchanging
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
cannot count; configured supported own fields are eligible; normal reload/view
contradiction and churn handling remain unchanged. Include whole `evaluate`
verdicts for the positive and identity-induced negative cases, not just helper
booleans. Test failures must preserve their actual cause rather than changing
expected outcomes to get a clean run.

The score remains step-level: an observed qualifying change can support the
step's existing domain-delta classification. This does not prove every emitted
delta atom matches the same field, fix non-widget evidence pooling, infer
correct identities, or recover J1's missing patch and receiver bindings. Once
the mechanism is reviewed and implemented, run focused tests, independent
source/result review, the canonical full suite and all five dedicated corpora
before adoption. W3's persistence repair and its preserved results stay separate.
