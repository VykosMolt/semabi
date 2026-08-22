#!/bin/sh
# Start the instrumented (evaluator-only) copies of the gauntlet-v2 apps on ports 8800-8807.
cd "$(dirname "$0")"
port=8800
for d in grok_01_apiary grok_02_observatory grok_03_pharmacy grok_04_climbing claude_01_airport_gates claude_02_pharmacy_dispensary claude_03_museum_loans claude_04_datacenter_racks; do
  (cd $d && python3 app.py --port $port > /dev/null 2>&1 &)
  echo "$d -> $port"
  port=$((port+1))
done
