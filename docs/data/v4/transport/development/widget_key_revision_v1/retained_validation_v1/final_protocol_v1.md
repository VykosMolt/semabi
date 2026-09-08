# W3 gate after the reviewed source checkpoint

Root committed `aaa9b5df915464754341794179b5297cf22f6140`, parent
`a1c0bc96d6a9725a3f23e18dbc96f97b0bd38f08`, containing only the four reviewed
W3 native/test files. Root accepted the v4 source/result review, copied the
exact 45 corpus files and verified the 18 existing suite files. The unchanged
`root_input_copy_v1.json` has SHA-256
`72bfcd5a62c9b7878cf476aa0a01f8f10c7ab44f350d0d696b384fdfa4d86620`.

The earlier plan and serial command record remain preparation history.
`command_templates_v2.json` records the accepted source-derived concurrent
schedule: one canonical serial full suite on CPU 6; allocation_positive on 10,
allocation_refusals on 11, pilot on 12, separating on 13 and
separating_extended on 14. The one later comparison uses CPU 15 after all six
native jobs are reaped and the required completed corpus results and custody
are checked. Root must still confirm live CPU availability and the aggregate
24-core cap immediately before launch. No other authentication-sensitive job
may overlap the suite.

`rendering_receipt_v1.json` binds the five reviewed templates to their rendered
files. Rendering only substitutes the committed HEAD in the guard; the other
four files remain byte-identical to their templates. The full helper remains
byte-identical to accepted W1. No instrument or native module was executed
during rendering or static checks.

`freeze_preparation_v1.py` is a single-purpose metadata preparation adapted from
the accepted W1 freeze inventories and canonical full-suite schema. It checks
the exact reviewed changes, clean HEAD, current tracked/native/test membership,
retained runtime/dependency bytes, input copies, discovery/runtime metadata and
rendered instrument hashes. It imports only the standard library. Its exclusive
outputs are source_freeze_v1.json, corpus_freeze_v1.json,
full_suite_source_freeze_v1.json, the fully bound commands_v2.json and its
creation receipt. No GO or native execution is part of that preparation.

The source/corpus pair binds the shared corpus guard/adapter/comparator and
exact inputs. The full-suite freeze separately binds canonical discovery and
its full entrypoint, plus that source/corpus pair and held evidence. The concrete
command record is written after all three digests exist, avoiding a hash cycle.
Every command uses `-P -B`, empty PYTHONPATH, PYTHONOPTIMIZE=0, disabled bytecode
writes, hash seed zero and six one-thread library settings. A job's absent
prefix is `/tmp/semabi_w3_gate_<job-identity>_v1_no_pyc`; the complete literal
paths appear in the command record. No prefix directory is created or cleaned
by preparation.

Root independently reviews and rechecks the resulting freezes and exact argv,
then issues a separate GO and owns every launch, terminal receipt, custody
check and result acceptance. The six-component semantic scope, complete
residual rows, primary-interpreter limitations and separate preservation versus
acceptance decisions remain as specified in plan_v1.md and
result_contract_v1.json.
