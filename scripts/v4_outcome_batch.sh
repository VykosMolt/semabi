#!/usr/bin/env bash
# Every outcome-layer number in docs/v4_outcomes.md, and the controls for them.
# Each writes its report to docs/data/v4/.  Around 40 minutes end to end.
set -e
cd "$(dirname "$0")/.."
V=${V:-.venv/bin/python}
M=docs/data/v4/manifests

$V -m semabi.eval.v4_outcome --run runs/v4/blend_book_transfer --chain $M/blend_book_chain.json \
   --reading "joint discrimination x3" --split 0.5 --control "Record draw" \
   --out outcome_blend_book_transfer_split05.json
$V -m semabi.eval.v4_outcome --run runs/v4/blend_book_transfer --chain $M/blend_book_chain.json \
   --reading "joint discrimination x3" --split 0.7 --control "Record draw" \
   --out outcome_blend_book_transfer_split07.json
# the control for the whole layer: the same learner on shuffled events
$V -m semabi.eval.v4_outcome --run runs/v4/blend_book_transfer --chain $M/blend_book_chain.json \
   --reading "joint discrimination x3" --split 0.7 --control "Record draw" --no-ablation \
   --permute 7 --out outcome_blend_book_transfer_permuted.json
# a second interaction history, none of which was fitted
$V -m semabi.eval.v4_outcome --run runs/v4/blend_book_transfer --chain $M/blend_book_chain.json \
   --reading "joint discrimination x3" --split 1.0 --control "Record draw" --no-ablation \
   --score-on runs/v4/blend_book_holdout --out outcome_blend_book_cross_trace.json
$V -m semabi.eval.v4_outcome --run runs/v4/harbour_transfer --chain $M/harbour_chain.json \
   --reading "joint discrimination x2" --split 0.5 \
   --out outcome_harbour_transfer_split05.json
$V -m semabi.eval.v4_outcome --run runs/v4/harbour_transfer --chain $M/harbour_chain.json \
   --reading "joint discrimination x2" --split 1.0 --no-ablation \
   --score-on runs/v4/harbour_holdout --out outcome_harbour_cross_trace.json
$V -m semabi.eval.v4_outcome --run runs/v4/opus_02_cellar_dev --chain $M/opus_02_cellar_dev_source.json \
   --reading "joint discrimination x2" --split 0.5 \
   --out outcome_opus_02_cellar_dev_split05.json
$V -m semabi.eval.v4_outcome --run runs/v4/vet_clinic_transfer --chain $M/vet_clinic_chain.json \
   --reading "joint discrimination x3" --split 0.5 \
   --out outcome_vet_clinic_transfer_split05.json
for app in "blend_book_transfer:blend_book_chain.json:joint discrimination x3:0.7" \
           "harbour_transfer:harbour_chain.json:joint discrimination x2:0.5" \
           "opus_02_cellar_dev:opus_02_cellar_dev_source.json:joint discrimination x2:0.5" \
           "vet_clinic_transfer:vet_clinic_chain.json:joint discrimination x3:0.5"; do
  IFS=: read -r run chain reading split <<< "$app"
  $V -m semabi.eval.v4_state_fidelity --run runs/v4/$run --chain $M/$chain \
     --reading "$reading" --split "$split" --tracked
done
