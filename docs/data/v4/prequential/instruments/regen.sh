#!/usr/bin/env bash
# Authenticated regeneration of the retained manifests, frontier reports and attestations
# (recreated on disk after the tmpfs workspace was lost; identical to the session's earlier
# regen.sh).  Stage by stage: source candidates (3 apps + cellar sections) -> chains ->
# frontier replays -> summary.  Runs single-file authority under a hash-frozen compiler.
set -e
cd /home/moloch/semabi
A=".venv/bin/python -I -S -B scripts/v4_authority.py"
M=docs/data/v4/manifests; T=docs/data/v4/attestations
S=/home/moloch/semabi-scratch/preq/regen
mkdir -p $S
for app in "vet_clinic:vet_clinic_dev:vet_clinic_transfer:vet_clinic_holdout" \
           "harbour:harbour_dev:harbour_transfer:harbour_holdout" \
           "blend_book:grok_02_blend_book_dev:blend_book_transfer:blend_book_holdout"; do
  IFS=: read -r app src tr ho <<< "$app"
  $A --attestation $T/${app}_source_candidates.execution.json freeze-source --source runs/v4/$src \
     --output $M/${app}_source_candidates.json > $S/${app}_src.txt 2>&1 &
done
PYTHONPATH=/home/moloch/semabi .venv/bin/python scripts/v4_freeze_source_candidates.py --source runs/v4/opus_02_cellar_dev \
   --output $M/opus_02_cellar_dev_source_sections.json > $S/cellar_src.txt 2>&1 &
wait
for app in "vet_clinic:vet_clinic_dev:vet_clinic_transfer:vet_clinic_holdout" \
           "harbour:harbour_dev:harbour_transfer:harbour_holdout" \
           "blend_book:grok_02_blend_book_dev:blend_book_transfer:blend_book_holdout"; do
  IFS=: read -r app src tr ho <<< "$app"
  $A --attestation $T/${app}_chain.execution.json freeze-chain --source-manifest $M/${app}_source_candidates.json \
     --source runs/v4/$src --transfer runs/v4/$tr --holdout runs/v4/$ho --output $M/${app}_chain.json > $S/${app}_chain.txt 2>&1
done
for app in vet_clinic harbour blend_book; do
  $A --attestation $T/frontier_$app.execution.json replay --manifest $M/${app}_chain.json \
     --output docs/data/v4/frontier_$app.json > $S/${app}_replay.txt 2>&1 &
done
wait
PYTHONPATH=/home/moloch/semabi .venv/bin/python scripts/v4_frontier_summary.py > $S/summary.txt 2>&1 || true
echo REGEN_DONE > $S/done.txt
