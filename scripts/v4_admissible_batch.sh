#!/usr/bin/env bash
# Every number in docs/v4_admissibility.md except the acquisition runs, which need the
# applications running and are listed at the bottom.  Around 25 minutes on one core.
set -e
cd "$(dirname "$0")/.."
V=${V:-.venv/bin/python}
M=docs/data/v4/manifests

for app in "blend_book_transfer:blend_book_chain.json:joint discrimination x3" \
           "harbour_transfer:harbour_chain.json:joint discrimination x2" \
           "opus_02_cellar_dev:opus_02_cellar_dev_source.json:joint discrimination x2" \
           "vet_clinic_transfer:vet_clinic_chain.json:joint discrimination x3"; do
  IFS=: read -r run chain reading <<< "$app"
  $V -m semabi.eval.v4_admissible --run runs/v4/$run --chain $M/$chain \
     --reading "$reading" --split 0.5
  $V -m semabi.eval.v4_bundle --run runs/v4/$run --chain $M/$chain \
     --reading "$reading" --split 0.5
done

# The acquisition runs drive the applications.  Start them first:
#   bash ~/semabi-gauntlet-v3/run_all.sh
# The seed must be one the retained trace never used -- blend resets to 1200.., cellar to 0-5 --
# because acquiring at a seed the trace itself replays re-observes the held-out answers.  A
# cellar run at seed 5 did exactly that and its result was withdrawn.
#
# $V -m semabi.eval.v4_acquire --run runs/v4/blend_book_transfer --chain $M/blend_book_chain.json \
#    --reading "joint discrimination x3" --split 0.5 --control "button:Record draw" \
#    --button "Record draw" --base http://127.0.0.1:8901 --seed 7 --policy uncertain
# $V -m semabi.eval.v4_acquire ... --policy any        # the matched control
# $V -m semabi.eval.v4_acquire --run runs/v4/opus_02_cellar_dev \
#    --chain $M/opus_02_cellar_dev_source.json --reading "joint discrimination x2" \
#    --split 0.5 --control "button:Move vessel" --button "Move vessel" \
#    --base http://127.0.0.1:8911 --seed 91 --policy unestablished

# The four mechanisms this run measured and rejected are keyword arguments on
# `outcome.learn` -- structural, touched, about, simplest -- all off by default, so everything
# above is the default configuration.  `docs/v4_admissibility.md` has the tables.
#
# The one combination that changes a result is cellar's `Move vessel` refitted after
# acquisition with `touched=True`: the evidence then holds the application's own guard
# (something chosen in the vessel list, nothing in the hall list) instead of a memorised key,
# and its four held-out actions are honest refusals.  That needs the app running and a
# functools.partial around outcome.learn; it is not a default and is not scripted here.
