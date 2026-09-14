#!/bin/bash
cd /home/moloch/semabi/semabi
run() { rm -rf runs/g1_$1; .venv/bin/python -m semabi.run_external --base http://127.0.0.1:$2 --run runs/g1_$1 --v1 --episodes 3 --steps 30 --active-rounds 3 --active-budget 150 --goals 6 > runs/log_g1_$1.txt 2>&1; echo "$1 done"; }
run 03_loft 8602 & run 05_pantry 8604 & run 08_docket 8607 & wait
echo G1RERUN_DONE
