# W3: widget promotion after a supplied identity revision

Source review of W1 commit `284d80c855ff37c42a509ae1dd88f83d4e04e3f4`
predicts that fitting can promote a widget under rendered keys and later apply
observation-local key associations without rechecking that promotion. W1's
duplicate-key repair does not address a bijective revision with unique keys.
This separate invented diagnostic tests that prediction through actual
`Hypotheses.fit`; it does not modify W1 or W2's retained evidence.

Use two ten-node observations. Both contain list items Alpha/Red and Beta/Blue,
with each color in a combobox. Only status text outside those items differs
between observations. The three other stable outside nodes keep the page's
view structure stable under the native heuristic. Supply the pair as an
invented reload, not as evidence of a real application intervention.

Build two fresh native graphs and hypotheses from identical observations.
CONTROL supplies no key association. AFTER_BIJECTION supplies only after-side
overrides Alpha-to-Beta and Beta-to-Alpha. Call the real default fitting method
once per condition. Do not force its selected key, promotion, parsing, entity
types or final state. Retain construction failures and unexpected results.

The source prediction is that both fits select `listitem#0`, retain distinct
non-positional canonical keys, and retain `combobox#0` as a persistent widget.
CONTROL's final same-key matches should have two retained values and no losses.
AFTER_BIJECTION should instead have zero retained values and two losses: the
canonical Alpha changes from Red to Blue, and Beta from Blue to Red. A retained
promotion under those final associations would be inconsistent with the actual
method's own retained-value criterion. It does not establish that these supplied
identities are true or normally learned.

Record complete fitted and subsequently parsed units, selected keys, slot
statistics, associations, persistent markers, canonical match multiplicities
and native before/after states and deltas. Use the actual V4 abstractor and
tracker; also retain changes outside the selected unit. An optional read-only
Python trace may snapshot the native promotion and final-association method
boundaries during fitting. It must preserve the exact prior trace function and
must not replace or alter native callables or their return values.

Reuse the sealed W1 stdlib validation guard to authenticate its original native
source, tests, inputs and package origins at the original W1 worktree. Reuse
only the deterministic serialization functions from W2's sealed diagnostic
source. Bind both helpers' exact bytes, this script, invented inputs, contract,
source/data freezes, runtime, command and environment in a separate W3 freeze.
Use the W1 worktree's existing runner with an exclusive W3 output directory,
one CPU, one numerical thread per library, hash seed zero, disabled bytecode
writes and a new absent lookup prefix. Main's study files are explicit inputs;
the executed SemABI package must come from W1's frozen worktree.

Review the completed instrument before execution, run it once, preserve its
complete attempt and source/process records before semantic inspection, then
review the result independently. No new native repair follows from the source
prediction alone. The ordinary V4 builder does not install these overrides;
this is an explicit supplied-identity diagnostic of a supported hypothesis
state, not a claim about automatic V4 identity induction or fresh transfer.
