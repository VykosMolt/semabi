#!/bin/bash
# JOIN attack.  dev: merge base + join + join2, fit the outcome layer on it, report the
# field theory and the Allocate berth control.  holdout: merge base + seeds 11-13, score
# the dev-fitted model on it, under the new code and under HEAD (worktree $S/base).
set -e
P=/home/moloch/semabi-scratch/preq
S=/tmp/claude-1000/-home-moloch-semabi/cbdd0615-d7c0-4fae-b02c-d64c20b5ee38/scratchpad
R=/home/moloch/semabi
V=$R/.venv/bin/python
CHAIN=docs/data/v4/manifests/harbour_chain.json
CTRL="button:Allocate berth"
cd $R
case "$1" in
  dev)
    python3 $P/join_merge.py $P/harbour_join_dev runs/v4/harbour_dev $P/logs/result_join_harbour.json $P/logs/result_join_harbour2.json
    PYTHONPATH=$R $V -m semabi.eval.v4_field_theory --run $P/harbour_join_dev --chain $CHAIN \
      --reading source_choice --split 0.999 --control "$CTRL" --out $S/ft_join_dev.json > $S/ft_join_dev.log 2>&1
    PYTHONPATH=$R $V -m semabi.eval.v4_outcome --run $P/harbour_join_dev --chain $CHAIN \
      --reading source_choice --split 0.999 --no-ablation --out $S/outcome_join_dev.json > $S/outcome_join_dev.log 2>&1
    ;;
  holdout)
    python3 $P/join_merge.py $P/harbour_join_hold runs/v4/harbour_transfer $P/logs/result_join_s11.json $P/logs/result_join_s12.json $P/logs/result_join_s13.json
    PYTHONPATH=$R $V -m semabi.eval.v4_outcome --run $P/harbour_join_dev --chain $CHAIN --reading source_choice \
      --split 0.999 --score-on $P/harbour_join_hold --control "$CTRL" --no-ablation \
      --out $S/outcome_join_hold.json > $S/outcome_join_hold.log 2>&1
    cd $S/base
    PYTHONPATH=$S/base $V -m semabi.eval.v4_outcome --run $P/harbour_join_dev --chain $CHAIN --reading source_choice \
      --split 0.999 --score-on $P/harbour_join_hold --control "$CTRL" --no-ablation \
      --out $S/outcome_join_hold_base.json > $S/outcome_join_hold_base.log 2>&1
    ;;
  *) echo "usage: join_attack.sh dev|holdout"; exit 2;;
esac
echo done > $S/JOIN_ATTACK_$1_DONE
