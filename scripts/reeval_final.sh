#!/bin/bash
cd /home/moloch/semabi/semabi
port=9300
for d in runs/final_*_s[01]; do
  n=$(basename $d); IFS=_ read -r _ variant labels ui seed <<< "$n"; seed=${seed#s}
  .venv/bin/python -m semabi.run_pipeline --run $d --ui $ui --labels $labels --variant $variant --seed $seed --goals 6 --port $port > $d/reeval.log 2>&1
  port=$((port+1))
  echo "$n done"
done
.venv/bin/python -m semabi.run_matrix --labels plain,obscured,misleading --seeds 0,1 --prefix final --port 9500 > runs/log_final_lab2.txt 2>&1
.venv/bin/python -m semabi.run_matrix --variants cascade,promote,weird --uis kanban,table,list --seeds 0 --prefix final --port 9600 > runs/log_final_var2.txt 2>&1
echo REEVAL_DONE
