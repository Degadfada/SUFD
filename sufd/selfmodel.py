"""Mind: SUFD's core. Owns every signal, its follower, and the sense ledger.

Self-observation is not a separate subsystem: SUFD's own metrics are pushed through
the same Signal -> Envelope -> Lens pipeline as any ESP32 sensor.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .envelope import WARMUP
from .follow import Follow, Follower, Note, Watch
from .lens import Lens, choose_lens
from .render import render_svg
from .signal import Signal

# label keyword -> the need it can inform. Deliberately tiny and inspectable.
NEEDS = {
    "temperature": "thermal safety / comfort",
    "battery": "energy budget",
    "door": "security",
}


@dataclass
class SenseRecord:
    name: str
    first_seen: float
    state: str = "new"              # new -> observing -> described -> named -> in_use
    label: Optional[str] = None
    label_source: Optional[str] = None   # "announced" | "human"
    summary: str = ""
    candidates: List[tuple] = field(default_factory=list)
    uses: List[str] = field(default_factory=list)
    history: List[tuple] = field(default_factory=list)   # (t, state, text)

    def move(self, t: float, state: str, text: str) -> None:
        self.state = state
        self.history.append((t, state, text))


class SelfProbe:
    """SUFD's own vital signs, as plain numbers. Clock is injectable for tests."""

    def __init__(self, clock: Callable[[], float] = time.perf_counter,
                 cpu: Callable[[], float] = time.process_time):
        self.clock, self.cpu = clock, cpu
        self._last_wall = clock()
        self._last_cpu = cpu()

    def read(self, mind: "Mind") -> Dict[str, float]:
        w, c = self.clock(), self.cpu()
        dw, dc = max(w - self._last_wall, 1e-9), c - self._last_cpu
        self._last_wall, self._last_cpu = w, c
        return {
            "self.cpu_load": min(1.0, dc / dw),
            "self.signals": float(len(mind.signals)),
            "self.notes": float(sum(len(f.follow.notes) for f in mind.followers.values())),
        }


class Mind:
    def __init__(self, probe: Optional[SelfProbe] = None):
        self.signals: Dict[str, Signal] = {}
        self.followers: Dict[str, Follower] = {}
        self.lenses: Dict[str, Lens] = {}
        self.ledger: Dict[str, SenseRecord] = {}
        self.attn: Dict[str, float] = {}
        self.events: List[tuple] = []        # (t, text) — SUFD's own narration
        self.probe = probe or SelfProbe()

    # ----------------------------------------------------------- ingest
    def ingest(self, name: str, t: float, v, hint: Optional[str] = None) -> None:
        sig = self.signals.get(name)
        if sig is None:                                   # FIRST CONTACT
            sig = self.signals[name] = Signal(name, hint=hint)
            self.followers[name] = Follower(sig)
            rec = self.ledger[name] = SenseRecord(name, first_seen=t)
            msg = "new signal noticed" + (f" (announced as {hint!r})" if hint else "")
            rec.move(t, "new", msg)
            self.events.append((t, f"{name}: {msg}"))
            if hint:
                rec.label, rec.label_source = hint, "announced"
        sig.push(t, v)
        self.followers[name].observe(t, v)
        self.attn[name] = 0.98 * self.attn.get(name, 0.0) + max(sig.env.surprise - 3.0, 0.0)
        self._advance(name, t)

    def _advance(self, name: str, t: float) -> None:
        rec, env = self.ledger[name], self.signals[name].env
        if rec.state == "new" and env.n >= 1:
            rec.move(t, "observing", "reading only; assuming nothing")
        if rec.state == "observing" and env.n >= WARMUP * 4:
            rec.summary = env.describe()
            rec.candidates = env.candidates(self.signals[name].hint)
            rec.move(t, "described", rec.summary)
            self.events.append((t, f"{name}: {rec.summary}"))
            if rec.label:                                  # announced: skip the question
                self._put_to_use(name, t)
            else:
                guess = "; ".join(f"{c[0]} ({c[2]})" for c in rec.candidates[:2]) or "no confident guess"
                self.events.append((t, f"{name}: what is this? candidates: {guess}"))
        if rec.state == "described" and not rec.label and env.n % 64 == 0:   # re-open as it matures
            old_top = rec.candidates[0][0] if rec.candidates else None
            rec.candidates = env.candidates(self.signals[name].hint)
            new_top = rec.candidates[0][0] if rec.candidates else None
            if new_top != old_top:
                why = rec.candidates[0][2] if rec.candidates else ""
                self.events.append((t, f"{name}: revised guess to {new_top} ({why})"))
        rec.summary = env.describe() if rec.state in ("described", "named", "in_use") else rec.summary

    def confirm(self, name: str, label: str, t: float) -> None:
        """The human names a sense once; SUFD binds it to a use."""
        rec = self.ledger[name]
        rec.label, rec.label_source = label, "human"
        rec.move(t, "named", f"human confirmed: {label}")
        self.events.append((t, f"{name}: human says this is {label!r}"))
        self._put_to_use(name, t)

    def _put_to_use(self, name: str, t: float) -> None:
        rec, sig = self.ledger[name], self.signals[name]
        for key, need in NEEDS.items():
            if rec.label and key in rec.label.lower():
                rec.uses.append(f"informs {need}")
        if sig.env.kind == "scalar" and rec.label:
            self.followers[name].watch = Watch(name, sig.env)
            w = self.followers[name].watch
            rec.uses.append(f"watching for readings above {w.hi:.3g} (baseline {w.base:.3g}, learned)")
        if rec.uses:
            rec.move(t, "in_use", "; ".join(rec.uses))
            self.events.append((t, f"{name}: now in use — {'; '.join(rec.uses)}"))

    # ------------------------------------------------------- self-sense
    def tick_self(self, t: float) -> None:
        for k, v in self.probe.read(self).items():
            self.ingest(k, t, v)

    # -------------------------------------------------------- attention
    def attention(self, budget_hz: float = 20.0) -> List[tuple]:
        """Spend a fixed human-bandwidth budget where the surprise is.

        Returns [(name, score, render_hz)] — quiet on-model signals get a trickle,
        surprising ones get the frames. This is SUFD pointing its own capability
        (rendering time) at what matters.
        """
        names = list(self.signals)
        if not names:
            return []
        floor = 0.5
        spare = max(budget_hz - floor * len(names), 0.0)
        total = sum(self.attn.get(n, 0.0) for n in names) or 1.0
        out = [(n, self.attn.get(n, 0.0), floor + spare * self.attn.get(n, 0.0) / total) for n in names]
        return sorted(out, key=lambda r: -r[1])

    # --------------------------------------------------------- surfaces
    def lens(self, name: str) -> Lens:
        self.lenses[name] = choose_lens(self.signals[name].env, self.lenses.get(name))
        return self.lenses[name]

    def panel(self, name: str, now: Optional[float] = None, human_t: Optional[float] = None) -> dict:
        sig, fol = self.signals[name], self.followers[name]
        fol.follow.human_t = human_t
        lens = self.lens(name)
        rec = self.ledger[name]
        return {
            "name": name, "label": rec.label, "state": rec.state, "mark": lens.mark,
            "reason": lens.reason, "summary": sig.env.describe(),
            "svg": render_svg(sig, lens, fol.follow, now),
            "notes": list(fol.follow.notes[-4:]),
            "pointer": fol.explain(human_t) if human_t is not None else None,
        }

    def senses(self) -> List[dict]:
        """'What can you sense?' answered from SUFD's own state."""
        return [{"name": r.name, "state": r.state, "label": r.label, "by": r.label_source,
                 "summary": r.summary, "uses": r.uses, "first_seen": r.first_seen}
                for r in self.ledger.values()]
