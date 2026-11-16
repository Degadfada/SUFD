"""Envelope: what SUFD has learned about a signal, sufficient to receive and render it.

Cheap O(1) updates run on every sample (Welford, EW step scale, surprise, binary
dwell, category counts). Heavier window estimates (robust range, rate, noise, trend,
period) are refreshed every REFRESH samples. Nothing here is a language model.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

REFRESH = 16          # samples between window refreshes
WINDOW = 256          # samples used for window estimates
TREND_N = 64          # samples used for the trend
WARMUP = 8            # samples before surprise is reported
MAX_CATEGORIES = 8    # beyond this a discrete-looking signal is treated as scalar
SURPRISE_CAP = 99.0


def _quantile(sorted_vals: Sequence[float], q: float) -> float:
    if not sorted_vals:
        return float("nan")
    i = q * (len(sorted_vals) - 1)
    lo, hi = int(math.floor(i)), int(math.ceil(i))
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (i - lo)


def _resample(xs: Sequence[float], ys: Sequence[float], dt: float) -> List[float]:
    """Linear interpolation onto a uniform grid of spacing dt (sources jitter)."""
    if not dt or dt != dt or len(xs) < 2:
        return list(ys)
    out, j, x = [], 0, xs[0]
    while x <= xs[-1] + 1e-12:
        while j < len(xs) - 2 and xs[j + 1] < x:
            j += 1
        x0, x1 = xs[j], xs[j + 1]
        f = 0.0 if x1 == x0 else min(1.0, max(0.0, (x - x0) / (x1 - x0)))
        out.append(ys[j] + (ys[j + 1] - ys[j]) * f)
        x += dt
    return out


def _median(vals: Sequence[float]) -> float:
    return _quantile(sorted(vals), 0.5)


class Envelope:
    def __init__(self) -> None:
        self.n = 0
        self.first_t: Optional[float] = None
        self.last_t: Optional[float] = None
        self.kind = "unknown"        # unknown | scalar | binary | categorical | vector
        self.dims = 1
        # running scalar stats (Welford)
        self._mean = 0.0
        self._m2 = 0.0
        self._n_num = 0
        self.min = math.inf
        self.max = -math.inf
        # surprise
        self._prev: Optional[float] = None
        self._ew_step = 0.0
        self.surprise = 0.0
        self.max_surprise = 0.0
        # discrete
        self._distinct: Dict[object, int] = {}
        self.toggles = 0
        self.last_change_t: Optional[float] = None
        self._last_val: object = None
        # window estimates (refreshed)
        self.p01 = self.p50 = self.p99 = float("nan")
        self.dt = float("nan")
        self.jitter = float("nan")
        self.noise = float("nan")
        self.r1 = float("nan")
        self.trend_per_s = 0.0
        self.trend = "steady"
        self.period: Optional[float] = None
        self.period_strength = 0.0
        self.component_range: List[Tuple[float, float]] = []
        self.is_integer = False
        self._many = False
        self._hits = 0
        self._last_period = (None, 0.0)

    # ------------------------------------------------------------ online
    @property
    def mean(self) -> float:
        return self._mean

    @property
    def std(self) -> float:
        return math.sqrt(self._m2 / (self._n_num - 1)) if self._n_num > 1 else 0.0

    def update(self, t: float, v, buf) -> None:
        self.n += 1
        if self.first_t is None:
            self.first_t = t
        self.last_t = t

        if isinstance(v, tuple):
            self.kind, self.dims = "vector", len(v)
            mag = math.sqrt(sum(x * x for x in v))
            self._numeric(mag, prev=self._prev)
            self._prev = mag
        elif isinstance(v, str):
            self._discrete(t, v)
            self.kind = "categorical"
        elif isinstance(v, bool):
            self._discrete(t, v)
            self.kind = "binary"
        else:
            x = float(v)
            if not self._many:
                self._distinct[x] = self._distinct.get(x, 0) + 1
            if len(self._distinct) > MAX_CATEGORIES * 4:
                self._distinct = {}  # stop tracking; plainly continuous
                self._many = True
            self._numeric(x, prev=self._prev)
            self._prev = x
            self.is_integer = all(float(k).is_integer() for k in self._distinct) if self._distinct else self.is_integer
            self.kind = self._numeric_kind()
            if self.kind in ("binary", "categorical"):
                self._discrete_toggle(t, x)

        if self.n % REFRESH == 0 or self.n == WARMUP:
            self._refresh(buf)

    def _numeric_kind(self) -> str:
        d = len(self._distinct)
        if self._many or d == 0:
            return "scalar"
        if d <= 2 and self.n >= WARMUP * 2:
            return "binary"
        if d <= MAX_CATEGORIES and self.is_integer and self.n >= WARMUP * 4:
            return "categorical"
        return "scalar"

    def _numeric(self, x: float, prev: Optional[float]) -> None:
        self._n_num += 1
        d = x - self._mean
        self._mean += d / self._n_num
        self._m2 += d * (x - self._mean)
        self.min, self.max = min(self.min, x), max(self.max, x)
        if prev is not None:
            step = abs(x - prev)
            floor = 1e-6 * max(1.0, abs(self._mean))
            s = min(SURPRISE_CAP, step / max(self._ew_step, floor)) if self._n_num > WARMUP else 0.0
            self.surprise = s
            self.max_surprise = max(self.max_surprise * 0.995, s)
            self._ew_step = step if self._ew_step == 0 else 0.95 * self._ew_step + 0.05 * step

    def _discrete(self, t: float, v) -> None:
        self._distinct[v] = self._distinct.get(v, 0) + 1
        self._discrete_toggle(t, v)
        self.surprise = 0.0

    def _discrete_toggle(self, t: float, v) -> None:
        if self._last_val is not None and v != self._last_val:
            self.toggles += 1
            self.last_change_t = t
            self.surprise = SURPRISE_CAP if self.n > WARMUP and self.toggles < 3 else min(
                SURPRISE_CAP, self.n / max(1, self.toggles))
        self._last_val = v

    # ------------------------------------------------------------ windowed
    def _refresh(self, buf) -> None:
        items = list(buf)[-WINDOW:]
        if len(items) < 4:
            return
        ts = [s[0] for s in items]
        dts = [b - a for a, b in zip(ts, ts[1:]) if b > a]
        if dts:
            self.dt = _median(dts)
            self.jitter = _median([abs(d - self.dt) for d in dts]) / self.dt if self.dt else float("nan")

        if self.kind == "vector":
            cols = list(zip(*[s[1] for s in items]))
            self.component_range = [(min(c), max(c)) for c in cols]
            ys = [math.sqrt(sum(x * x for x in s[1])) for s in items]
        elif self.kind in ("scalar", "binary", "categorical") and not isinstance(items[-1][1], str):
            ys = [float(s[1]) for s in items]
        else:
            return

        srt = sorted(ys)
        self.p01, self.p50, self.p99 = _quantile(srt, 0.01), _quantile(srt, 0.5), _quantile(srt, 0.99)
        if self.kind != "scalar" and self.kind != "vector":
            return

        diffs = [b - a for a, b in zip(ys, ys[1:])]
        self.noise = 1.4826 * _median([abs(d - _median(diffs)) for d in diffs]) / math.sqrt(2) if diffs else 0.0

        # least-squares trend over the recent samples, so a regime change is noticed promptly
        ys_all, ts_all = ys, ts
        ys, ts = ys[-TREND_N:], ts[-TREND_N:]
        n = len(ys)
        t0 = ts[0]
        xs = [t - t0 for t in ts]
        mx, my = sum(xs) / n, sum(ys) / n
        sxx = sum((x - mx) ** 2 for x in xs)
        slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx else 0.0
        self.trend_per_s = slope
        change = slope * (xs[-1] - xs[0])
        rng = max(self.p99 - self.p01, 1e-12)
        self.trend = "steady"
        if abs(change) >= max(3 * (self.noise or 0.0), 0.15 * rng):
            self.trend = "rising" if change > 0 else "falling"

        ys, ts = ys_all, ts_all
        n = len(ys)
        my_all = sum(ys) / n
        # smoothness: lag-1 autocorrelation of the mean-removed signal (1 = smooth, 0 = white noise)
        cen = [y - my_all for y in ys]
        cvar = sum(c * c for c in cen)
        if cvar > 0 and n > 4:
            self.r1 = sum(a * b for a, b in zip(cen, cen[1:])) / cvar
        # period: from the detrended full window, so a drift does not mask the cycle
        xs_all = [t - ts[0] for t in ts]
        mx_a = sum(xs_all) / n
        sxx_a = sum((x - mx_a) ** 2 for x in xs_all)
        sl_a = sum((x - mx_a) * (y - my_all) for x, y in zip(xs_all, ys)) / sxx_a if sxx_a else 0.0
        resid = [y - (my_all + sl_a * (x - mx_a)) for x, y in zip(xs_all, ys)]
        resid = _resample(xs_all, resid, self.dt)     # autocorrelation needs a uniform grid
        n_r = len(resid)
        rvar = sum(r * r for r in resid)
        total_sd = math.sqrt(cvar / n)
        found = (None, 0.0)
        if math.sqrt(rvar / n_r) >= 0.1 * total_sd:     # else it is rounding, not a cycle
            found = self._period_once(resid, rvar)
        # sticky: a period must be seen twice to be believed, and survives one miss
        if found[0]:
            self._hits, self._last_period = min(self._hits + 1, 3), found
        else:
            self._hits = max(self._hits - 1, 0)
        self.period, self.period_strength = self._last_period if self._hits >= 2 else (None, 0.0)

    def _period_once(self, resid: List[float], var: float):
        n = len(resid)
        if n < 24 or var <= 0 or not self.dt or math.isnan(self.dt):
            return (None, 0.0)
        acf = []
        for lag in range(1, n // 3):
            acf.append(sum(resid[i] * resid[i + lag] for i in range(n - lag)) / var)
        # first descent below zero, then the highest following peak
        start = next((i for i, a in enumerate(acf) if a < 0), None)
        if start is None:
            return (None, 0.0)
        best, best_i = 0.0, None
        for i in range(start, len(acf) - 1):
            if acf[i] >= acf[i - 1] and acf[i] >= acf[i + 1] and acf[i] > best:
                best, best_i = acf[i], i
        if best_i is not None and best >= 0.5:
            return ((best_i + 1) * self.dt, best)
        return (None, 0.0)

    # ------------------------------------------------------------ meaning
    @property
    def rate_hz(self) -> float:
        return 1.0 / self.dt if self.dt and not math.isnan(self.dt) else float("nan")

    @property
    def duty(self) -> float:
        """Fraction of samples high, for binary signals."""
        if not self._distinct:
            return float("nan")
        hi = max(self._distinct, key=lambda k: float(k) if not isinstance(k, str) else 0)
        return self._distinct[hi] / sum(self._distinct.values())

    @property
    def categories(self) -> List[object]:
        return sorted(self._distinct, key=lambda k: str(k))

    def describe(self) -> str:
        """Behaviour in plain words. States what was seen, never what it 'is'."""
        if self.n < WARMUP:
            return f"still observing ({self.n} samples so far)"
        rate = f"{self.rate_hz:.3g}/s" if not math.isnan(self.rate_hz) else "irregular rate"
        if self.kind == "binary":
            return (f"two-state, high {self.duty:.0%} of the time so far, "
                    f"{self.toggles} changes, {rate}")
        if self.kind == "categorical":
            return f"{len(self._distinct)} distinct value(s) so far, {self.toggles} changes, {rate}"
        if self.kind == "vector":
            return f"{self.dims}-component vector, typical magnitude {self.p50:.3g}, {rate}"
        smooth = "smooth" if self.r1 > 0.9 else ("fairly smooth" if self.r1 > 0.7 else ("jittery" if self.r1 > 0.4 else "noisy"))
        speed = "slow" if (self.period or 0) > 20 or self.dt >= 0.5 and self.noise < 0.2 * (self.p99 - self.p01 + 1e-12) else "fast"
        parts = [f"{speed}, {smooth}", f"{self.p01:.3g} to {self.p99:.3g}"]
        if self.trend != "steady":
            parts.append(f"{self.trend} {abs(self.trend_per_s) * 60:.2g} per min")
        else:
            parts.append("holding steady")
        if self.period:
            parts.append(f"repeats every {self.period:.3g} s")
        parts.append(rate)
        return ", ".join(parts)

    def candidates(self, hint: Optional[str] = None) -> List[Tuple[str, float, str]]:
        """Ranked guesses at what a signal might be, each WITH its reason.

        These are heuristics for the human to confirm, never facts. A source hint
        (e.g. unit "C") outranks everything because the device itself said so.
        """
        out: List[Tuple[str, float, str]] = []
        if hint:
            out.append((hint, 0.95, "the source announced it"))
        if self.n < WARMUP:
            return out
        lo, hi = self.p01, self.p99
        if self.kind == "binary":
            out.append(("switch / presence / door state", 0.5, "only two values so far"))
        elif self.kind == "vector" and self.dims == 3:
            out.append(("motion / orientation (accelerometer-like)", 0.5, "3-component vector"))
        elif self.kind == "scalar" and self.period:
            out.append(("oscillating source (audio / vibration-like)", 0.55, f"repeats every {self.period:.3g} s"))
        elif self.kind == "scalar" and self.r1 > 0.7:
            if -40 <= lo and hi <= 125 and self.dt >= 0.2:
                out.append(("temperature-like", 0.6, f"slow, fairly smooth, bounded {lo:.3g} to {hi:.3g}"))
            if 0 <= lo and hi <= 100:
                out.append(("level / percentage-like", 0.4, "smooth, within 0 to 100"))
        return sorted(out, key=lambda c: -c[1])

    def snapshot(self) -> Dict[str, object]:
        return {
            "n": self.n, "kind": self.kind, "dims": self.dims,
            "rate_hz": None if math.isnan(self.rate_hz) else round(self.rate_hz, 4),
            "range": None if math.isnan(self.p01) else [round(self.p01, 4), round(self.p99, 4)],
            "mean": round(self.mean, 4), "std": round(self.std, 4),
            "noise": None if math.isnan(self.noise) else round(self.noise, 4),
            "trend": self.trend, "trend_per_min": round(self.trend_per_s * 60, 4),
            "period_s": self.period and round(self.period, 3),
            "toggles": self.toggles, "surprise": round(self.surprise, 2),
            "summary": self.describe(),
        }
