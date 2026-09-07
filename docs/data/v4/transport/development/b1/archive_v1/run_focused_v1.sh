#!/usr/bin/env bash
# Run only after root grants B1 the campaign's sole CPU-worker lease.
set -euo pipefail

b1_phase=${1:?expected before or after}
case "$b1_phase" in before|after) ;; *) exit 2 ;; esac
b1_root=/home/moloch/semabi/runs/.b1_worktree
b1_evidence="$b1_root/docs/data/v4/transport/development/b1"
b1_candidate="$b1_evidence/source_snapshots/candidate_v1"
b1_result="$b1_evidence/runtime/${b1_phase}_v1"
b1_python=/home/moloch/semabi/.venv/bin/python
mkdir -p "$b1_evidence/runtime"
mkdir "$b1_result"                    # Never replace an earlier run or failure log.
date -u +%FT%TZ > "$b1_result/started_at_utc.txt"
taskset -pc $$ > "$b1_result/affinity.txt"
ionice -p $$ > "$b1_result/io_priority.txt"
ps -o pid=,ni=,args= -p $$ > "$b1_result/process.txt"

if [[ "$b1_phase" == before ]]; then
    b1_directory=$(mktemp -d /tmp/semabi-b1-before-v1.XXXXXX)
    git -C "$b1_root" archive 4440a4f534b4e8a32d836c7a710e6defe4002129 \
        semabi pyproject.toml pytest.ini | tar -x -C "$b1_directory"
    mkdir "$b1_directory/tests"
    cp "$b1_candidate/tests/test_v4_binding.py" "$b1_directory/tests/test_v4_binding.py"
    cd "$b1_directory"
    sha256sum -c "$b1_evidence/source_snapshots/base/native.sha256" \
        > "$b1_result/source_checks.txt"
    sha256sum -c "$b1_candidate/tests.sha256" >> "$b1_result/source_checks.txt"
else
    b1_directory="$b1_root"
    cd "$b1_directory"
    sha256sum -c "$b1_candidate/native_and_tests.sha256" > "$b1_result/source_checks.txt"
fi
printf '%s\n' "$b1_directory" > "$b1_result/source_directory.txt"
export PYTHONPATH="$b1_directory"
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0
"$b1_python" --version > "$b1_result/python_version.txt"

b1_tests=(
    test_a_partial_singleton_does_not_establish_uniqueness
    test_a_complete_singleton_at_its_bounds_remains_unique
    test_incomplete_aggregation_preserves_only_observed_evidence
    test_incomplete_aggregation_reaches_recursive_identity
    test_creation_deduplication_does_not_complete_a_partial_search
    test_score_abstains_on_a_partial_singleton
    test_two_observed_targets_remain_underdetermined_when_search_is_incomplete
    test_many_witnesses_one_target_is_not_ambiguity
    test_two_assignments_disagreeing_about_the_target_is_ambiguity
    test_agreement_among_the_assignments_reached_is_not_determinacy
    test_a_search_that_cannot_finish_says_so_instead_of_running
    test_a_truncated_enumeration_pins_nothing
    test_an_enumeration_that_stopped_early_can_never_refute
    test_one_assignment_that_works_stops_a_refutation
    test_an_assignment_that_could_not_be_tested_counts_against_refuting
    test_a_contradicted_precondition_leaves_no_assignment
    test_a_type_that_is_not_rendered_here_is_ignorance_not_non_applicability
)
b1_nodes=()
for b1_test in "${b1_tests[@]}"; do
    b1_nodes+=("tests/test_v4_binding.py::$b1_test")
done
printf '%s\n' "${b1_nodes[@]}" > "$b1_result/selected_tests.txt"
if "$b1_python" -m pytest -q -p no:cacheprovider \
    --junitxml="$b1_result/junit.xml" "${b1_nodes[@]}" > "$b1_result/pytest.log" 2>&1; then
    b1_exit=0
else
    b1_exit=$?
fi
printf '%s\n' "$b1_exit" > "$b1_result/exit_code.txt"
date -u +%FT%TZ > "$b1_result/finished_at_utc.txt"
printf '%s: pytest exit %s; evidence %s\n' "$b1_phase" "$b1_exit" "$b1_result"
exit "$b1_exit"
