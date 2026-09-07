#!/usr/bin/env bash
# Deferred reconstruction only; acquire the campaign's sole worker lease first.
set -euo pipefail

b1_phase=${1:?expected before or after}
b1_repository=${2:?expected a repository containing fixed base 4440a4f}
b1_python=${3:?expected the Python executable with the recorded test dependencies}
case "$b1_phase" in
    before) b1_snapshot=base ;;
    after) b1_snapshot=candidate_v1 ;;
    *) exit 2 ;;
esac
b1_archive=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
b1_repository=$(cd -- "$b1_repository" && pwd)
b1_run=$(mktemp -d "/tmp/semabi-b1-archive-${b1_phase}-v1.XXXXXX")
mkdir "$b1_run/source" "$b1_run/results"
b1_results="$b1_run/results"
date -u +%FT%TZ > "$b1_results/started_at_utc.txt"
taskset -pc $$ > "$b1_results/affinity.txt"
ionice -p $$ > "$b1_results/io_priority.txt"
ps -o pid=,ni=,args= -p $$ > "$b1_results/process.txt"

git -C "$b1_repository" archive 4440a4f534b4e8a32d836c7a710e6defe4002129 \
    semabi pyproject.toml pytest.ini | tar -x -C "$b1_run/source"
for b1_source in semabi/compiler/v4/binding.py semabi/compiler/v4/consequence.py; do
    cp "$b1_archive/source_snapshots/$b1_snapshot/$b1_source.txt" \
        "$b1_run/source/$b1_source"
done
mkdir "$b1_run/source/tests"
cp "$b1_archive/source_snapshots/candidate_v1/tests/test_v4_binding.py.txt" \
    "$b1_run/source/tests/test_v4_binding.py"
cd "$b1_run/source"
if [[ "$b1_phase" == before ]]; then
    sha256sum -c "$b1_archive/source_snapshots/base/native.sha256" \
        > "$b1_results/source_checks.txt"
    sha256sum -c "$b1_archive/source_snapshots/candidate_v1/tests.sha256" \
        >> "$b1_results/source_checks.txt"
else
    sha256sum -c "$b1_archive/source_snapshots/candidate_v1/native_and_tests.sha256" \
        > "$b1_results/source_checks.txt"
fi
printf '%s\n' "$PWD" > "$b1_results/source_directory.txt"
export PYTHONPATH="$PWD" PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1
"$b1_python" --version > "$b1_results/python_version.txt"
cp "$b1_archive/runtime/${b1_phase}_v1/selected_tests.txt" "$b1_results/selected_tests.txt"
mapfile -t b1_nodes < "$b1_results/selected_tests.txt"
if "$b1_python" -m pytest -q -p no:cacheprovider \
    --junitxml="$b1_results/junit.xml" "${b1_nodes[@]}" > "$b1_results/pytest.log" 2>&1; then
    b1_exit=0
else
    b1_exit=$?
fi
printf '%s\n' "$b1_exit" > "$b1_results/exit_code.txt"
date -u +%FT%TZ > "$b1_results/finished_at_utc.txt"
printf '%s reconstruction: pytest exit %s; new evidence %s\n' \
    "$b1_phase" "$b1_exit" "$b1_results"
exit "$b1_exit"
