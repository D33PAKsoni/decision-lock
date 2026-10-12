"""Community Cloud entry point: always isolate histories for a public demo."""

import os
import runpy
from pathlib import Path

os.environ["DECISION_LOCK_PUBLIC_ENTRY"] = "1"
runpy.run_path(str(Path(__file__).with_name("app.py")), run_name="__main__")
