#!/bin/bash
cd /home/moloch/semabi
port=9950
for ui in kanban table list; do
  .venv/bin/python -m semabi.run_pipeline --run runs/ctrl_random_$ui --ui $ui --episodes 13 --steps 30 --active-rounds 0 --goals 6 --port $port > runs/log_ctrl_$ui.txt 2>&1
  port=$((port+1))
done
echo CTRL_DONE
