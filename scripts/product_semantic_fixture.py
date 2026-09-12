#!/usr/bin/env python3
"""Evaluator-only renamed development fixture; never imported by the learner.

Seed changes create fresh visible records in an isolated application process. The
application's procedures, comparisons, routes and rendering remain unchanged.
This is disclosed fixture development evidence, not an independent application.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8879)
    parser.add_argument("--fixture", choices=("dispatch", "workshop"), default="dispatch")
    parser.add_argument("--owner-names", type=json.loads,
                        default=["Lumen route", "Quartz route", "Indigo route"])
    parser.add_argument("--resource-names", type=json.loads,
                        default=["Amber carrier", "Cobalt carrier", "Silver carrier"])
    args = parser.parse_args()
    for names in (args.owner_names, args.resource_names):
        if not isinstance(names, list) or len(names) != 3 or not all(isinstance(n, str) and n for n in names) or len(set(names)) != 3:
            parser.error("supply three distinct nonempty visible names per collection")
    root = Path(__file__).resolve().parents[1] / "experiments" / "transport_v1"
    sys.path.insert(0, str(root))
    spec = importlib.util.spec_from_file_location("semantic_evaluator_fixture_server", root / "server.py")
    server = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(server)
    from fixtures.model import REVIEW_RECORDS
    records = REVIEW_RECORDS[args.fixture]
    original_records = dict(records)
    records.clear()
    for row, name in zip(server.BASES[args.fixture]["jobs"], args.owner_names):
        records[name] = original_records[row["name"]]
        row["name"] = name
    for row, name in zip(server.BASES[args.fixture]["resources"], args.resource_names):
        row["name"] = name
    server.CURRENT = server.fresh(args.fixture)
    print(json.dumps({"boundary": "evaluator-only seed renaming; unchanged development application",
                      "url": f"http://127.0.0.1:{args.port}/{args.fixture}",
                      "owner_names": args.owner_names, "resource_names": args.resource_names}), flush=True)
    server.ThreadingHTTPServer(("127.0.0.1", args.port), server.Handler).serve_forever()


if __name__ == "__main__":
    main()
