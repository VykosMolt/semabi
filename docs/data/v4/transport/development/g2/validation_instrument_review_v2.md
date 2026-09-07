# G2 validation-instrument review, revision 2

2026-09-07. **No blocking issue remains in the reviewed validation candidates.**
Read-only review of the revised validation plan, phase freezer,
corpus adapter and new G1-to-G2 comparator. This report leaves the first review
unchanged. No candidate instrument, compiler fit, fixture, or test was run;
Python source was parsed with `ast.parse`, and metadata was read and hashed.
No integrated G2 result is asserted.

The reviewer did not author these instruments. The reviewer authored the
chronology counterexample, reviewed the isolated G2 implementation, and wrote
the first instrument review; that prior design exposure is disclosed. No shared
fixture implementation, reserved content, or hidden oracle contract was read.

## Resolution of the first review

Both initial findings are resolved in the revised candidates:

* `validation_plan.md` now gives the required `run_job.py` corpus invocation
  and requires the launcher for the full suite and comparator. `run_corpus.py`
  rejects a missing/nonzero `PYTHONHASHSEED` and any of the four numerical
  thread settings that differs from one. The preserved launcher sets those
  variables before starting Python, so the plan does not rely on changing
  hash behavior after interpreter initialization.
* `compare_corpora.py` and the plan now define the exact six-component
  projection: `reading`, `fit`, `dev_steps`, `outcome_cut`, `development`, and
  `holdout`. Only top-level execution provenance and
  `reading.provenance.source_run` are omitted. Dictionaries are compared over
  the union of keys, lists retain positional order and extra elements, scalar
  and type differences are retained, and every difference is emitted. There
  is no threshold-box normalization, rule simplification, visible-check
  overlay, or requirement that the differences be empty.

The freezer records the comparator and the preserved G1 results manifest as
verification dependencies. The comparator authenticates that manifest under
the G2 freeze, authenticates G1 result bytes against it, requires matching
corpus manifests and consumed-input maps, and checks each phase's snapshot
and successful job against its own source. This avoids comparing a G2 result
to a baseline with a different seed or relabeling G1 scores as G2.

The original three proposal files were independently rehashed under
`instrument_revisions/v1_before_review/` (their stored names end in `.txt`).
All matched the first review's fingerprints. The first review still has SHA-256
`d1fa5ef74dc51576e9f1b6079a72e538e1a1f9c773be4b0b8b6f31621c730916`.

## Additional result-to-job association check

The first comparator revision, SHA-256
`8a38a58ec3accffbde95cedf5ddc327df8eb0464ff3a1ceb02f898cbe0f509c5`,
verified an outer job and phase snapshot without reading the final inner
`<case>_process.json`. The outer job contains no result digest. Consequently,
those checks alone did not establish that the compared result bytes were the
completed measurement's output.

The existing measurement already records a final `state=completed`, case,
`result_sha256`, source snapshot, instrument digest and `changed_inputs` in
the inner process record. The review requested verification of that record
against the actual result, plus the expected outer command's case/output/freeze
and the full four-key thread-limit map. The result file itself deliberately
contains the earlier running provenance; requiring it to say `completed` would
reject valid output. The final inner record is the correct completion evidence.

The final comparator, SHA-256
`6a4c7eedcfd6143581a8cd75e47c0459b48ac8614657fcf0e0a615d1558ad001`,
resolves this finding. It reads and rehashes the inner record, requires its
completed state and matching case, verifies its result digest against actual
result bytes, checks unchanged inputs and the exact consumed-input map, and
authenticates snapshot and measurement digests. For G1 it also authenticates
that inner record against the preserved results manifest. It verifies the
outer job's exact adapter/case/output/freeze command, working directory,
source HEAD, complete four-key thread map, hash seed, successful completion,
log digest and phase-specific runtime-source hashes. The former comparator
bytes were independently checked in
`instrument_revisions/compare_v1_before_inner_link_review.py.txt` and match
their recorded fingerprint.

Safe metadata checks confirmed these required completion/digest/command/
environment fields match all five existing G1 corpus records. The candidate
comparator itself was not executed. Its recursive comparison still retains
every non-provenance value, type, key, list-order and list-length difference.

## Final reviewed fingerprints and acceptance scope

```
3a72fdf09962e8132e2fe40b7fa33a174125837d313cede13f6ce9e4cf139b9d  validation_plan.md
28051db11556b83ee81012a8136119c8eda3ac59be01bb41e4293ee793b9b3a3  freeze_development.py
e2c8b75cd7003855aceceddb322b2cd9e7f2302bf8c734acde50bc26152cbd87  run_corpus.py
6a4c7eedcfd6143581a8cd75e47c0459b48ac8614657fcf0e0a615d1558ad001  compare_corpora.py
```

All three Python files parse successfully under `ast.parse`; that checks
syntax without executing their code. The source and custody checks accepted
in the first review remain applicable. No request to modify learner semantics
or discard a residual difference is made here.

The G1 results manifest and integrated G2 artifact copy are prerequisites of
the proposed freeze and were not yet installed at review time. The freezer
must authenticate those actual files before any G2 measurement; this review
does not substitute for that check. Full-suite and corpus execution, source
stability through completion, process reaping and final result review remain
required. Acceptance here is of the exact instrument candidates and declared
comparison contract, not of unexecuted G2 results.
