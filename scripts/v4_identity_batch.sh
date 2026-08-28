#!/usr/bin/env bash
# The reports behind docs/v4_identity.md: what the version space establishes under each
# hypothesis class, why its confident errors were wrong, and the operator layer's per-action
# ledger -- on every application with a live region, after the control-identity repair.
# Each writes to docs/data/v4/.  Ten minutes on four cores; the runs are independent.
set -e
cd "$(dirname "$0")/.."
V=${V:-.venv/bin/python}
M=docs/data/v4/manifests
D=docs/data/v4

for app in "blend_book_transfer:blend_book_chain.json:joint discrimination x3" \
           "harbour_transfer:harbour_chain.json:joint discrimination x2" \
           "opus_02_cellar_dev:opus_02_cellar_dev_source_sections.json:joint discrimination x3"; do
  IFS=: read -r run chain reading <<< "$app"
  (
    $V -m semabi.eval.v4_admissible --run runs/v4/$run --chain $M/$chain --reading "$reading" --split 0.5
    $V -m semabi.eval.v4_admissible --run runs/v4/$run --chain $M/$chain --reading "$reading" --split 0.5 \
       --hypothesis list --out admissible_${run}_frozen_prefix_list.json
    $V -m semabi.eval.v4_inadequacy --run runs/v4/$run --chain $M/$chain --reading "$reading" --split 0.5 \
       --out $D/inadequacy_${run}.json
    $V -m semabi.eval.v4_claim_substance --run runs/v4/$run --chain $M/$chain --reading "$reading" --split 0.5
  ) > $D/log_identity_$run.txt 2>&1 &
done
$V -m semabi.eval.v4_claim_substance --run runs/v4/vet_clinic_transfer --chain $M/vet_clinic_chain.json \
   --reading "joint discrimination x3" --split 0.5 > $D/log_identity_vet_clinic_transfer.txt 2>&1 &
wait
