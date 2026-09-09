"""Pass the exact shared preflight artifact and arguments to the cached CLI."""
import argparse
import json
import os
from pathlib import Path

from semabi.baselines.cached_form import main as cached_main


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binding-file", type=Path, required=True)
    parser.add_argument("--application-url", required=True)
    parser.add_argument("--credentials-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    binding = json.loads(args.binding_file.read_text())
    if binding.get("status") != "ELIGIBLE" or binding.get("call") is None:
        raise ValueError("Only an eligible shared call may reach this runner")
    call = binding["call"]
    args.output_dir.mkdir(parents=True, exist_ok=False)
    operation = args.output_dir / "operation.json"
    operation.write_text(json.dumps(call["operation"], indent=2) + "\n")
    return cached_main(["--operation-file", str(operation),
                        "--application-url", args.application_url,
                        "--credentials-file", str(args.credentials_file),
                        "--arguments", json.dumps(call["arguments"]),
                        "--output-dir", str(args.output_dir / "baseline"),
                        "--max-actions", "20", "--max-writes", "12", "--max-seconds", "60"])


if __name__ == "__main__":
    raise SystemExit(main())
