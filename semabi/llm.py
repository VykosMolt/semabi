"""Minimal LLM wrapper over the `claude -p` CLI (no API key required).
Used only by baselines and (optionally) hypothesis proposal; never trusted as ground truth."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def ask(prompt: str, model: str = "sonnet", system: str | None = None, timeout: int = 1500, cache_dir: Path | None = None) -> str:
    key = None
    if cache_dir:
        import hashlib
        key = hashlib.sha1((model + (system or "") + prompt).encode()).hexdigest()
        p = Path(cache_dir) / f"{key}.json"
        if p.exists():
            return json.loads(p.read_text())["text"]
    cmd = ["claude", "-p", "--model", model, "--output-format", "json"]
    if system:
        cmd += ["--system-prompt", system]
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    out = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=timeout, env=env)
    if out.returncode != 0:
        raise RuntimeError(f"claude -p failed: {out.stderr[:500]}")
    j = json.loads(out.stdout)
    text = j.get("result", "")
    if cache_dir and key:
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        (Path(cache_dir) / f"{key}.json").write_text(json.dumps({"text": text, "usage": j.get("usage"), "cost": j.get("total_cost_usd")}))
    return text


def extract_json(text: str) -> dict:
    """Find the first JSON object in a response."""
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON in response")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    raise ValueError("unbalanced JSON")
