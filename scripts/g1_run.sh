#!/bin/bash
cd /home/moloch/semabi/semabi
for spec in "01_kiln 8600" "02_harbor 8601" "05_pantry 8604"; do
  set -- $spec
  .venv/bin/python -m semabi.run_external --base http://127.0.0.1:$2 --run runs/g1_$1 --v1 --episodes 3 --steps 30 --active-rounds 3 --active-budget 100 --goals 6 > runs/log_g1_$1.txt 2>&1 &
done
wait
echo G1_DONE
