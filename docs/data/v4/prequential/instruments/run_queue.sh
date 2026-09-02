#!/bin/bash
# Idempotent campaign runner. Safe to re-run at ANY time (after crash, reboot,
# or by accident): completed work is detected on disk and skipped; interrupted
# work resumes from its fit caches. At most 2 memory-capped workers ever run.
#
#   systemd-run --user --unit=preq-runner-$(date +%s) bash /home/moloch/semabi-scratch/preq/run_queue.sh
#
set -u
P=/home/moloch/semabi-scratch/preq
PY=/home/moloch/semabi/.venv/bin/python
exec 9>"$P/run_queue.lock"
flock -n 9 || { echo "runner already active"; exit 0; }
log() { echo "$(date +%H:%M:%S) $*" >> "$P/logs/runner.log"; }
log "=== runner start"

worker() {  # worker <unit-hint> <script> [args...]
  local hint=$1; shift
  systemd-run --user --scope --unit="preq-${hint}-$(date +%s)" \
    -p MemoryHigh=4G -p MemoryMax=6G -q \
    nice -n 19 env PYTHONPATH=/home/moloch/semabi "$PY" "$@" \
    >> "$P/logs/runner.log" 2>&1
  log "done: $hint (rc=$?)"
}

# ---- locked-corpus search (lane B head), once
if [ ! -f "$P/twin_search_locked.json" ]; then
  log "launch: twin-search-locked"
  worker twin-locked "$P/twin_search.py" \
    /home/moloch/semabi/runs/v4/twin_ledger_locked_dev "$P/twin_search_locked.json" &
fi

# ---- remaining boundaries, max 2 concurrent workers total
for t in 251 263 280 294 309 319 331 346 365; do
  if [ -f "$P/cells/t${t}.json" ] && ! grep -q '"partial"' "$P/cells/t${t}.json"; then
    log "skip: t${t} already complete"
    continue
  fi
  while [ "$(jobs -rp | wc -l)" -ge 2 ]; do wait -n; done
  log "launch: boundary t${t}"
  worker "t${t}" "$P/engine.py" boundary "$t" &
done
wait
log "boundaries + locked search complete"

# ---- provenance analysis
python3 "$P/analyse.py" > "$P/logs/analyse_final.out" 2>&1
log "analyse.py written to logs/analyse_final.out"

# ---- prefix schedule attacks at t188 and t263, sequential
for t in 188 263; do
  for s in production fwd rev buttonfirst rand1 rand2; do
    if [ -f "$P/logs/t${t}_${s}.json" ]; then
      log "skip: attack t${t} ${s} already done"
      continue
    fi
    log "launch: attack t${t} ${s}"
    worker "atk-${t}-${s}" "$P/attack.py" "$t" "$s"
  done
done
log "=== QUEUE_DONE"
touch "$P/QUEUE_DONE"
