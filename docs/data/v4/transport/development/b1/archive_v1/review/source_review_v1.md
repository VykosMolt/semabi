# B1 independent source review

**No blocking source defect found. Accepted for the deferred focused
before/after validation. Runtime validation has not run and is not accepted
by this review.** Integration or a repaired-outcome claim still requires the
owned, versioned validation evidence after root grants B1 the sole worker slot.

The reviewed candidate is isolated at
/home/moloch/semabi/runs/.b1_worktree, branch b1-incomplete-binding, based on
4440a4f534b4e8a32d836c7a710e6defe4002129. This reviewer did not author the
implementation or its tests. Review used the approved generalized contract,
the two production guards, existing and added tests, preserved independent
failure results and deferred validation commands.

## Mechanism and preserved boundaries

The singleton solver guard is correctly conditional on the actual accumulated
truncation flag. It retains the one Binding object with its values, provenance
and assignment evidence, returns UNSETTLED with truncated=True, and explicitly
states that uniqueness was not established. Truthiness still reflects the
retained assignment; unique becomes None, pinned remains empty and nonempty
target projection reports INCOMPLETE. The search domains, ordering, pruning,
node/answer bounds and traversal remain unchanged.

The distinction at an exact numeric bound is preserved. A later contradicted
candidate can be pruned without a refused recursive extension, so merely
reaching limit=1 or nodes=2 does not create truncation. Complete singleton,
complete contradiction, zero-answer truncation, complete multi-witness
agreement and witnessed target disagreement retain their existing branches.
The existing empty requested-target convention remains DETERMINED,0.

The consequence guard runs after representative fields, recursive identity and
binding-evidence metadata are collected, but before any verdict-return branch.
It uses the original bound.truncated flag rather than the number of deduplicated
parts. Any observed decided consequence makes the incomplete aggregate POSSIBLE;
empty or wholly UNKNOWN/NOT_APPLICABLE evidence makes it UNKNOWN. It therefore
blocks incomplete SUPPORTED, REFUTED and NOT_APPLICABLE claims centrally.

The detail counts actual retained assignments with len(bound.admissible) and
evaluated representatives with len(parts). It reports all five native
consequence counts and labels the retained winner.detail as representative
evidence. Lowercase assignment evidence supported is kept separately and cannot
enter the uppercase SUPPORTED consequence count. Empty parts have explicit zero
counts and no invented representative reason. The selected representative's
structured fields and both input collections remain untouched by the new guard.

Recursive identity uses the same aggregator and original bound, so the new
guard also sets the identity carrier's live binding_truncated flag and applies
the same verdict/count rules. The normal consequence.score path already
copies the solver status, count and flag; a repaired partial singleton reaches
its existing UNSETTLED-to-UNKNOWN gate before consequence evaluation. No JSON,
schema-label, target-projection or deduplication redesign is included.

An import-free AST comparison removed only the two new guards from copies of
the candidate syntax trees. Both resulting production ASTs exactly matched
their base snapshots. This mechanically confirms that the complete-search
logic and the other production mechanisms were not edited; it is not an
execution proof of their runtime behavior.

## Independent failure evidence and tests

The original JOIN result still records a limited singleton as UNIQUE with
truncated=False despite its independently known second target. The released
aggregation result separately retains all four Alpha/w0, Alpha/w1, Beta/w0 and
Beta/w1 assignments under complete search. Both limit=2 and nodes=4 retain only
the two Alpha assignments, correctly flag truncation, then deduplicate to one
native creation consequence.

The raw result contains the predeclared 12 creation cases and 30 direct
supplied-verdict controls. For Alpha-only pages, complete native parts are
SUPPORTED/REFUTED and the complete aggregate is POSSIBLE; bounded aggregation
incorrectly reports SUPPORTED. Beta-only pages produce the opposite partial
REFUTED claim despite a complete POSSIBLE result. Both defect flags remain
true under both limits. Original outputs and reports were read without
rewriting their defect flags. These are supplied-state diagnostics, not
observational learning evidence.

Seven added test functions declare 44 parametrized cases in the existing
tests/test_v4_binding.py. They cover:

- Both limits for true partial singletons, exact assignment/provenance/JSON,
  truthiness, uniqueness, pinned values and target status.
- Complete singletons at both exact bounds, including a contradicted tail.
- Sixteen complete/partial aggregation controls with exact observed counts,
  representative reasons, preserved structured evidence and unchanged inputs.
- Five recursive identity verdict cases, including the live truncation flag.
- Twelve native creation-dedup cases using both limits and all four raw-page
  controls, preserving native per-part verdicts and metadata.
- The score gate using the real limited solver and a forbidden consequence
  callback, plus incomplete witnessed target disagreement.

The existing helper that supplies an empty binding tuple is not used to assert
retained counts in the new evidence matrix. Its new cases construct real native
binding records. The actual creation test supplies the real caller's binding
count/status/flag and checks two retained assignments against one evaluated
representative. Complete controls preserve the existing order-dependent
UNKNOWN/NOT_APPLICABLE results rather than expanding B1 into another repair.

All three candidate files parse as Python without importing them. Candidate
and base bytes match their snapshots; the base files also match git objects at
4440a4f. No pytest collection, test execution, native import, learner fit,
browser action or corpus job was performed by this reviewer.

## Deferred execution

The reviewed run_focused_v1.sh selects 17 explicit test functions: the 44 new
cases and ten existing synthetic controls, for 54 declared cases per phase.
Every selected node name exists in the candidate AST. Source inspection found
no selected fit call; the selection avoids unrelated corpus-fitting tests in
the same file.

Before validation extracts semabi and test configuration from the immutable
base commit to a fresh temporary tree, then supplies the frozen candidate test
file. After validation uses the isolated candidate tree. The script checks the
respective native/test hashes, uses the same explicit selection and records
separate logs, JUnit XML, node IDs, resource settings, timestamps and exit codes.
Exclusive output-directory creation preserves earlier failures and successes.
The documented outer command supplies CPU23 affinity, nice19, idle I/O and
one numerical thread. These commands remain deferred pending root's worker
handover; G2 owns that worker during this review.

Before-run failures must be inspected for the intended contract failures.
An after-run pass, process reaping and input/source integrity checks remain
required. This review does not turn the declaration of 54 cases into 54 passes.

## Reviewed digests

Candidate-relative paths below are rooted in the isolated B1 worktree.
Control-relative paths are rooted at main
docs/data/v4/transport/development/join_native_control/.

| Scope | Artifact | SHA-256 |
| --- | --- | --- |
| Candidate | semabi/compiler/v4/binding.py | 0f905cae535aa975dffe517f1107884f37524fdc3cbcc781ec7f645cd0f9b0dc |
| Candidate | semabi/compiler/v4/consequence.py | c95bd040c8b066aaaac5bb5653b2ff20824ed3f2b59aba81c42b8a579ca8445e |
| Candidate | tests/test_v4_binding.py | d0c86811efbbce1dfbf92023cdbf8c52f26f9560ac9bf1dfabfa895772451278 |
| Candidate | docs/data/v4/transport/development/b1/candidate_v1.patch | b30e5ce17c311bd354116f762c4cd0b17831e901362b8384a8db0ebbb2794126 |
| Candidate | docs/data/v4/transport/development/b1/source_snapshots/candidate_v1/manifest.json | dba7b8c20bfbd8b95c749af1745def944bbea3be864278f13582ba400c45bb03 |
| Candidate | docs/data/v4/transport/development/b1/source_snapshots/base/manifest.json | c9a5661d259c8983cbf201b3aec4a55f7cf42411d4e7d7b752fcfadd680c0450 |
| Candidate | docs/data/v4/transport/development/b1/approved_design.md | e105dac41e1b60f28764d3d62fffbbfa46fe86d2f2919764793f71b3b0a8552b |
| Candidate | docs/data/v4/transport/development/b1/run_focused_v1.sh | 2c0873babe97dbd0fc55806da357066a03aaa9c1121eb002b04fd10507dc8e8a |
| Control | binding_truncation_design_v2.md | e105dac41e1b60f28764d3d62fffbbfa46fe86d2f2919764793f71b3b0a8552b |
| Control | run_v1/result.json | bcecfef87f737c8c57dd93f5871e8f43a6c89db5b3b3457d7c036c492e86b51e |
| Control | report.md | 09b4ce76e03abfbd9b5c1c7983ae9a9da75e08027f2506b650d76ccf831dd503 |
| Control | aggregation_run_v1/result.json | e48f67f36e81431a9773c5fe0fa8ccac9a60057b27efaf43fdcf583545a7f99b |
| Control | aggregation_report_v1.md | 5151e0511cbce57cfd9289d0dcdefd65347b9dcd28e998b8240f5b96293c1c85 |
| Control | aggregation_contract_v1.md | 772d0930d28f0c32e6e48a0ef14aa08b89575b5d8ff0119213249a98ad9e6ba3 |

All review commands used taskset -c 23, nice -n 19 and ionice -c 3.
The only review output is this main-checkout document. Main source and HEAD,
the isolated candidate source, and preserved experimental outputs were not
edited. No sealed fixture, oracle or reserved semantics were opened.
