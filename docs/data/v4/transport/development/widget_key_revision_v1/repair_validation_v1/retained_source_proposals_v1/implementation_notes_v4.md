# Context key changes after association

Candidate v4 repairs the statically rejected v3 context-split gap. The prior
candidate snapshots and baseline snapshots remain retained; candidate v3 was
never executed. The implementation worker ran no native tests or executions
while preparing this revision and made no commit. Root owns the paired baseline
and candidate execution and acceptance.

`_split_by_context` records actual nonempty selected-key slot changes for a
derived or remaining unit only when its template has aliases or observation key
overrides. After every derived unit and context mapping exists, the native raw
parser supplies the selected components. A shared materialization helper checks
the fitted site, owner, former-key and new-key component node bindings. It restores
the former key's raw ordinary-field value and applies the current correspondence
once to the new whole selected key. Slot statistics are refreshed without
selecting another key. The unassociated path keeps its prior behavior.

The existing associated composite harmonization uses the same helper. It now
also validates and restores the former key if that slot is outside the new
composite. Unassociated harmonization retains v3's original per-instance
materialization and incomplete-instance behavior.

For an affected instance already present in the ordinary page cache, context-key
materialization validates the same raw owner and participating bindings, retains
the cache dictionary and instance object, retags a derived template, and refreshes
only the touched key fields and positional flag. A detached ordinary parse
supplies its normal alias and positional behavior. The added private `cache`
option defaults to the existing public behavior; raw-key parses always skip the
cache regardless of that option. The detached ordinary option is used only for
these already-present affected cache objects. Arbitrary objects returned by older
parse calls are not live views and are outside this bounded cache refresh.

Every participating binding within a unit is checked before any of that unit's
instances are materialized. A later unit can still fail after an earlier unit
has changed; a small context-materialization failure marker makes subsequent
builds fail explicitly. The existing build failure path clears both entity maps
and unfreezes the hypothesis. Constructing a new `Hypotheses` is the recovery
path for this bounded repair. There is no implicit recovery or reset in `fit`.

The new native-parser/direct-unit context fixture makes the real `_choose_key`
change both derived and remaining scopes from `text#0` to `listitem#0`. Its
none/alias/override controls check canonical selected keys, raw former values,
supported widgets, fitted/fresh parse agreement, distinct cache object coherence,
and repeated builds. A second regression injects an existing but incorrect cached
former-key node and verifies explicit failure on two builds, empty entity maps,
and unfrozen state. The only edit to a prior test replaces invalid parent 999 in
the owner-mismatch fixture with asserted-existing, different parent 0; its
mismatch and revocation assertions stay intact. The original executed baseline
and its failures remain retained by root.

`baseline_v4/source` contains the original production modules from
`a1c0bc96d6a9725a3f23e18dbc96f97b0bd38f08` and exactly the same two tests as `candidate_v4/source`.
The full candidate patch has SHA-256
`d7f3239c98f42b36460ff8de244ebc8c1bed061a8741075c1a2c5484a80d11f5`.
The tests-only baseline patch has SHA-256
`169441e20cefd14af75799d194bfbc00dc284eebd002c0c2d2631cc5b4af02f0`.
The full diff from candidate v3 has SHA-256
`2878ed9c49d326cc3979c5968c04cc70e049ff2c2321e5494f829d3262fbe62d`.
Separate source-only and test-only v3 diffs are retained beside that patch.
`candidate_v4/source_freeze_v1.json` records all current, previous and baseline
file hashes and patch hashes.

| Candidate file | SHA-256 |
| --- | --- |
| `semabi/compiler/v2/hypotheses.py` | `8dab56a4b4d7a56424e5e91648b49f60f9ba576502ad0d9832ccce57ba50d235` |
| `semabi/compiler/v2/refinement.py` | `592029f46ed70f37198386535e5a45c7330cb98189bbda3b20663df28afa335a` |
| `tests/test_v2_collection_variation.py` | `b66dc6caf0bc68a2694e5129d514efca415833ef2d879adf5ba086bbad6cd26c` |
| `tests/test_v2_refinement.py` | `60faa0ecaa61e2a11dbc382baeff971f7acc313f95887d39330ffc6ddcf7c748` |
