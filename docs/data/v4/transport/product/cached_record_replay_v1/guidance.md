The cached baseline now accepts learned CREATE, READ and UPDATE recipes.
The two-file patch is `cached_record_v2.patch`. It adds 136 production lines
and retains the existing budgets and creation flow, with reviewed deadline and redaction corrections.
`cached_record_delivery_v2.json` binds the original and candidate bytes and
records the frozen P4 BrowserSession/Surface dependencies. No main files or
application state were changed.

READ and UPDATE receive the same SemABI artifact assistance: flat string
argument schema, cached readback URL, selector/anchor names, field descriptors,
record-local Edit or advertised menu trigger, cached update arguments, and
submit descriptor. Shared `visible_record_matches` provides current local
record parsing. Each arm must carry the acquisition and artifact-assistance
charge. This remains conditional replay, not independent onboarding.

The target must match exactly one current local record. Direct Edit must be
unique within that record; a cached menu route requires one record-local
advertised trigger and one globally unique cached Edit afterwards. All cached
read fields and the submit control must resolve globally uniquely and share
one native form where present. The loaded anchor must equal the requested
target. Unknown or incomplete family recipes stop before browser creation.

READ returns structured values with DISPATCHED, then closes the browser.
UPDATE captures all cached read-field values, holds temporary observed DOM
elements through the P4 continuity API, re-resolves and checks those evolving
values and elements before each fill and Save, and dispatches Save once.
The handle is released in finally. Missing continuity support stops UPDATE.
The existing elapsed deadline includes authentication and all browser work;
late possible actions stay UNKNOWN and are not retried.

The baseline does not consume learned effect slots, match full learned form
contracts, check unmodeled defaults, verify saved effects or replacement
absence, or reload. Global descriptor ambiguity, including an unnamed
composer/editor pair, stops honestly. Temporary DOM references do not assert
persistent record identity. An independent evaluator still must establish the
requested business result.

All 82 tests in the existing `tests/test_cached_form.py` passed on CPU 7 with
one thread per numeric library: 43 existing create/deadline tests and 32 new
record cases plus seven review regressions. Positive READ/UPDATE cases use fixtures with no saved effect;
negative cases cover duplicate targets/Edit, global field/submit ambiguity,
wrong loaded anchor, split native ownership, reactive changes, DOM replacement,
missing continuity API, deadline after Edit, invalid recipes/schemas/menu
metadata, and credential redaction. No live app test or paired assessment was
performed. The corrected source passed independent review with no remaining material
finding in the assigned scope. The patch intentionally excludes the P4 dependency files; combine
it with the reviewed P4 implementation before using UPDATE with BrowserSession.

Version 2 supersedes the initial package. It checks elapsed limits after
continuity cleanup and after intent, navigation, and authentication event
logging before dispatch. A late cleanup preserves a prior failure; otherwise
late post-update cleanup becomes UNKNOWN. Credential redaction replaces
longer values first so overlapping usernames cannot expose password suffixes.
