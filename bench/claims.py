"""Independent reproduction of the simulation claims the research agents reported ([S] items in the KB).

Pure functions, no SUFD import: these check the *knowledge*, not the implementation.

    python bench/claims.py

Claim 1 (flicker): a mean ± 3σ band calibrated on an initial window is exceeded far more than 0.27% of the time
         on 1/f noise, and a longer calibration window does not fix it.
Claim 2 (autocorrelation): a CUSUM (k=0.5, h=5) run on raw AR(1) data has a far smaller in-control ARL than on
         standardised one-step innovations (which restores ≈ 465 two-sided).
Claim 3 (Siegmund): one-sided ARL0 ≈ [e^{-2Δb} − 1 + 2Δb] / (2Δ²) with b = h + 1.166 reproduces the NIST table.
"""
from __future__ import annotations

import math
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scenarios as S                                                # noqa: E402


def claim_flicker(seeds=16, n=16384, windows=(1000, 10000)):
    out = {}
    for w in windows:
        rates = []
        for sd in range(seeds):
            x = [v for _, v in S.flicker(sd, n).samples]
            mu = statistics.fmean(x[:w])
            sg = statistics.pstdev(x[:w])
            post = x[w:]
            rates.append(sum(1 for v in post if abs(v - mu) > 3 * sg) / len(post))
        out[w] = (statistics.mean(rates), min(rates), max(rates))
    r = random.Random(1)
    wn = [r.gauss(0, 1) for _ in range(n)]
    mu, sg = statistics.fmean(wn[:1000]), statistics.pstdev(wn[:1000])
    out["white"] = sum(1 for v in wn[1000:] if abs(v - mu) > 3 * sg) / (n - 1000)
    return out


def cusum_run_length(gen, k=0.5, h=5.0, cap=20000):
    hi = lo = 0.0
    for i in range(1, cap + 1):
        z = gen()
        hi = max(0.0, hi + z - k)
        lo = max(0.0, lo - z - k)
        if hi > h or lo > h:
            return i
    return cap


def claim_cusum(phis=(0.0, 0.5, 0.9), trials=300):
    res = {}
    for phi in phis:
        raw, inn = [], []
        for tr in range(trials):
            r = random.Random(tr * 31 + int(phi * 10))
            g = math.sqrt(1 - phi * phi)
            st = {"x": r.gauss(0, 1)}

            def nxt_raw():
                st["x"] = phi * st["x"] + g * r.gauss(0, 1)
                return st["x"]
            raw.append(cusum_run_length(nxt_raw))

            r2 = random.Random(tr * 31 + 7 + int(phi * 10))
            st2 = {"x": r2.gauss(0, 1)}

            def nxt_inn():
                prev = st2["x"]
                st2["x"] = phi * prev + g * r2.gauss(0, 1)
                return (st2["x"] - phi * prev) / g                    # standardised innovation
            inn.append(cusum_run_length(nxt_inn))
        res[phi] = (statistics.mean(raw), statistics.mean(inn))
    return res


def siegmund_arl0(h, k=0.5):
    """One-sided in-control ARL, Siegmund approximation (delta = -k for the in-control drift below the reference)."""
    b = h + 1.166
    d = -k
    return (math.exp(-2 * d * b) - 1 + 2 * d * b) / (2 * d * d)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:                                                 # noqa: BLE001
        pass
    print("CLAIM 1 — mean±3σ on 1/f noise (nominal 0.27%)")
    f = claim_flicker()
    for w in (1000, 10000):
        m, lo, hi = f[w]
        print(f"  calibrated on {w:>5} samples: mean {m:.2%}  (seeds range {lo:.2%} – {hi:.2%})")
    print(f"  white-noise control:        {f['white']:.2%}")
    print("\nCLAIM 2 — two-sided CUSUM k=0.5, h=5: in-control ARL, raw AR(1) vs standardised innovations")
    c = claim_cusum()
    for phi, (raw, inn) in c.items():
        print(f"  phi={phi}: raw {raw:7.0f}   innovations {inn:7.0f}   (collapse x{inn / raw:.1f})")
    print("\nCLAIM 3 — Siegmund one-sided ARL0 (NIST table k=0.5: h=4 -> 336, h=5 -> 930)")
    for h in (4, 5):
        print(f"  h={h}: {siegmund_arl0(h):7.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
