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
for mode in fresh permute; do
  $V -m semabi.eval.v4_renaming --run runs/v4/harbour_transfer --chain $M/harbour_chain.json \
     --reading "joint discrimination x2" --score-on runs/v4/harbour_holdout --mode $mode \
     --workdir $W/harbour_$mode --out $D/renaming_harbour_$mode.json > /dev/null 2>&1 &
  $V -m semabi.eval.v4_renaming --run runs/v4/blend_book_transfer --chain $M/blend_book_chain.json \
     --reading "joint discrimination x3" --score-on runs/v4/blend_book_holdout --mode $mode \
     --workdir $W/blend_$mode --out $D/renaming_blend_book_$mode.json > /dev/null 2>&1 &
done
wait
