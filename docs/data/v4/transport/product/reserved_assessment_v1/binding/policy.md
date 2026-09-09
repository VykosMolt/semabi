# Shared assessment binding prior v1

This is assessment assistance shared identically by both execution arms. It is
not the product's ordinary-goal API, a general planner, or evidence of task
execution. The binder uses only the ordinary goal, its supplied arguments, and
the automatically learned public operations for the selected connection. It
does not consume application names, request identifiers, fixture expectations,
selectors, or action recipes.

The entire goal must match one of these deliberately limited English forms:

- Create a/an [new] ENTITY with this exact FIELD: VALUE
- Save a/an new ENTITY with this exact FIELD: VALUE
- Replace the ENTITY whose full/exact FIELD is "OLD" with "NEW".

ENTITY is one opaque current-connection concept, expressed as a single word.
It is not an independently learned entity type. The binder checks the action
and payload grammar and the exposed operation scope, not arbitrary domain
semantics or an application object model.
Grammar is case-insensitive and permits an optional final period. Supplied
values are matched literally and retain their exact case, punctuation, and
whitespace. Values come from the argument dictionary, never from prose
extraction. A trailing instruction, qualifier, output request, filter, unread
choice, or second step prevents complete matching. Instructions inside a
supplied literal payload remain payload.

Argument keys and learned labels use case and punctuation normalization only.
The small key-role prior recognizes old/current/existing prefixes for current
selection and new/replacement prefixes for replacement. An exact/full prefix
marks a complete value and can identify current selection when paired with an
explicit new/replacement key. Conflicting or missing replacement roles are
unestablished. Update keys must name the same normalized field. Identical old
and new values are outside this replacement prior. Ordering never assigns
meaning.

A sole content/text/body/value payload can bind to a sole unnamed text
property whose learned description is "Visible editor value". This is an
explicit cardinality and payload prior; it does not learn an alias between an
application concept and a field. Named fields require an exact normalized
property-name or visible-label match. Current selection requires the learned
schema description "Exact current local anchor: LABEL".

Only active local-form-creation operations and local-exact-value-replacement
operations qualify. A replacement requires exactly one selector and one
replacement text property, with a declared local exact-value replacement scope.
The full source artifact and its limitations accompany the returned call.

Every input argument and required property must participate in one unique
bijection. Only the current learned flat, closed, required-string schema is
supported, including its length and supported HTTP(S)-URL/email constraints.
Values must already have normalized nonempty whitespace. Unknown schema
constraints are rejected. There are no conversions, inferred defaults, list
joining, implicit current-value reads, merging, retries, or partial dispatches.
Multiple compatible active operations are ambiguous.

ELIGIBLE means only that the request has a complete binding under this prior.
It returns a deep copy of the public operation and the unchanged mapped values.
Both arms receive that exact call. The receipt hashes the request, the public
operation catalog, the selected artifact, this policy, and the binder source.
UNSUPPORTED returns a null call, records unresolved clauses or binding reasons,
and retains the request in the assessment denominator.

All receipts say browser_started=false and execution_result=NOT_STARTED. They
are preflight classifications, not execution outcomes. General goal planning
remains UNESTABLISHED. Restart, viewport, logout, and interruption opportunities
belong to the coordinator and require separate evidence; an eligible creation
body does not establish that an intervention occurred.
