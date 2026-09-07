# J1 collector requirements

This is public operational metadata for a separately authored generated local
fixture. Case scripts, allocation, application content, mapping and oracle remain
evaluator-owned until predictions and the first assessment are preserved.

Use one unchanged public route, `http://127.0.0.1:8771/join`, and one public reset,
`http://127.0.0.1:8771/reset`. The primary and invariance presentation profiles run
sequentially on that same address. The fixture accepts the existing Browser reset
payload containing an optional seed, but every reset produces the same public
initial state. The seed cannot select a case, graph or answer. Local assets only.

Scripts use schema version 2 and retain ordinary `snapshot`, `click` and `select`
primitives. Every target has an accessible role, exact accessible name and,
when needed, an exact visible ancestor-group scope:

```json
{"kind":"click","role":"button","name":"<visible control label>","exact":true,
 "scope":{"role":"group","name":"<visible group name>","exact":true}}
```

The required collector extension is generic: resolve exactly one visible group
in the preceding public observation by the declared role/name, and resolve
exactly one matching visible descendant control inside it. Apply the ordinary
Browser primitive to the resolved raw control node. A repeated label must not
fall back to a global first match, ordinal, hidden DOM attribute, catalog index,
source inspection, or oracle binding. Missing or nonunique scopes/controls count
as unreachable, without replacement or extra probing. The same resolver must be
used for primary and invariance profiles and must preserve raw owner ancestry.
Do not pass scope, case identifiers, scripts, endpoint bindings, expected answers,
or application state dictionaries to the learner. The learner receives the
ordinary raw observation and completed public primitive, with its raw node target.
The retained T1 collector does not implement this scope contract and is not
authorized by this envelope to silently ignore it.

Every script has one snapshot after the uniform public reset and one after each
of 12 public primitives; the final primitive is the primary attempt. There are
24 cases and 288 scripted primitives per split, plus 24 case resets. Under the
retained Recorder boundary, an initial observed reload adds one charge: 313
charged actions, 312 paired interactions, one unpaired reset, and 24 primary
attempts per split. Those Recorder totals are requirements to verify during the
future collector audit, not measurements from this construction. Training and
held-out primary evaluation have 48 primary attempts combined. The 24-attempt
invariance evaluation is separate and must score the same frozen fit without
refitting or evidence admission from either evaluation split. Snapshot calls do
not grant unlogged exploratory interactions. Failed setup and resets stay charged.

Wait for ordinary application completion before taking the next observation.
The root element exposes `aria-busy` while actions are pending. Any readiness
handling must use this generic public signal or the established Browser settle
path and must not wait on an expected answer, hidden case state or oracle.

Before learner execution, separately freeze/review the collector extension,
chronology-correct learner source, pre-action prediction preservation and any
identity intervention. With a granted worker slot, audit accessibility visibility,
complete alternatives, scope resolution, selected control values, source-owner
recovery, reset pairing and actual primitive accounting on retained raw evidence.
The construction's in-process model checks do not establish those conditions.

The service is single-session state. Its separately identified owner must record
PID/PGID, command, cwd, profile, source inventory and timestamps, then stop and reap
only its own process before switching profiles. Use CPU 23, nice 19 and idle IO:

```text
taskset -c 23 nice -n 19 ionice -c 3 python experiments/join_v1/server.py --host 127.0.0.1 --port 8771 --profile primary
taskset -c 23 nice -n 19 ionice -c 3 python experiments/join_v1/server.py --host 127.0.0.1 --port 8771 --profile permuted
```

These are prepared commands, not executed services. Experiment jobs require the
reviewed retained job wrapper and a unique J1 run identity under an owned `jobs/`
directory. Browser or fitting work remains pending worker-slot authorization.
