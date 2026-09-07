# Fresh transport fixtures

The public interface and initial scripts are in `public_contract.json`.
Start the local server with `python experiments/transport_v1/server.py --port 8767`.
The server has one mutable session. Browser arms and cases must use it sequentially;
each reset replaces the complete session. Independent audits start their own server.

The learner receives only accessibility snapshots and ordered public action history.
Application source, reset payloads, oracle files, and withheld evaluation scripts are
outside the learner input. All controls are ordinary visible HTML controls addressed
by accessible labels. A native number input may be represented as `textbox` by the
existing Browser snapshot implementation; the scripted recorder can record that
interface translation. No learner representation change is implied.

`oracle/` is sealed evaluator material. Its reserved fixture contract and traces
must remain unopened by the root learner and evaluator until the repair checkpoint.
`audits/self_consistency.json` is safe to read: it reports counts and audit status,
without fixture outcome values. These audits do not fit or evaluate SemABI.

Fixtures, oracle specification, and scripts are hashed before auditing in
`manifest_pre_audit.json`. The final freeze records the same exact inputs after
self-consistency checks. Every application change requires a new freeze before
any SemABI evaluation.
