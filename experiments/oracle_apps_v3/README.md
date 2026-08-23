# Instrumented gauntlet-v3 applications (evaluator-only)

Copies of two gauntlet-v3 applications (`~/semabi-gauntlet-v3`, commit `64393bc`) whose
render code additionally emits `data-eid` (this element renders entity id), `data-erefs`
(this element references these entity ids) and `data-oid` (option -> entity id), plus the
ids the client payload needed to carry them. Used only by `semabi/eval/oracle_hook.py` and
`semabi/eval/oracle.py` for the A/B/Bv rungs of the V3 localization
(`docs/v3_diagnosis.md`).

The DOM trees are identical in the compiler's observation language — attributes are not
part of the snapshot — verified by driving original and copy through the same primitive
sequences and comparing structural signatures at every step
(`semabi/eval/v3_instrumentation_check.py`; 2 seeds x 61 snapshots per application, 0
mismatches, `docs/data/v3/instrumentation_*.json`). The traces collected on them are
byte-identical to the official traces. The benchmark repository is untouched.

| copy | original | ports used |
|---|---|---|
| `vet_clinic` | `authors/C_claude_sonnet/apps/01_vet_clinic` | 8980 |
| `harbour` | `authors/B_claude_opus/apps/01_harbour` | 8981 |
