# W2 observation regression proposal: baseline v2

This is an unexecuted revision of the disclosed W2 development tests. It follows
the frozen `widget_observation_v1/repair_contract_v3.md` and root's bounded
fixture correction after W3 source acceptance. The entire `baseline_v1`
directory remains unchanged, including its earlier W1 source bindings and
unexecuted predictions. These invented observations are neither blind nor
fresh transport evidence.

## Source boundary and dependencies

Both planned W2 execution arms use integrated HEAD
`e8f33c9056cc51135b7f9553fad3a7ad829def04`, which includes the accepted W3
parser and persistence repair. Its `Hypotheses._parse_units` signature is
`(sig, *, raw_keys=False, cache=True)` when bound. The v2 manifest records the
exact native bytes, W3 integration record, candidate objective v3 source
proposal, and prior test proposal. The unchanged objective at this HEAD is
the baseline; the proposed objective is root-owned and outside the test patch.

The complete proposed test bytes, exact test-only diff from integrated HEAD,
and exact diff from the frozen v1 test bytes are retained here. Native code,
pytest collection, tests, diagnostic instruments and corpora were not executed
during this revision. Static checks parse and compile source without executing
the resulting code, inspect ASTs, and compare file bytes and hashes.

## Corrected stale-source diagnostic

The two stale-source cases retain their expected `SPURIOUS` verdict and error
count. The fixture now saves the bound native private parser, forwards both
keyword arguments unchanged, and mutates only an after-side raw-key parse.
The `slots` case removes only active `combobox#0`, retaining `heading#0` and
all node bindings. The `node_binding` case removes only the widget binding,
retaining both values and the key binding. The original branch assertions and
verdict assertions remain present.

The wrapped boundary is explicitly exercised exactly once with `raw_keys=True`
and `cache=False` before scoring. Assertions establish the exact resulting
slot and binding dictionaries, the retained native parsed-emission cache
objects, and an unchanged complete native emitted delta. The mutation log is
then cleared. Every later observed mutation must still be after/raw; an empty
evaluation log is permitted in both arms because the unchanged objective
does not use the added raw widget channel. The existing configured-own-field
and reload-promoted positive controls independently require `EXPLAINED`, so
ignoring the channel cannot satisfy the shared suite. Neither fixture imports
the candidate helper or changes an expectation according to the arm.

This remains an explicitly instrumented stale-source diagnostic. It does not
claim that native frame transfer creates this complete cached state. Native
carrier behavior is covered separately.

## Added native inherited-frame controls

The two new tests construct observations and candidate unit/key/persistence
decisions, then use real `ObsGraph`, native ordinary and raw parsing, slot
statistics, entity building, V4 emission, state diff and complete `evaluate`.
Their positive parser results are never replaced by custom parses.

- Column context: a table header cell renders `Field`; a data cell frames a
  keyed button `1` and a combobox changing red to blue. Native transfer clears
  the frame's transient source value and retains its node binding, then native
  column processing adds `col`. The final frame slots must equal
  `{'col': 'Field'}` while the child owns persistent `^combobox#0`.
- Later attachment: a section has a constant numeric heading and a separate
  constant textbox `9`, alongside a frame containing button `1` and the changing
  combobox. The heading prevents the section from becoming a transient frame.
  A declared native attachment moves only that textbox onto the frame after
  the frame transfers its own combobox. The final frame slots must equal
  `{'attached:textbox#0': '9'}`. The combobox's old frame node binding remains,
  and only the child bears its effective persistence marker.

Both cases assert the immediate parent, sole nested child, exact active values
and node bindings on both pages, a unique actual emitted child owner of the
expected type, its key and emitted attribute, and exactly one red-to-blue
attribute delta with no object or relation changes. The unchanged V2 content
predicate must be false; the full verdict must be `EXPLAINED` with zero errors
and one delta atom. The original empty-frame positive remains unchanged.

## Preservation, predictions and remaining gates

All 126 assertion ASTs from v1 remain in their original functions and order.
Of its 39 top-level functions, 38 retain their exact function source and AST;
only the stale-source fixture changes. All eight repository-original tests
and the original helper also retain their exact source and AST. The two
added test functions raise the static total from 44 to 46 cases.

Against the unchanged objective plus accepted W3 native source, **11 failures
and 35 passes are predicted, not measured**. The nine v1 positive cases retain
their predictions; the two new native inherited-frame cases also require
`EXPLAINED` where the baseline is predicted to return `SPURIOUS`. Candidate
objective v3 is predicted to pass all 46 cases. These counts are source-based
expectations, not pytest collection or execution results.

Root owns independent fixture/source review, paired execution and acceptance.
If execution fails at a native fixture or emission precondition, retain and
report that actual failure separately from a verdict failure. No expected
outcome may be weakened to match a run. Focused results cannot replace the
canonical full suite and all five dedicated corpora required before adoption.
