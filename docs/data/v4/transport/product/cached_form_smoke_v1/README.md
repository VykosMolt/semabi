Both cached-form development smoke requests dispatched successfully, and an
independent browser check found exactly one matching record before and after
reload in each application.

| Application | Learned artifact | CLI result | Actions | Possible writes | Replay seconds | Visible matches before / after reload |
| --- | --- | --- | ---: | ---: | ---: | --- |
| Memos | `op_da6cd313fd7951e26d2c`, v3 | DISPATCHED | 7 | 5 | 6.635 | 1 / 1 |
| Linkding | `op_5c8e47ab193b2c074b8e`, v1 | DISPATCHED | 11 | 9 | 6.214 | 1 / 1 |

The action and possible-write counts include three authentication actions per
application. Each replay allowed at most 20 actions and 12 possible writes.
Both CLI processes exited 0 and closed their browser sessions.

Both exact active operation artifacts came from public SemABI HTTP. The
baseline received their learned schema, navigation and control descriptors.
Memos filled the learned unnamed content editor and clicked Save. Linkding
followed the learned Add bookmark link, filled Description, Tags, Title and
URL, then clicked Save. Each descriptor was resolved against a fresh observed
surface. Arguments were generated from the schemas: fresh readable strings,
one tag token, and an `example.invalid` URI. No hand-authored selector or
runtime effect helper was supplied to replay.

The independent check directly reused the unchanged `DOM_JS` and
`record_checks` from `runs/product_evaluator_v3/check_effects.py`. It opened a
fresh session for each app, authenticated through ordinary UI, checked the
visible record, reloaded, and checked again. Its six authentication actions
and 4.726 / 2.754 seconds are separate from replay. All checker sessions closed;
the checker process exited 0. Its first launch failed on a local import path
before any browser opened; correcting that wrapper path did not repeat a
baseline request.

Executed P2 source was captured at commit
`1bde0a742b7aab1f55f459275e6ef55fe7350247`. Recorded source hashes matched
through both replays and independent checks. Full redacted observations,
action intents, action outcomes, steps, schemas, arguments, process exit
codes and independent DOM captures remain beside this summary.

This is a development smoke on existing accounts. Accounts were not reset,
fixtures were not matched, and this is not the prospective paired assessment
or evidence of superiority. Visible uniqueness is limited to the inspected
UI. The smoke did not independently inventory all other side effects or
collect pre-submission absence snapshots.

`ledger_v1.json` separates shared artifact assistance, replay and verification.
The four public GETs took 0.012 seconds in total. Both comparison arms must
carry the same prior P2 learning and artifact-acquisition charge. Prior
learning cost was not present in these public responses and was not
remeasured; the ledger retains it as unmeasured, not zero. Each supplied
artifact retains its two successful automatic learning trials. No additional
learning, model calls, paid calls or replay retries occurred.
