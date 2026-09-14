#!/bin/bash
cd /home/moloch/semabi/semabi
run() { rm -rf runs/g2_$1; .venv/bin/python -m semabi.run_external --base http://127.0.0.1:$2 --run runs/g2_$1 --v1 --episodes 3 --steps 30 --active-rounds 3 --active-budget 150 --goals 6 > runs/log_g2_$1.txt 2>&1; echo "$1 done"; }
run grok_01_apiary 8700 & run grok_02_observatory 8701 & run grok_03_pharmacy 8702 & wait
run grok_04_climbing 8703 & run claude_01_airport 8710 & run claude_02_pharmacy 8711 & wait
run claude_03_museum 8712 & run claude_04_datacenter 8713 & wait
echo G2_DONE
