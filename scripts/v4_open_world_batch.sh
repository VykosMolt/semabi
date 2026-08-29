#!/usr/bin/env bash
# Every report docs/v4_open_world.md quotes, on top of scripts/v4_identity_batch.sh: the
# version space and the chosen list on a history nothing was fitted on, the causal-prequential
# boundary, and the renaming instrument.  All in parallel; about an hour, bounded by the
# prequential runs, which refit the model before every scored action.
set -u
cd "$(dirname "$0")/.."
V=${V:-.venv/bin/python}
M=docs/data/v4/manifests
D=docs/data/v4
W=${W:-/tmp/semabi_open_world}
mkdir -p $W

bash scripts/v4_identity_batch.sh > $D/log_open_world_identity.txt 2>&1 &
$V -m semabi.eval.v4_admissible --run runs/v4/harbour_transfer --chain $M/harbour_chain.json \
   --reading "joint discrimination x2" --split 1.0 --score-on runs/v4/harbour_holdout > $D/log_open_world_xhist_harbour.txt 2>&1 &
$V -m semabi.eval.v4_admissible --run runs/v4/blend_book_transfer --chain $M/blend_book_chain.json \
   --reading "joint discrimination x3" --split 1.0 --score-on runs/v4/blend_book_holdout > $D/log_open_world_xhist_blend.txt 2>&1 &
$V -m semabi.eval.v4_inadequacy --run runs/v4/harbour_transfer --chain $M/harbour_chain.json \
   --reading "joint discrimination x2" --split 1.0 --score-on runs/v4/harbour_holdout \
   --out $D/inadequacy_harbour_transfer_on_holdout.json > /dev/null 2>&1 &
$V -m semabi.eval.v4_inadequacy --run runs/v4/blend_book_transfer --chain $M/blend_book_chain.json \
   --reading "joint discrimination x3" --split 1.0 --score-on runs/v4/blend_book_holdout \
   --out $D/inadequacy_blend_book_transfer_on_holdout.json > /dev/null 2>&1 &
$V -m semabi.eval.v4_outcome --run runs/v4/blend_book_transfer --chain $M/blend_book_chain.json \
   --reading "joint discrimination x3" --split 0.5 --control "Record draw" \
   --out outcome_blend_book_transfer_split05.json > /dev/null 2>&1 &
$V -m semabi.eval.v4_outcome --run runs/v4/blend_book_transfer --chain $M/blend_book_chain.json \
   --reading "joint discrimination x3" --split 1.0 --control "Record draw" --no-ablation \
   --score-on runs/v4/blend_book_holdout --out outcome_blend_book_cross_trace.json > /dev/null 2>&1 &
$V -m semabi.eval.v4_outcome --run runs/v4/harbour_transfer --chain $M/harbour_chain.json \
   --reading "joint discrimination x2" --split 0.5 --out outcome_harbour_transfer_split05.json > /dev/null 2>&1 &
$V -m semabi.eval.v4_outcome --run runs/v4/harbour_transfer --chain $M/harbour_chain.json \
   --reading "joint discrimination x2" --split 1.0 --no-ablation \
   --score-on runs/v4/harbour_holdout --out outcome_harbour_cross_trace.json > /dev/null 2>&1 &
$V -m semabi.eval.v4_admissible_prequential --run runs/v4/blend_book_transfer --chain $M/blend_book_chain.json \
   --reading "joint discrimination x3" --split 0.5 --stride 8 > $D/log_open_world_prequential_blend.txt 2>&1 &
$V -m semabi.eval.v4_admissible_prequential --run runs/v4/harbour_transfer --chain $M/harbour_chain.json \
   --reading "joint discrimination x2" --split 0.5 --stride 4 > $D/log_open_world_prequential_harbour.txt 2>&1 &
for app in "harbour_transfer:harbour_chain.json:joint discrimination x2:harbour_holdout:harbour" \
           "blend_book_transfer:blend_book_chain.json:joint discrimination x3:blend_book_holdout:blend_book" \
           "vet_clinic_transfer:vet_clinic_chain.json:joint discrimination x3:vet_clinic_holdout:vet_clinic" \
           "opus_02_cellar_dev:opus_02_cellar_dev_source_sections.json:joint discrimination x3:cellar_seed11:cellar"; do
  IFS=: read -r run chain reading other name <<< "$app"
  $V -m semabi.eval.v4_metamorphic --run runs/v4/$run --chain $M/$chain --reading "$reading" \
     --score-on runs/v4/$other --workdir $W/reversed_$name --out $D/reversal_$name.json > /dev/null 2>&1 &
done
# renaming: every name that only identifies, replaced (fresh) or permuted; the version
# space, the chosen list and the durable ledger compared at every click
for app in "harbour_transfer:harbour_chain.json:joint discrimination x2:harbour_holdout:harbour" \
           "blend_book_transfer:blend_book_chain.json:joint discrimination x3:blend_book_holdout:blend_book" \
           "vet_clinic_transfer:vet_clinic_chain.json:joint discrimination x3:vet_clinic_holdout:vet_clinic" \
           "opus_02_cellar_dev:opus_02_cellar_dev_source_sections.json:joint discrimination x3:cellar_seed11:cellar"; do
  IFS=: read -r run chain reading other name <<< "$app"
  for mode in fresh permute; do
    $V -m semabi.eval.v4_renaming --run runs/v4/$run --chain $M/$chain --reading "$reading" \
       --score-on runs/v4/$other --mode $mode --workdir $W/${name}_$mode \
       --out $D/renaming_${name}_$mode.json > /dev/null 2>&1 &
  done
done
# can behaviour before the cut choose among readings, and does the suffix agree
for app in "vet_clinic_transfer:vet_clinic_chain.json:joint discrimination x3:vet_clinic" \
           "harbour_transfer:harbour_chain.json:joint discrimination x2:harbour" \
           "blend_book_transfer:blend_book_chain.json:joint discrimination x3:blend_book" \
           "opus_02_cellar_dev:opus_02_cellar_dev_source_sections.json:joint discrimination x3:cellar"; do
  IFS=: read -r run chain reading name <<< "$app"
  $V -m semabi.eval.v4_reading_selection --run runs/v4/$run --chain $M/$chain \
     --out reading_selection_$name.json > /dev/null 2>&1 &
  $V -m semabi.eval.v4_reading_selection --run runs/v4/$run --chain $M/$chain --ablate "$reading" \
     --out reading_ablation_$name.json > /dev/null 2>&1 &
done
# what a control's label says against what it does
$V -m semabi.eval.v4_roles --run runs/v4/blend_book_transfer --chain $M/blend_book_chain.json \
   --reading "joint discrimination x3" --out $D/roles_blend_book_transfer.json > /dev/null 2>&1 &
$V -m semabi.eval.v4_roles --run runs/v4/harbour_transfer --chain $M/harbour_chain.json \
   --reading "joint discrimination x2" --out $D/roles_harbour_transfer.json > /dev/null 2>&1 &
wait
