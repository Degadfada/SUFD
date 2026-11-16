"""Scoreboard: run the scenario corpus through the current SUFD build and score it against pass marks.

    python bench/run.py --baseline     # record bench/baseline.json (M0: slice 1)
    python bench/run.py                # score, write bench/scoreboard.md, diff against the baseline

Only stable public names are used (Mind, Signal, Watch, choose_lens, render_svg), so the same harness scores
slice 1, the renamed build (M1 gate: identical numbers) and every later milestone. A capability the build does
not have yet scores "—" (not implemented), which is a fail for its gate, never a silent pass.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
import traceback
from pathlib import Path
from typing import Callable, Dict, List, Optional

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import scenarios as S                                             # noqa: E402
from sufd import Mind, SelfProbe, Signal, Watch, choose_lens, render_svg   # noqa: E402

NA = None           # "not implemented in this build"


def fresh_mind() -> Mind:
    tick = iter(range(10 ** 9))
    return Mind(SelfProbe(clock=lambda: float(next(tick)), cpu=lambda: 0.0))


def feed(samples, name="x", hint=None):
    m = fresh_mind()
    described_at = None
    for i, (t, v) in enumerate(samples):
        m.ingest(name, t, v, hint)
        if described_at is None and m.ledger[name].state in ("described", "named", "in_use"):
            described_at = i + 1
    return m, described_at


def jump_notes(m: Mind, name="x") -> List:
    return [n for n in m.followers[name].follow.notes if "jump" in n.text]


# ---------------------------------------------------------------- metrics
def m_false_jumps() -> Dict[str, float]:
    out = {}
    for key in ("ramp", "sine", "white", "flicker", "heavy_tail"):
        sc = S.SINGLE[key](0)
        m, _ = feed(sc.samples)
        # notes are capped at 50 by Follower; count from the full run by re-observing note growth is unavailable
        # in slice 1, so report the retained count per 1000 samples (a lower bound when the cap is hit)
        out[key] = round(1000 * len(jump_notes(m)) / len(sc.samples), 2)
    return out


def m_quantised_blip() -> Dict[str, object]:
    """A flat quantised sensor then ONE 1-LSB blip must stay a scalar and raise no event. (Slice 1 misclassifies
    the signal as binary and reports 'changed to ...': any note at the blip counts, not only 'jump' notes.)"""
    sc = S.quantised_blip(0)
    m, _ = feed(sc.samples)
    blip_t = sc.truth["blip_t"]
    notes = [n for n in m.followers["x"].follow.notes if abs(n.t - blip_t) <= 1.0]
    return {"kind": m.signals["x"].env.kind, "notes_at_blip": [n.text for n in notes]}


def m_period() -> Dict[str, Optional[float]]:
    out = {}
    for key in ("sine", "sine_jitter"):
        sc = S.SINGLE[key](0)
        m, _ = feed(sc.samples)
        p = m.signals["x"].env.period
        out[key + "_rel_err"] = None if not p else round(abs(p - sc.truth["period"]) / sc.truth["period"], 4)
        out[key + "_err_bar"] = NA if not hasattr(m.signals["x"].env, "period_err") else m.signals["x"].env.period_err
    return out


NOMINAL_3SIGMA = 0.0027      # two-sided Gaussian tail beyond ±3σ


def _watch_run(samples, calib_n: int, k: Optional[float] = None):
    """Calibrate a learned watch on the first calib_n samples (as if a human confirmed the sense), then judge.
    k=None uses the build's own default band; k=3 asks for a band whose nominal exceedance is 0.27%."""
    sig = Signal("x")
    for t, v in samples[:calib_n]:
        sig.push(t, v)
    w = Watch("x", sig.env) if k is None else Watch("x", sig.env, k=k)
    acts, clears, beyond = [], [], 0
    for t, v in samples[calib_n:]:
        sig.push(t, v)
        if v > w.hi or v < w.lo:
            beyond += 1
        n = w.check(t, v, sig.env)
        if n is not None:
            (acts if n.level == "warn" else clears).append(t)
    return w, acts, clears, beyond


EXCEED_SEEDS = 20


def m_exceedance() -> Dict[str, float]:
    """Ask for a band with nominal 0.27% exceedance (±3σ) and measure what happens after calibration, averaged
    over EXCEED_SEEDS seeds (single seeds swing 0.9%–17% on 1/f noise). The watch band is frozen at calibration,
    so post-calibration samples are only counted against it. Mean±kσ should hold on white noise and fail on 1/f."""
    out = {"nominal": NOMINAL_3SIGMA, "seeds": EXCEED_SEEDS}
    cases = (("white", 1000, lambda sd: S.gaussian(sd, 6000)), ("heavy_tail", 1000, lambda sd: S.heavy_tail(sd, 6000)),
             ("flicker", 1000, lambda sd: S.flicker(sd, 8192)), ("flicker_10k", 4096, lambda sd: S.flicker(sd, 16384)))
    for key, calib, gen in cases:
        rates = []
        for sd in range(EXCEED_SEEDS):
            sc = gen(sd)
            sig = Signal("x")
            for t, v in sc.samples[:calib]:
                sig.push(t, v)
            w = Watch("x", sig.env, k=3.0)
            post = [v for _, v in sc.samples[calib:]]
            rates.append(sum(1 for v in post if v > w.hi or v < w.lo) / len(post))
        out[key] = round(statistics.mean(rates), 5)
        out[key + "_worst"] = round(max(rates), 5)
    return out


def m_detection() -> Dict[str, Optional[float]]:
    out = {}
    for key in ("mean_shift", "ar1_mean_shift"):
        sc = S.SINGLE[key](0)
        ev = sc.truth["events"][0]
        _, acts, _, _ = _watch_run(sc.samples, 500)
        before = [a for a in acts if a < ev]
        after = [a for a in acts if a >= ev]
        out[key + "_delay"] = None if not after else after[0] - ev          # None = never detected
        out[key + "_false_before"] = len(before)
    return out


def m_chatter() -> Dict[str, int]:
    """Chatter as defined in plan v4.1 S3: ≥3 activations of one condition within 60 s. Fleeting: active < 10 s
    (evaluation reference until per-signal on-delays exist). Truth for this scenario: exactly 1 episode."""
    sc = S.chatter_near_threshold(0)
    _, acts, clears, _ = _watch_run(sc.samples, sc.truth["calib"])
    chatter = sum(1 for i in range(2, len(acts)) if acts[i] - acts[i - 2] <= 60.0)
    episodes = len(acts)
    durations = []
    for a in acts:
        nxt = [c for c in clears if c > a]
        durations.append((nxt[0] - a) if nxt else math.inf)
    fleeting = sum(1 for d in durations if d < 10.0)
    return {"activations": episodes, "chatter_events": chatter, "fleeting": fleeting}


def m_hostile() -> Dict[str, object]:
    sc = S.hostile(0)
    errors = []
    try:
        m = fresh_mind()
        for t, v in sc.samples:
            try:
                m.ingest("h", t, v)
            except Exception as e:                                    # noqa: BLE001
                errors.append(f"ingest({t},{v!r}): {type(e).__name__}")
        try:
            m.panel("h")
        except Exception as e:                                        # noqa: BLE001
            errors.append(f"panel: {type(e).__name__}")
    except Exception as e:                                            # noqa: BLE001
        errors.append(f"setup: {type(e).__name__}")
    return {"exceptions": len(errors), "first": errors[:3]}


def m_fuzz() -> Dict[str, object]:
    """2000 random (timestamp, value) pairs of mixed types, ordering and magnitude: count unhandled exceptions."""
    import random
    r = random.Random(12345)
    pool = [lambda: r.gauss(0, 1), lambda: float("nan"), lambda: float("inf"), lambda: r.randint(-5, 5),
            lambda: r.random() < 0.5, lambda: r.choice(["a", "b", "on", ""]), lambda: None,
            lambda: tuple(r.gauss(0, 1) for _ in range(r.choice([1, 2, 3]))), lambda: 1e308 * r.random(),
            lambda: -0.0]
    m = fresh_mind()
    errs: Dict[str, int] = {}
    t = 0.0
    for _ in range(2000):
        t += r.choice([1.0, 0.0, -0.5, 1e-9, 1e6, 0.1])
        try:
            m.ingest(r.choice(["a", "b", "c"]), t, r.choice(pool)())
        except Exception as e:                                        # noqa: BLE001
            errs[type(e).__name__] = errs.get(type(e).__name__, 0) + 1
    return {"exceptions": sum(errs.values()), "by_type": errs}


def m_unmodelled() -> bool:
    m, _ = feed(S.white(0).samples)
    return m.ledger["x"].state == "unmodelled"


def m_signature() -> Dict[str, object]:
    """S1 on the frozen 180-case set. Slice-1 labels are mapped generously to classes (a label naming several
    classes counts as correct for each) — documented so later builds are not compared unfairly."""
    label_map = {
        "temperature-like": {"temperature", "cpu_temp"},
        "level / percentage-like": {"battery", "humidity"},
        "switch / presence / door state": {"switch"},
        "motion / orientation (accelerometer-like)": {"accelerometer"},
        "oscillating source (audio / vibration-like)": {"microphone_level"},
    }
    top1 = top3 = 0
    described = []
    cases = S.signature_set()
    for sc in cases:
        m, d = feed(sc.samples)
        described.append(d if d is not None else 10 ** 6)
        cands = m.signals["x"].env.candidates()
        labels = [c[0] for c in cands]
        cls = sc.truth["class"]
        ok = [cls in label_map.get(lbl, {lbl}) for lbl in labels]
        top1 += bool(ok[:1] and ok[0])
        top3 += any(ok[:3])
    return {"cases": len(cases), "top1": round(top1 / len(cases), 3), "top3": round(top3 / len(cases), 3),
            "described_median_samples": statistics.median(described)}


def m_perf() -> Dict[str, float]:
    from sufd.sim import make_sources
    m = fresh_mind()
    src = make_sources()
    next_at = {k: v[0] for k, v in src.items()}
    t, n = 0.0, 0
    c0 = time.process_time()
    while t <= 300:
        for k, (_, period, fn, hint) in src.items():
            if t >= next_at[k]:
                m.ingest(k, round(t, 3), fn(t), hint)
                next_at[k] = t + period
                n += 1
        t = round(t + 0.1, 3)
    cpu = time.process_time() - c0
    return {"samples": n, "us_per_sample": round(1e6 * cpu / n, 1), "cpu_share_realtime": round(cpu / 300, 4)}


def m_capabilities() -> Dict[str, object]:
    """Capabilities that later milestones add. Absent ⇒ "—" and the gate fails."""
    env = Signal("x").env
    return {
        "alias_flag": hasattr(env, "alias_suspect") or NA,
        "tau_zeta": hasattr(env, "tau") or NA,
        "pit_calibration": hasattr(env, "pit") or NA,
        "timing_jitter_skew": NA,
        "stuck_clip_gap_flags": hasattr(env, "flags") or NA,
        "relations": NA, "thermal": NA, "privacy_class": NA, "trust": NA,
    }


METRICS: Dict[str, Callable[[], object]] = {
    "false_jumps_per_1000": m_false_jumps, "quantised_blip_flagged": m_quantised_blip, "period": m_period,
    "band_exceedance": m_exceedance, "detection": m_detection, "chatter": m_chatter, "hostile": m_hostile,
    "white_is_unmodelled": m_unmodelled, "fuzz": m_fuzz, "S1_signature": m_signature, "perf": m_perf,
    "capabilities": m_capabilities,
}

# Pass marks (plan v4.1 §4 and milestone gates). Each returns True/False/None(=not implemented).
GATES = [
    ("S1 top-1 ≥ 0.80 (fixed 180-case set)", lambda r: r["S1_signature"]["top1"] >= 0.80),
    ("S1 top-3 ≥ 0.95", lambda r: r["S1_signature"]["top3"] >= 0.95),
    ("S1 described within 64 samples (median)", lambda r: r["S1_signature"]["described_median_samples"] <= 64),
    ("M3 ramp false jumps = 0", lambda r: r["false_jumps_per_1000"]["ramp"] == 0),
    ("M3 sine false jumps = 0", lambda r: r["false_jumps_per_1000"]["sine"] == 0),
    ("M3 1-LSB blip: stays scalar, no event", lambda r: r["quantised_blip_flagged"]["kind"] == "scalar"
     and not r["quantised_blip_flagged"]["notes_at_blip"]),
    ("M3 period error bar present", lambda r: None if r["period"]["sine_err_bar"] is NA else True),
    ("M3 white noise ⇒ unmodelled", lambda r: r["white_is_unmodelled"] is True),
    ("M3 flicker exceedance ≤ 2× nominal (0.54%)", lambda r: r["band_exceedance"]["flicker"] <= 2 * NOMINAL_3SIGMA),
    ("M3 white exceedance within 0.5–2× nominal", lambda r: 0.5 * NOMINAL_3SIGMA <= r["band_exceedance"]["white"]
     <= 2 * NOMINAL_3SIGMA),
    ("S3 exactly one episode per true crossing", lambda r: r["chatter"]["activations"] == 1),
    ("S4 1σ shift detected ≤ 10 samples", lambda r: (r["detection"]["mean_shift_delay"] or 1e9) <= 10),
    ("S4 correlated shift detected", lambda r: r["detection"]["ar1_mean_shift_delay"] is not None),
    ("S3 chatter events = 0", lambda r: r["chatter"]["chatter_events"] == 0),
    ("S3 fleeting alarms = 0", lambda r: r["chatter"]["fleeting"] == 0),
    ("M2 hostile input: 0 exceptions", lambda r: r["hostile"]["exceptions"] == 0),
    ("M2 fuzz (2000 random inputs): 0 exceptions", lambda r: r["fuzz"]["exceptions"] == 0),
    ("M3 alias flag", lambda r: None if r["capabilities"]["alias_flag"] is NA else True),
    ("M3 τ/ζ identification", lambda r: None if r["capabilities"]["tau_zeta"] is NA else True),
    ("S5 PIT calibration", lambda r: None if r["capabilities"]["pit_calibration"] is NA else True),
    ("M2 jitter/skew attribution", lambda r: None if r["capabilities"]["timing_jitter_skew"] is NA else True),
    ("S6 CPU ≤ 5% of one core (PC, demo load)", lambda r: r["perf"]["cpu_share_realtime"] <= 0.05),
]


def run_all() -> Dict[str, object]:
    res: Dict[str, object] = {}
    for k, fn in METRICS.items():
        try:
            res[k] = fn()
        except Exception:                                             # noqa: BLE001
            res[k] = {"error": traceback.format_exc(limit=2)}
    return res


def judge(res) -> List[tuple]:
    rows = []
    for label, g in GATES:
        try:
            v = g(res)
        except Exception:                                             # noqa: BLE001
            v = "error"
        rows.append((label, v))
    return rows


def render(res, rows, base) -> str:
    sym = {True: "PASS", False: "FAIL", None: "— (not implemented)", "error": "ERROR"}
    lines = ["# SUFD scoreboard", "",
             f"Build: {res.get('_label', '?')} · generated {time.strftime('%Y-%m-%d %H:%M')}", "",
             "| Gate | Result |", "|---|---|"]
    lines += [f"| {lbl} | {sym.get(v, v)} |" for lbl, v in rows]
    passed = sum(1 for _, v in rows if v is True)
    lines += ["", f"**{passed} / {len(rows)} gates pass.**", "", "## Raw metrics", "", "```json",
              json.dumps({k: v for k, v in res.items() if not k.startswith("_")}, indent=1, default=str), "```"]
    if base:
        lines += ["", "## Changed since baseline", ""]
        diffs = [f"- `{k}`: {json.dumps(base.get(k), default=str)} → {json.dumps(v, default=str)}"
                 for k, v in res.items() if not k.startswith("_") and base.get(k) != v and k != "perf"]
        lines += diffs or ["- (no metric changed apart from timing)"]
    return "\n".join(lines) + "\n"


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")                      # Windows consoles default to cp1252
    except Exception:                                                 # noqa: BLE001
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", action="store_true", help="record bench/baseline.json")
    ap.add_argument("--label", default="current")
    a = ap.parse_args()
    res = run_all()
    res["_label"] = "slice-1 baseline" if a.baseline else a.label
    rows = judge(res)
    base_p = HERE / "baseline.json"
    if a.baseline:
        base_p.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    base = json.loads(base_p.read_text(encoding="utf-8")) if base_p.exists() and not a.baseline else None
    (HERE / "scoreboard.md").write_text(render(res, rows, base), encoding="utf-8")
    for lbl, v in rows:
        print(f"{'PASS' if v is True else ('----' if v is None else 'FAIL')}  {lbl}")
    print(f"{sum(1 for _, v in rows if v is True)}/{len(rows)} pass · wrote bench/scoreboard.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
