"""Verify [B] citations: for each (book, printed page, offset, must-contain terms) extract the PDF page ±1 with
pdftotext and report whether every term appears. Read-only. Output feeds the KB verification log."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Where the source books live on YOUR machine. They are copyrighted and are not part of this repository.
#   SUFD_LECTURE_NOTES : folder holding the textbook PDFs (Antoniou, Giron-Sierra, Dorf & Bishop, Bird)
#   SUFD_DOWNLOADS     : folder holding the other PDFs (Living Computers, ML for Industrial Applications, AI for Art)
B = os.environ.get("SUFD_LECTURE_NOTES", "")
D = os.environ.get("SUFD_DOWNLOADS", "")
if not B or not D:
    sys.exit("set SUFD_LECTURE_NOTES and SUFD_DOWNLOADS to the folders that hold the source PDFs (see "
             "spec/knowledge-base.md section 3). bench/citations_log.json is the recorded result of an earlier run.")
ANT = B + r"\500L\Digital Signal Processing\Andreas-Intoniou-Digital-signal-processing.pdf"
GIR = B + r"\500L\Digital Signal Processing\Digital Signal Processing with Matlab Examples Volume 1 Signals and Data Filtering Non-stationary Signals Modulation by Jose Maria Giron-Sierra auth z-libo - Copy.pdf"
DOR = B + r"\500L\Control Engineering\Textbooks\Richard C. Dorf, Robert H. Bishop - Modern Control Systems (12th Edition) (2010).pdf"
LIV = D + r"\Living_Computers_Replicators,_Information_Processing,_and_the_Evolution.pdf"
MLI = D + r"\Machine Learning for Industrial Applications.pdf"
ART = D + r"\Artificial Intelligence for Art Creation and Understanding.pdf"
BIRD = B + r"\300l\1st semster\JOHN BIRD.pdf"
CHECKS = [  # id, file, printed page, offset (pdf = printed + offset), terms (case-insens regex, ALL must appear in page±1)
 ("K-ant-alias", ANT, 229, 26, [r"alias"]),
 ("K-ant-sampling-thm", ANT, 294, 26, [r"sampling theorem"]),
 ("K-ant-resolution", ANT, 355, 26, [r"resolution"]),
 ("K-ant-quant-q2/12", ANT, 638, 26, [r"quantiz", r"12"]),
 ("K-ant-groupdelay", ANT, 252, 26, [r"group delay"]),
 ("K-ant-wiener-khinchine", ANT, 608, 26, [r"wiener|khinch"]),
 ("K-ant-psd-definition", ANT, 605, 26, [r"power spectral|spectral density"]),
 ("K-gir-wold", GIR, 158, 34, [r"wold"]),
 ("K-gir-gabor-heisenberg", GIR, 359, 34, [r"heisenberg|uncertainty"]),
 ("K-dor-S+C", DOR, 238, 26, [r"sensitivity", r"complementary|noise"]),
 ("K-dor-observer", DOR, 847, 26, [r"observer"]),
 ("K-dor-observability", DOR, 839, 26, [r"observab"]),
 ("K-dor-gain-phase-margin", DOR, 655, 26, [r"phase margin|gain margin"]),
 ("K-liv-mutual-info", LIV, 175, 15, [r"mutual information|information about"]),
 ("K-liv-error-threshold", LIV, 128, 15, [r"error threshold|threshold"]),
 ("K-liv-gold", LIV, 213, 15, [r"gold"]),
 ("K-mli-FPE-BIC", MLI, 136, 16, [r"akaike|AIC|BIC|FPE"]),
 ("K-mli-timesplit", MLI, 131, 16, [r"time series|chronolog|time"]),
 ("K-art-grounding", ART, 7, 15, [r"ground"]),
 ("K-art-posthoc-LLM", ART, 9, 15, [r"LLM|language model"]),
 ("K-bird-transient", BIRD, 259, 15, [r"time constant|transient"]),
]
def page_text(f, p):
    r = subprocess.run(["pdftotext", "-f", str(p), "-l", str(p), f, "-"], capture_output=True, text=True, errors="replace")
    return r.stdout
out = []
for cid, f, pg, off, terms in CHECKS:
    hit = {}
    for d in (-1, 0, 1):
        t = page_text(f, pg + off + d)
        hit[d] = all(re.search(x, t, re.I) for x in terms) if t.strip() else None
    ok = any(v for v in hit.values())
    where = next((d for d in (0, -1, 1) if hit[d]), None)
    empty = all(v is None for v in hit.values())
    out.append((cid, "NO-TEXT" if empty else ("VERIFIED" + ("" if where == 0 else f" (page {where:+d})") if ok else "NOT FOUND")))
for cid, st in out:
    print(f"{cid:28s} {st}")
unreadable = [cid for cid, st in out if st == "NO-TEXT"]
log = Path(__file__).resolve().parent / "citations_log.json"
if unreadable:
    # never replace recorded evidence with a partial run (a missing drive once turned 14 entries into NO-TEXT)
    print(f"\n{len(unreadable)} citation(s) could not be read (is the source folder available?); "
          f"{log.name} left unchanged.")
    sys.exit(2)
json.dump(dict(out), open(log, "w"), indent=1)
