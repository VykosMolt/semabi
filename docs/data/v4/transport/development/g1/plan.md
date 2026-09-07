# G1: preserve graph ownership after V4 hypothesis selection

T1 is disclosed development evidence, preserved before repair at `8dc28ba`.
The complete first-pass review must close before learner edits begin. Root has
seen T1 observations, scores, the T1-only fixture audit and oracle binding
controls. Root has not opened the shared fixture implementation or the reserved
interface contents. This repair does not spend the reserved evaluation.

## Demonstrated cause and bounded mechanism

V4 search copies hypotheses, including their observation graph. The selected H
is later paired with the earlier G. Reading an unseen page inserts its signature
into A.G, while H.parse_units asks H.G for the same signature and raises KeyError.
T1 inferred readings fail on every target; graph-coherent pinned readings execute
but still lack task bindings. The latter is a separate representation problem.

Carry H.G after final inference/promotion selection in compile_v4, and construct
candidate abstractors with Hx.G in search._build. Preserve the existing search
signature and V2 behavior. Do not rebind hypothesis caches, change search
objectives, normalize live pages, alter field/identity policies or change
acquisition. Candidate graphs must remain independent.

## Acceptance and execution order

1. Add regression coverage in existing test homes. Real inferred compilation and
   consequence.fit(None) must parse, recognize controls and abstract a new page.
   Test both ordinary selection and an accepted promotion, plus pinned and
   legacy identity branches. Observe frozen learned vocabulary, headers,
   templates, emissions and resolved controls before/after reading; permit only
   per-observation structure to grow. Show that a source/sibling graph is not
   changed and that selected training behavior is preserved.
2. Run focused meaningful tests and independent source/test review. Preserve any
   failed run with its exact source rather than weakening expectations.
3. Freeze the repaired source in a new development manifest. Reuse the original
   T1 scorer on the two initial and four distinct terminal development histories;
   identical first-pass arm pairs do not require duplicate development scoring.
   Keep all seven pinned candidates and current inference, task/all-click scopes,
   identity surfaces and runtime errors. Reapply the existing evaluator-only
   binding controls. Runtime recovery alone is not representation recovery.
4. Validate retained behavior and all five dedicated allocation/pilot/separating
   corpora, retaining known residuals. Use the existing reviewed corpus instrument
   with a new output directory and source snapshot. Run the full suite with
   authorized local sockets, one thread, and serialized cache/auth-sensitive work.
   No source/head changes during provenance-sensitive fitting jobs.
5. Review the exact changes and evidence, preserve a local verified checkpoint,
   then investigate remaining representation losses. A separate chronology
   source audit may proceed concurrently but must not alter G1 source or claims.
   Reserve a new freeze before assessment on unseen cases; continue toward JOIN
   after the useful demonstrated transport blockers are investigated.

Root owns this protocol and development instruments. The implementation worker
owns only the two production files and suitable existing tests. Independent
review and validation are separately assigned. All numeric libraries use one
thread; aggregate heavy work remains below 12 cores. Every run has a unique
directory, command, source/data hashes, process owner and termination record.

The original temporary corpus reconstruction was unavailable on resumption.
`rebuild_inputs.py` reuses the preserved reconstruction instrument with isolated
output manifests, protecting its original baseline validation record. The new
45-file reconstruction lives at `runs/v4/transport_g1_corpora_v1`; all 36 consumed
input files match the baseline, with nine additional merge-provenance records.
The runtime adapter verifies the bound source, measurement helpers and every
reconstructed file before fitting. The summary checks each score against its
phase's exact source/freeze and recomputes all-click denominators from raw rows.
Earlier unexecuted adapter proposals are retained under `instrument_revisions/`.
