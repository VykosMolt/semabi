#!/bin/bash
cd /home/moloch/semabi
i=0
for d in $(ls -d ~/semabi-gauntlet/apps/*/); do
  name=$(basename $d)
  port=$((8600+i)); i=$((i+1))
  [ -f runs/gauntlet_$name/eval.json ] && continue
  .venv/bin/python -m semabi.run_external --base http://127.0.0.1:$port --run runs/gauntlet_$name --episodes 3 --steps 30 --active-rounds 3 --active-budget 100 --goals 6 > runs/log_gauntlet_$name.txt 2>&1
  echo "$name done: $(grep -E '^operators' runs/log_gauntlet_$name.txt)"
done
echo GAUNTLET_DONE
