#!/bin/bash
cd /home/moloch/semabi
rm -rf runs/final_standard_misleading_list_s1
.venv/bin/python -m semabi.run_pipeline --run runs/final_standard_misleading_list_s1 --ui list --labels misleading --variant standard --seed 1 --episodes 3 --steps 30 --active-rounds 3 --active-budget 100 --goals 6 --port 9700 > runs/log_rerun_one.txt 2>&1
scripts/reeval_final.sh
