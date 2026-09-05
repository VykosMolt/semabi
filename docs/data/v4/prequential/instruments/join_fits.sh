#!/bin/bash
# P21 fits, all in parallel, each memory-capped: the Allocate berth control inspected
# and the holdout scored, under the new code (R) and under the pre-change worktree (B).
P=/home/moloch/semabi-scratch/preq
S=/tmp/claude-1000/-home-moloch-semabi/cbdd0615-d7c0-4fae-b02c-d64c20b5ee38/scratchpad
R=/home/moloch/semabi; B=$S/base
V=$R/.venv/bin/python
CHAIN=docs/data/v4/manifests/harbour_chain.json
CTRL="button:Allocate berth"
launch() {  # name root cmd...
  local name=$1 root=$2; shift 2
  systemd-run --user --slice=preq.slice --scope --unit=p21-$name-$(date +%s) -p MemoryMax=5G -q \
    --working-directory=$root nice -n 5 env PYTHONPATH=$root SEMABI_ROOT=$root "$@" > $S/p21_$name.log 2>&1 &
}
launch inspect     $R $V $P/join_inspect.py $P/harbour_join_dev $CHAIN source_choice "$CTRL" $S/join_inspect_dev.json
launch inspectbase $B $V $P/join_inspect.py $P/harbour_join_dev $CHAIN source_choice "$CTRL" $S/join_inspect_dev_base.json
launch hold        $R $V -m semabi.eval.v4_outcome --run $P/harbour_join_dev --chain $CHAIN --reading source_choice \
  --split 0.999 --score-on $P/harbour_join_hold --no-ablation --out $S/outcome_join_hold.json
launch holdbase    $B $V -m semabi.eval.v4_outcome --run $P/harbour_join_dev --chain $CHAIN --reading source_choice \
  --split 0.999 --score-on $P/harbour_join_hold --no-ablation --out $S/outcome_join_hold_base.json
launch ft          $R $V -m semabi.eval.v4_field_theory --run $P/harbour_join_dev --chain $CHAIN --reading source_choice \
  --split 0.999 --control "$CTRL" --out $S/ft_join_dev.json
launch dev         $R $V -m semabi.eval.v4_outcome --run $P/harbour_join_dev --chain $CHAIN --reading source_choice \
  --split 0.999 --no-ablation --out $S/outcome_join_dev.json
wait
echo done > $S/P21_FITS_DONE
