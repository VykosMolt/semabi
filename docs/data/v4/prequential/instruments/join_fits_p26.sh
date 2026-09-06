#!/bin/bash
# P26: merge the pilot-booking dev corpus, inspect Book pilot under both readings, score
# the dev-fitted model on the pilot holdout under both readings.  Runs under the main tree.
P=/home/moloch/semabi-scratch/preq
S=/tmp/claude-1000/-home-moloch-semabi/cbdd0615-d7c0-4fae-b02c-d64c20b5ee38/scratchpad
R=/home/moloch/semabi; V=$R/.venv/bin/python
CHAIN=docs/data/v4/manifests/harbour_chain.json
CTRL="button:Book pilot"
cd $P && python3 join_merge.py harbour_pil_dev $R/runs/v4/harbour_dev logs/result_join_pil51.json logs/result_join_pil52.json logs/result_join_pil53.json || exit 1
cd $R
for mode in search chain; do
  if [ $mode = search ]; then args="search search"; else args="$CHAIN source_choice"; fi
  nice -n 5 env PYTHONPATH=$R SEMABI_ROOT=$R $V $P/join_inspect.py $P/harbour_pil_dev $args "$CTRL" $S/p26_inspect_$mode.json > $S/p26_inspect_$mode.log 2>&1 &
  nice -n 5 env PYTHONPATH=$R SEMABI_ROOT=$R $V $P/join_score.py $P/harbour_pil_dev $P/harbour_pil_hold $args $S/p26_score_$mode.json "$CTRL" > $S/p26_score_$mode.log 2>&1 &
done
wait
echo done > $S/P26_FITS_DONE
