#!/bin/bash
cd /home/moloch/semabi/semabi
run() { .venv/bin/python -m semabi.run_external --base http://127.0.0.1:$2 --run runs/g1_$1 --v1 --episodes 3 --steps 30 --active-rounds 3 --active-budget 150 --goals 6 > runs/log_g1_$1.txt 2>&1; echo "$1 done"; }
rm -rf runs/g1_01_kiln runs/g1_02_harbor runs/g1_03_loft runs/g1_04_stack runs/g1_05_pantry runs/g1_06_yard runs/g1_07_slate runs/g1_08_docket
run 01_kiln 8600 & run 02_harbor 8601 & run 03_loft 8602 & wait
run 04_stack 8603 & run 05_pantry 8604 & run 06_yard 8605 & wait
run 07_slate 8606 & run 08_docket 8607 & wait
echo G1ALL_DONE
