# Source-derived scheduling assessment

The inspected paths support overlapping the five corpus jobs with the sole
canonical full suite. This recommendation assumes frozen reviewed source,
already-existing input directories, exclusive case outputs and distinct
bytecode prefixes. It is not a runtime write trace or a general purity claim
about every public compiler API. Root decides against actual host allocation.

`run_corpus.py.template` creates only `corpora/<case>`, copies its source
snapshot there, and writes adapter/origin/postflight records there. It sets
`SEMABI_BASELINE_CORPORA` and the unchanged measurement module's `OUT` only in
its own interpreter. The outer runner writes only that job's directory.

The unchanged `baseline/check_corpora.py` writes its process, fit, partial and
complete result JSON under `OUT`. It hashes the files under its case's dev/hold
pair before and after measurement. Its learner path is:

1. `link_probe.settled_reading` constructs `EvidenceLog`, builds hypotheses,
   calls `search`, and converts the result using `pinned.from_search`.
2. `search.search` works on copied hypotheses and reads the optional refutation
   sidecar. It does not call the separate `write_refutation` API.
   `pinned.from_search` also reads that sidecar and returns an in-memory reading;
   it does not call `pinned.save`.
3. `consequence.fit` calls `compile_v4` with `write_diagnostics=False`, a pinned
   reading and an `evidence_log`. The compile boundary independently disables
   diagnostics whenever that evidence view is supplied. The identity/model/log
   write branches and `LearnedModel.save` are therefore not reached.
4. Development and holdout scoring use the compiled in-memory model and
   evidence. `EvidenceLog.__init__` invokes `mkdir(exist_ok=True)` on an existing
   input directory and reads observations/steps. Its append methods and the
   other persistence APIs are not called on this path.

The inspected objective, inducer, abstractor, identity and outcome code contains
no reached file-write operation on that route. All 45 inputs are shared only
as readers; separating and separating_extended intentionally share the same
holdout input directory. No canonical test refers to that corpus root or its
case directory names. The 18 retained full-suite inputs occupy three separate
directories: harbour_transfer, blend_book_transfer and harbour_dev.

`tests/test_v4_manifests.py` creates private `.pytest-v4-manifest-*` directories
under the worktree and removes each in fixture teardown. Its repaired
`_installed_cache` uses the test's own `bytecode` root, temporarily changes only
that interpreter's `sys.pycache_prefix`, restores it, and leaves authenticated
`.py` bytes and mtime untouched. It writes no corpus prefix or corpus input.

`tests/test_v4_execution_authority.py` creates synthetic candidate repositories,
forged sources, launchers and caches beneath `tmp_path`. Its private site-package
directories are also beneath that scratch. Its cache-prefix changes are local
to the pytest interpreter; synthetic child interpreters use their documented
isolated startup flags. The corpus interpreters neither read those fixture
roots nor share the pytest ambient prefix. The relevant native and runtime
source files are shared as readers.

The full-suite freeze binds explicit files and native/test membership, not
new output directories. The corpus guard binds the same native/input bytes,
not the full-suite scratch directories. Independent output growth therefore
does not violate either existing guard's declared inventory scope.

The proposed six-CPU allocation is full suite CPU 6 and the corpora in declared
order on CPUs 10 through 14. Canonical pytest remains serial and no second
authentication-sensitive job may overlap it. All library thread limits stay
at one. Root must verify those CPUs are idle/allowed and that all admitted work
remains within the 24-core cap immediately before launch, then retain runtime
affinity/resource and final termination evidence. If that condition or this
scoped disjointness is not accepted, `commands_v1.json` retains the serial
schedule. No native run was performed to reach this assessment.

`scheduling_source_evidence_v1.json` records the exact inspected paths, hashes
and relevant function ranges. It is preparation evidence, not a final source
freeze or GO.
