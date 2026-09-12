"""p42_moves with the revision rule switched off (diagnostic: which repair moved a reading)."""
import os, sys, runpy
sys.path.insert(0, os.environ.get("SEMABI_ROOT", "/home/moloch/semabi"))
from semabi.compiler.v4 import objective
objective._drop_revisions = lambda delta, prev: None
sys.argv = [sys.argv[0]] + sys.argv[1:]
runpy.run_path("/home/moloch/semabi/docs/data/v4/prequential/instruments/p42_moves.py", run_name="__main__")
