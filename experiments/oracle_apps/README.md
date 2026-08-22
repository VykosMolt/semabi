# Instrumented gauntlet-v2 apps (evaluator-only)

Copies of the eight gauntlet-v2 apps (`~/semabi-gauntlet-v2`, tag `gauntlet-v2`)
whose render code additionally emits `data-eid` (this element renders entity
id), `data-erefs` (this control references these entity ids) and `data-oid`
(option -> entity id) attributes, plus the ids the client payload needed for
that. `INSTRUMENTATION.diff` is the complete diff against the originals.

The DOM trees are identical in the compiler's observation language (attributes
are not part of the snapshot); verified by driving original and copy through the
same random primitive sequences and comparing structural signatures at every
step. Used only by `semabi/eval/oracle_hook.py` / `semabi/eval/oracle.py`
(docs/v2_oracle.md). `./run_all.sh` starts them on ports 8800-8807.
