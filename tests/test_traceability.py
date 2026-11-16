"""M0 traceability: the knowledge base and its verification log must agree (plan v4.1 dimension 26)."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KB = (ROOT / "spec" / "knowledge-base.md").read_text(encoding="utf-8")
LOG = json.loads((ROOT / "bench" / "citations_log.json").read_text(encoding="utf-8"))
TAGS = {"B", "D", "S", "K", "FP"}


def rows():
    out = []
    for line in KB.splitlines():
        if line.startswith("| K-"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            out.append(cells)
    return out


def test_ids_are_unique():
    ids = [r[0] for r in rows()]
    assert len(ids) == len(set(ids)), [i for i in ids if ids.count(i) > 1]


def test_every_logged_citation_has_a_kb_row():
    ids = {r[0] for r in rows()}
    missing = [k for k in LOG if k not in ids]
    assert not missing, f"verified in the log but absent from the KB: {missing}"


def test_every_verified_row_is_backed_by_the_log():
    unbacked = []
    for r in rows():
        status = next((c for c in r if c.startswith("verified")), None)
        if status and "by us" not in status and r[0] not in LOG:
            unbacked.append(r[0])
    assert not unbacked, f"KB says verified but no log entry: {unbacked}"


def test_log_has_no_failures():
    bad = {k: v for k, v in LOG.items() if not v.startswith("VERIFIED")}
    assert not bad, bad


def test_every_row_carries_a_provenance_tag():
    bad = []
    for r in rows():
        cells = " ".join(r)
        found = set(re.findall(r"\b(B|D|S|K|FP)\b", cells.replace("/", " ")))
        if not (found & TAGS):
            bad.append(r[0])
    assert not bad, bad


def test_reproduced_claims_match_bench_claims():
    """The KB quotes the reproduction; fail if the numbers drift from what bench/claims.py actually prints."""
    import subprocess, sys
    out = subprocess.run([sys.executable, str(ROOT / "bench" / "claims.py")], capture_output=True, text=True,
                         encoding="utf-8").stdout
    assert "h=4:     338" in out and "h=5:     938" in out
    assert "338 / 938" in KB
