"""akpaneka — judgement and action. Notes, the follower and the learned watch.

SUFD's side of shared attention: a 'now' cursor and Notes — what it noticed and *why* (every note carries
its reason from the envelope; the human is never handed an unexplained alarm).
Human's side: a pointer at a time. SUFD answers a pointer from the envelope.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from ..idea.envelope import IdeaEnvelope
from ..eno.signal import EnoSignal

JUMP_AT = 6.0          # surprise (x typical step) that earns a note
DEBOUNCE = 5           # samples between jump notes


@dataclass
class AkpanekaNote:
    t: float
    signal: str
    level: str          # info | notice | warn
    text: str
    why: str            # the envelope fact behind it


class AkpanekaFollower:
    """Turns a signal's envelope into notes. One per signal; call observe() per sample."""

    def __init__(self, signal: EnoSignal, keep: int = 50):
        self.sig = signal
        from ..edimek.follow import EdimekFollow as Follow     # lazy: edimek.follow imports AkpanekaNote from here
        self.follow = Follow()
        self.keep = keep
        self._since_jump = DEBOUNCE
        self._last_trend = "steady"
        self._last_state = None
        self._state_since: Optional[float] = None
        self.watch: Optional["AkpanekaWatch"] = None

    def _add(self, n: AkpanekaNote) -> None:
        self.follow.notes.append(n)
        del self.follow.notes[: -self.keep]

    def observe(self, t: float, v) -> None:
        env = self.sig.env
        name = self.sig.name
        if env.n < 8:
            return
        self._since_jump += 1

        if env.kind in ("binary", "categorical"):
            if self._last_state is not None and v != self._last_state:
                dwell = t - (self._state_since or t)
                self._add(AkpanekaNote(t, name, "notice", f"changed to {v!r} after {dwell:.0f} s",
                               f"{env.toggles} change(s) in {env.n} samples"))
            if v != self._last_state:
                self._last_state, self._state_since = v, t
        elif env.surprise >= JUMP_AT and self._since_jump >= DEBOUNCE:
            self._since_jump = 0
            self._add(AkpanekaNote(t, name, "notice", f"jumped {env.surprise:.1f}x its usual step",
                           f"typical step {env._ew_step:.3g}, noise {env.noise:.3g}"))

        # trend only on non-cyclic scalars observed long enough to rule a cycle out
        if (env.trend != self._last_trend and env.kind == "scalar" and env.period is None
                and env.n >= 32 and (env.last_t - env.first_t) >= 30):
            if env.trend != "steady":
                self._add(AkpanekaNote(t, name, "info", f"started {env.trend}: {abs(env.trend_per_s) * 60:.2g} per min",
                               f"least-squares slope over the last {min(env.n, 256)} samples exceeds 3x noise"))
            self._last_trend = env.trend

        if self.watch:
            n = self.watch.check(t, v, env)
            if n:
                n.signal = name
                self._add(n)

    def explain(self, t: float) -> str:
        """Answer the human pointing at time t, from the envelope. No language model."""
        env = self.sig.env
        if not self.sig.buf:
            return "nothing observed yet"
        t_near, v = min(self.sig.buf, key=lambda s: abs(s[0] - t))
        parts = [f"at t={t_near:.1f}: {v!r}"]
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            if self.watch:      # judge against what the sense was confirmed to be like
                z = (v - self.watch.base) / self.watch.spread
                ref = f"its confirmed baseline {self.watch.base:.3g} (±{self.watch.spread:.2g})"
            elif env.std > 0:
                z = (v - env.mean) / env.std
                ref = f"its mean {env.mean:.3g}"
            else:
                z = ref = None
            if ref:
                where = "typical" if abs(z) < 1.5 else ("high" if z > 0 else "low")
                parts.append(f"{where} for this signal ({z:+.1f}σ from {ref})")
        near = [n for n in self.follow.notes if abs(n.t - t_near) <= max(3 * (env.dt or 1), 3)]
        for n in near:
            parts.append(f"I noted: {n.text} ({n.why})")
        return "; ".join(parts)


class AkpanekaWatch:
    """Created when a sense is confirmed and put to use.

    Baseline is learned from the sense's own envelope at that moment — mean and a
    spread floor of 3x noise — so the threshold is *derived*, not hard-coded.
    """

    def __init__(self, label: str, env: IdeaEnvelope, k: float = 5.0):
        self.label = label
        self.base = env.mean
        self.spread = max(env.std, 3 * (env.noise if not math.isnan(env.noise) else 0.0), 1e-9)
        self.hi = self.base + k * self.spread
        self.lo = self.base - k * self.spread
        self._above = False

    def check(self, t: float, v, env: IdeaEnvelope) -> Optional[AkpanekaNote]:
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            return None
        if v > self.hi and not self._above:
            self._above = True
            return AkpanekaNote(t, self.label, "warn",
                        f"above its learned band (> {self.hi:.3g}); now {v:.3g}",
                        f"baseline {self.base:.3g} +/- {self.spread:.3g} learned when first confirmed")
        if v <= self.hi * 0.999 and self._above and v < self.base + 0.5 * (self.hi - self.base):
            self._above = False
            return AkpanekaNote(t, self.label, "info", "back inside its learned band", f"{self.base:.3g} baseline")
        return None
