Predeclared diagnostic contract, 2026-09-07.

Question: on the six disclosed G1 training histories, would applying the existing
section normalizer with a profile learned only from raw training observations
change designated T1 evaluation pre-states or training pages?

The fixed histories are dispatch and workshop, each at `initial_v2`,
`contested_1701`, and `contested_1702`. Each uses its fixture's unchanged
`evaluation_v2` observations, steps, and public task-target decision metadata.
Input paths are enumerated explicitly. The script verifies the G1 source/head,
run completion, raw input hashes, observation signatures, step references, and
task-target joins. It never opens a path named by a case, an action, or source
provenance metadata.

For each history, build one `ObsGraph` from its raw training observations in
recorded order. Resolve its statistical vocabulary and value paths, then set
`learning=False` before admitting any evaluation descriptors. Use the existing
`sections.normalise` on training and evaluation observations. Separately call
the existing full-training `_normalise_sections` on a fresh in-memory log and
check its exact output against the same training-only profile. No model fitting,
browser action, or application/oracle/reserved input is allowed.

Retain each raw/canonical signature, node count, parent changes, appended nodes,
and accepted span candidates. Join every designated task to its raw evaluation
step and record its pre-state transformation. Assert that every original node
index, full `Node.key()`, and bounding box is preserved, that all action targets
still identify the same original node, and that all derived step references
resolve. Preserve the complete statistical profile and require its digest to
remain unchanged after training normalization and after every evaluation page.

Capture executable/source/input bytes and hashes before execution, verify them
again afterwards, and retain full results and owned-process metadata through
the existing one-thread job runner. All new files remain under this diagnostic's
directory; source, tests, and existing evidence are read-only.

If no designated pre-state or training page changes, this proposed section
normalization control cannot explain their loss on these histories. This does
not resolve every normalization or representation question. If pages change,
identify them as candidates for further parsing diagnosis; changed structure
alone establishes neither a repair nor task capability.
