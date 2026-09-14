#!/bin/bash
cd /home/moloch/semabi/semabi
.venv/bin/python -m semabi.run_matrix --labels plain,obscured,misleading --seeds 0,1 --prefix final --port 9000 > runs/log_final_lab.txt 2>&1
.venv/bin/python -m semabi.run_matrix --variants cascade,promote,weird --uis kanban,table,list --seeds 0 --prefix final --port 9100 > runs/log_final_var.txt 2>&1
