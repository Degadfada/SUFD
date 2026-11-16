"""edimek — surface. EdimekLens: a visual encoding chosen from the envelope, not from any app.

The grammar (see spec/first-principles.md §4):
    scalar          -> strip       (position on a common scale)
    binary          -> steps       (state + dwell time)
    categorical     -> lanes       (membership + sequence)
    vector          -> trajectory  (motion in the plane of two components)
Every choice records a human-readable `reason`, so the person can follow *why*
the signal is drawn the way it is.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from ..idea.envelope import IdeaEnvelope


# ----------------------------------------------------------------- scales
def nice_num(x: float, round_: bool) -> float:
    """Heckbert's 'nice number': 1, 2, 5 or 10 times a power of ten."""
    if x <= 0 or math.isnan(x):
        return 1.0
    e = math.floor(math.log10(x))
    f = x / (10 ** e)
    if round_:
        n = 1 if f < 1.5 else 2 if f < 3 else 5 if f < 7 else 10
    else:
        n = 1 if f <= 1 else 2 if f <= 2 else 5 if f <= 5 else 10
    return n * (10 ** e)


def nice_ticks(lo: float, hi: float, target: int = 5) -> List[float]:
    if hi <= lo:
        hi = lo + 1.0
    step = nice_num(nice_num(hi - lo, False) / max(1, target - 1), True)
    first = math.ceil(lo / step) * step
    out, v = [], first
    while v <= hi + step * 1e-9:
        out.append(round(v, 10))
        v += step
    return out


def decimate_minmax(samples: Sequence[Tuple[float, float]], t0: float, t1: float,
                    columns: int) -> List[Tuple[float, float]]:
    """Reduce samples to at most ~2 points per pixel column, keeping each column's
    min and max so a one-sample spike is never averaged away."""
    if len(samples) <= columns * 2 or t1 <= t0:
        return list(samples)
    buckets: List[List[Tuple[float, float]]] = [[] for _ in range(columns)]
    for t, v in samples:
        i = min(columns - 1, max(0, int((t - t0) / (t1 - t0) * columns)))
        buckets[i].append((t, v))
    out: List[Tuple[float, float]] = []
    for b in buckets:
        if not b:
            continue
        lo, hi = min(b, key=lambda s: s[1]), max(b, key=lambda s: s[1])
        out.extend(sorted({lo, hi}, key=lambda s: s[0]))
    return out


@dataclass
class EdimekAxis:
    """A y-axis that widens immediately but narrows only after sustained evidence,
    so it does not 'breathe' and make the human lose the signal."""
    lo: float = 0.0
    hi: float = 1.0
    log: bool = False
    primed: bool = False
    _votes: int = 0
    SHRINK_AFTER = 20

    def fit(self, lo: float, hi: float) -> None:
        pad = (hi - lo) * 0.08 or max(abs(hi) * 0.05, 0.5)
        step = nice_num(nice_num((hi - lo) + 2 * pad, False) / 4, True)
        nlo, nhi = math.floor((lo - pad) / step) * step, math.ceil((hi + pad) / step) * step
        if not self.primed:
            self.lo, self.hi, self.primed = nlo, nhi, True
            return
        if nlo < self.lo or nhi > self.hi:                  # widen now
            self.lo, self.hi = min(self.lo, nlo), max(self.hi, nhi)
            self._votes = 0
        elif (nhi - nlo) < 0.6 * (self.hi - self.lo):       # narrow only if it persists
            self._votes += 1
            if self._votes >= self.SHRINK_AFTER:
                self.lo, self.hi, self._votes = nlo, nhi, 0
        else:
            self._votes = 0


@dataclass
class EdimekLens:
    mark: str                       # strip | steps | lanes | trajectory | none
    window_s: float
    reason: str
    axis: EdimekAxis = field(default_factory=EdimekAxis)
    categories: List[object] = field(default_factory=list)


def choose_window(env: IdeaEnvelope) -> Tuple[float, str]:
    if env.period:
        w = min(600.0, max(10.0, 3 * env.period))
        return w, f"window = 3 periods ({env.period:.3g} s) so the eye can lock to the cycle"
    if env.dt and not math.isnan(env.dt):
        w = min(300.0, max(30.0, 120 * env.dt))
        return w, f"window = ~120 samples at {env.rate_hz:.3g}/s"
    return 30.0, "default 30 s window until the rate is known"


def edimek_choose_lens(env: IdeaEnvelope, previous: Optional[EdimekLens] = None) -> EdimekLens:
    """Pick the encoding from the envelope. Reuses the previous EdimekAxis (hysteresis)."""
    window, wreason = choose_window(env)
    axis = previous.axis if previous else EdimekAxis()

    if env.n < 8 or env.kind == "unknown":
        return EdimekLens("none", window, "not enough samples yet to choose an encoding", axis)
    if env.kind == "binary":
        return EdimekLens("steps", window, f"only two values so far -> step line; {wreason}", axis)
    if env.kind == "categorical":
        return EdimekLens("lanes", window, f"{len(env.categories)} distinct values -> one lane each; {wreason}",
                    axis, env.categories)
    if env.kind == "vector":
        return EdimekLens("trajectory", window, f"{env.dims}-component vector -> path in the plane of components 0 and 1",
                    axis)
    log = env.p01 > 0 and env.p99 / max(env.p01, 1e-12) >= 1000
    axis.log = log
    why = "continuous number -> line on a common scale"
    if log:
        why += "; spans 3+ decades -> log axis"
    return EdimekLens("strip", window, f"{why}; {wreason}", axis)
