#!/bin/bash
cd /home/moloch/semabi
for r in final_standard_plain_kanban_s0 final_standard_plain_table_s0 final_standard_plain_list_s0 \
         final_standard_obscured_kanban_s0 final_standard_obscured_table_s0 final_standard_obscured_list_s0 \
         final_standard_misleading_kanban_s0 final_standard_misleading_table_s0 final_standard_misleading_list_s0 \
         final_cascade_plain_kanban_s0 final_promote_plain_kanban_s0 final_weird_plain_kanban_s0; do
  [ -f runs/llm_${r}_sonnet/model.json ] || .venv/bin/python -m semabi.baselines.llm_passive --run runs/$r --out runs/llm_${r}_sonnet --model sonnet > runs/llm_${r}.log 2>&1
  echo "$r llm done"
done
for r in final_standard_plain_kanban_s0 final_standard_misleading_kanban_s0 final_weird_plain_kanban_s0 final_promote_plain_kanban_s0; do
  [ -f runs/llmall_${r}_sonnet/model.json ] || .venv/bin/python -m semabi.baselines.llm_passive --run runs/$r --out runs/llmall_${r}_sonnet --model sonnet --all-steps --max-steps 200 > runs/llmall_${r}.log 2>&1
  echo "$r llm-all done"
done
echo LLM_DONE
