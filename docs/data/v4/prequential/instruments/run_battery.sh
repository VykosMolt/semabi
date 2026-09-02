#!/bin/bash
# Full retained-state regeneration after the harbour sidecar changes: authenticated
# manifests + frontiers + summary (regen.sh), then every batch that consumes the chains.
# Detached and idempotent enough to re-run: each stage writes a marker; finished stages
# are skipped.  Launch with:
#   systemd-run --user --slice=preq.slice --unit=preq-battery-$(date +%s) -p MemoryMax=20G \
#     bash /home/moloch/semabi-scratch/preq/run_battery.sh
set -u
cd /home/moloch/semabi
P=/home/moloch/semabi-scratch/preq
S=$P/battery; mkdir -p $S
log() { echo "$(date +%H:%M:%S) $*" >> $S/battery.log; }
stage() {  # stage <name> <command...>
  local name=$1; shift
  if [ -f "$S/$name.done" ]; then log "skip: $name"; return 0; fi
  log "start: $name"
  nice -n 19 "$@" > "$S/$name.out" 2>&1
  local rc=$?
  log "end: $name (rc=$rc)"
  [ $rc -eq 0 ] && touch "$S/$name.done"
  return $rc
}
log "=== battery start"
stage regen bash $P/regen.sh
stage open_world bash scripts/v4_open_world_batch.sh
stage identity bash scripts/v4_identity_batch.sh
stage outcome bash scripts/v4_outcome_batch.sh
stage admissible bash scripts/v4_admissible_batch.sh
log "=== BATTERY_DONE"
touch $S/BATTERY_DONE
