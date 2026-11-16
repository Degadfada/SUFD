"""System-level performance probe (plan S6): CPU share under the demo load; µs/sample is recorded, not gated."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run
print(run.m_perf())
