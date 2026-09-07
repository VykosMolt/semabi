"""Run the immutable 161-check harness against corrected source snapshots."""
import hashlib
import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
FILE = HERE.parents[1] / "evaluation_preservation_checks_v1.py"
assert hashlib.sha256(FILE.read_bytes()).hexdigest() == "e7b7adf30461016c893aca4016986568a81a8f434b48003dd54467c092ff62ab"
spec = importlib.util.spec_from_file_location("_unchanged_caller_review", FILE)
harness = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = harness
spec.loader.exec_module(harness)
harness.HELD = HERE / "held_sources"
sys.argv = [str(FILE), "--out", str(HERE / "unchanged_checks")]
raise SystemExit(harness.main())
