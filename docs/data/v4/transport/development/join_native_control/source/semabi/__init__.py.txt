"""SemABI: semantic interface induction from black-box interaction.

Package boundary (enforced by tests/test_boundary.py):
  semabi.relmodel  - domain-free relational language. Shared.
  semabi.hidden    - EVALUATOR ONLY. Hidden ground-truth domains.
  semabi.env       - local web apps rendering hidden domains. Evaluator side.
  semabi.compiler  - black-box side. Must never import hidden/env/eval.
  semabi.eval      - scoring learned models against hidden ground truth.
"""
