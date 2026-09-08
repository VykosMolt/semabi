# Saved training operator boundary

This is an inspection of the already preserved training fit, not a held-out
prediction result. `inspect_operators_v1.py` authenticates the copied trace
against the 705-file first-pass seal and extracts its stored fields without
importing native modules or reconstructing any model. Output SHA-256:
`d865137fa1ce9257ba00ac2537e899ef52694ae0592ffb796044dffe72548887`.

The final projection contains ten operators, all with two object parameters:
`?o1` of T0 and `?o0` of T1. Each has a Transmit click and a synthetic select
action in its lifted signature; each effect is an emission. Their stored
preconditions use endpoint attribute inequalities. The ten observed grounding
calls have only `?o0` wanted, both parameters classified as output variables,
no effect variables, and no intermediate witnesses. Each returns a selection
query, covering six distinct combobox slots. These are copied decisions of this
fit; they are not proof of semantic correctness or of an absent entity type.

The final Transmit outcome retains owner plus six selection roles. Both event
frames retain output-position 0 as owner and no role at position 1. The latter
fact must remain separate from frame accuracy and from any correctness claim
about a selected target. The other three control models have no learned roles
and retain only their observed silent event.

The synthetic select must not be misclassified as a chronological macro error.
For example, stored `transition_000000` has `steps == macro == [12]` yet two
lifted acts. In native `Inducer.lift`, an effect/output parameter not supplied
by the actual actions is sought in the prestate view, and lines 892–902 insert
its naming pseudo-action. `_find_view_source` at lines 980–1001 selects the first
matching widget/context slot after the collection-member-position guard.
The saved fields and source establish this construction; this inspection does
not call the helper on reconstructed state.

`referring.ground` derives wanted variables from effects, output arguments and
enabling owners, while merely recording other parameters as witnesses. The
stored calls introduce no new intermediate. Its selection-query branch tests
naming on each operator's positive evidence. That is narrower than proving a
query names the task's selected endpoint across all control occasions.
`outcome.py:1084–1112` subsequently keeps an event argument role only when its
nonempty naming tallies agree; the saved model supplies no role for position 1.

The next independent inspection asks whether the visible bridge records and
their references exist in the saved abstraction at all. A missing intermediate
parameter alone cannot distinguish an upstream representation loss from a
proposal-language boundary. Actual evaluation outcome performance remains
unestablished under the retained failed scorer until the separately reviewed
path-format correction and all downstream custody gates complete.
