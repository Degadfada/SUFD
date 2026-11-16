"""kufre — self. The SUFD daemon core: bounded ingest, fault isolation, host self-signals, attention-budgeted
rendering and per-surface patches.

Design rules (knowledge base ids in brackets):
- hot path is O(1) per sample; one bad signal can never take the daemon down: it is quarantined [K-giac-latency];
- the queue is bounded and drops the OLDEST samples first (fresh data matters more), counting every drop;
- the event loop's own scheduling lag is a first-class signal (`self.loop_lag_ms`) [K-giac-latency];
- render rate follows the attention budget, with `focus` signals pinned to the patch rate;
- patches send only panels whose content changed since that surface last saw them, and name the sample ids they
  reflect so a surface can measure sensor-to-pixel latency end to end [S2].
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from collections import deque
from typing import Callable, Deque, Dict, List, Optional, Tuple

from .mind import KufreMind

def kufre_rss_mb() -> Optional[float]:
    """Resident memory of this process in MB (Windows working set, or /proc on Linux/the Pi). None if unknown."""
    try:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            class PMC(ctypes.Structure):
                _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
            pmc = PMC()
            pmc.cb = ctypes.sizeof(pmc)
            h = ctypes.windll.kernel32.GetCurrentProcess()
            ctypes.windll.psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
            if ctypes.windll.psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb):
                return round(pmc.WorkingSetSize / 1048576, 1)
            return None
        with open("/proc/self/statm") as f:
            return round(int(f.read().split()[1]) * os.sysconf("SC_PAGE_SIZE") / 1048576, 1)
    except Exception:                                                  # noqa: BLE001
        return None


PANEL_KEYS = ("name", "label", "state", "mark", "reason", "summary", "svg", "t0", "t1", "pointer", "quarantined")


class KufreSurface:
    """One connected human-facing screen. It remembers which panel versions it has seen."""

    def __init__(self, conn_id: int):
        self.conn_id = conn_id
        self.seen: Dict[str, int] = {}
        self.ids: Dict[str, List[int]] = {}
        self.seq = 0
        self.focus: set = set()

    def patch(self, runtime: "KufreRuntime") -> Optional[dict]:
        changed = {n: p for n, p in runtime.panels.items() if self.seen.get(n) != p["v"]}
        if not changed:
            return None
        out, reflect = {}, {}
        for n, p in changed.items():
            self.seen[n] = p["v"]
            out[n] = {k: p.get(k) for k in PANEL_KEYS}
            if n in self.ids:
                reflect[n] = self.ids.pop(n)[:100]
        self.seq += 1
        return {"type": "patch", "seq": self.seq, "panels": out, "reflect": reflect}


class KufreRuntime:
    def __init__(self, *, queue_max: int = 5000, quarantine_after: int = 5, patch_hz: float = 10.0,
                 render_budget_hz: float = 20.0, focus_prefixes: Tuple[str, ...] = ("phone.",),
                 clock: Callable[[], float] = time.monotonic, mind: Optional[KufreMind] = None,
                 max_signals: int = 256, ring_capacity: Optional[int] = None):
        self.clock = clock
        self.t0 = clock()
        self.mind = mind or KufreMind()
        if ring_capacity:
            self.mind.ring_capacity = ring_capacity
        self.max_signals = max_signals
        self.queue: Deque[tuple] = deque()
        self.queue_max = queue_max
        self.quarantine_after = quarantine_after
        self.patch_hz = patch_hz
        self.render_budget_hz = render_budget_hz
        self.focus_prefixes = focus_prefixes
        self.panels: Dict[str, dict] = {}
        self.surfaces: Dict[int, KufreSurface] = {}
        self.pointers: Dict[str, float] = {}
        self.dirty: set = set()
        self.last_render: Dict[str, float] = {}
        self.pending_ids: Dict[str, List[Tuple[int, int]]] = {}
        self.errors: Dict[str, int] = {}
        self.quarantined: Dict[str, str] = {}
        self.slow: Dict[str, int] = {}
        self.slow_ingest_s = 0.05
        self.stats = {"submitted": 0, "dropped": 0, "ingested": 0, "ingest_errors": 0, "patches": 0,
                      "renders": 0, "render_ms_total": 0.0, "slow_ingests": 0, "refused_new_signals": 0, "client_latency": None, "loop_lag_ms_max": 0.0}
        self._conn = 0
        self.patch_event = asyncio.Event()

    # ------------------------------------------------------------------ time and wiring
    def now(self) -> float:
        return self.clock() - self.t0

    def new_surface(self) -> KufreSurface:
        self._conn += 1
        s = KufreSurface(self._conn)
        self.surfaces[s.conn_id] = s
        return s

    def drop_surface(self, s: KufreSurface) -> None:
        self.surfaces.pop(s.conn_id, None)

    # ------------------------------------------------------------------ ingest (called by transports)
    def submit(self, name: str, value, hint: Optional[str] = None, conn_id: int = 0, sample_id: int = 0) -> bool:
        """Queue one sample stamped with ARRIVAL time. Returns False if it displaced an older sample."""
        self.stats["submitted"] += 1
        if name not in self.mind.signals and len(self.mind.signals) >= self.max_signals:
            self.stats["refused_new_signals"] += 1           # a sender cannot grow memory by inventing names
            return False
        displaced = False
        if len(self.queue) >= self.queue_max:
            self.queue.popleft()                                     # drop oldest, count it
            self.stats["dropped"] += 1
            displaced = True
        self.queue.append((self.now(), name, value, hint, conn_id, sample_id))
        return not displaced

    def drain(self, limit: int = 2000, budget_s: float = 0.006) -> int:
        """Ingest queued samples, but never hold the event loop longer than `budget_s` (default 6 ms).

        A slow ingest (a pathological signal) earns a strike; three strikes quarantine it, so one signal cannot
        starve the others. Anything left stays queued, bounded, for the next tick."""
        n, deadline = 0, time.perf_counter() + budget_s
        while self.queue and n < limit and time.perf_counter() < deadline:
            t, name, value, hint, conn_id, sid = self.queue.popleft()
            n += 1
            if name in self.quarantined:
                continue
            t_in = time.perf_counter()
            try:
                self.mind.ingest(name, round(t, 4), value, hint)
                self.errors[name] = 0
                self.stats["ingested"] += 1
                self.dirty.add(name)
                if sid:
                    self.pending_ids.setdefault(name, []).append((conn_id, sid))
            except Exception as e:                                   # noqa: BLE001  fault isolation is the point
                self.stats["ingest_errors"] += 1
                self.errors[name] = self.errors.get(name, 0) + 1
                if self.errors[name] >= self.quarantine_after:
                    self.quarantined[name] = f"{type(e).__name__}: {e}"[:120]
                    self.dirty.add(name)
            if time.perf_counter() - t_in > self.slow_ingest_s:
                self.slow[name] = self.slow.get(name, 0) + 1
                self.stats["slow_ingests"] += 1
                if self.slow[name] >= 3 and name not in self.quarantined:
                    self.quarantined[name] = f"ingest too slow (>{self.slow_ingest_s * 1000:.0f} ms, 3 times)"
                    self.dirty.add(name)
        return n

    # ------------------------------------------------------------------ rendering
    def _is_focus(self, name: str) -> bool:
        return name.startswith(self.focus_prefixes) or any(name in s.focus for s in self.surfaces.values())

    def render_due(self, focus_now: bool = False) -> int:
        """Render dirty signals. Focus signals render only on the patch tick (`focus_now`), so there is ONE
        coalescing stage between a sample and the pixel (two cascaded 10 Hz clocks gave p95 ~200 ms). Other signals
        follow their attention-derived render rate."""
        if not self.dirty:
            return 0
        rate = {n: hz for n, _, hz in self.mind.attention(self.render_budget_hz)}
        now, done = self.clock(), 0
        for name in list(self.dirty):
            if self._is_focus(name):
                if not focus_now:
                    continue
            else:
                hz = rate.get(name, 0.5)
                if now - self.last_render.get(name, -1e9) < 1.0 / max(hz, 0.1):
                    continue
            self.dirty.discard(name)
            self.last_render[name] = now
            t = time.perf_counter()
            self._render(name)
            self.stats["render_ms_total"] += 1000 * (time.perf_counter() - t)
            self.stats["renders"] += 1
            done += 1
        return done

    def _render(self, name: str) -> None:
        prev = self.panels.get(name, {"v": 0})
        if name in self.quarantined:
            p = {"name": name, "label": None, "state": "quarantined", "mark": "none", "svg": "", "t0": 0, "t1": 0,
                 "summary": "", "reason": "", "pointer": None, "quarantined": self.quarantined[name]}
        else:
            p = self.mind.panel(name, human_t=self.pointers.get(name))
            sig = self.mind.signals[name]
            t_end = sig.buf[-1][0] if sig.buf else 0.0
            p["t1"], p["t0"] = t_end, t_end - self.mind.lens(name).window_s
            p["notes"] = None
            p["quarantined"] = None
        p["v"] = prev["v"] + 1
        self.panels[name] = p
        ids = self.pending_ids.pop(name, [])
        for s in self.surfaces.values():
            mine = [i for c, i in ids if c == s.conn_id]
            if mine:
                s.ids.setdefault(name, []).extend(mine)

    def point(self, name: str, t: float) -> None:
        """The human points at time t on a signal; SUFD answers on the next render."""
        if name in self.mind.signals and isinstance(t, (int, float)) and t == t:
            self.pointers[name] = float(t)
            self.dirty.add(name)

    # ------------------------------------------------------------------ the loop
    async def run(self, stop: asyncio.Event, on_tick: Optional[Callable[[], None]] = None) -> None:
        """Drain, render and self-observe until `stop` is set. Cheap work only; never blocks the loop long."""
        next_self, next_lag, next_patch, tick = 0.0, 0.0, 0.0, 0.01
        expected = self.clock() + tick
        while not stop.is_set():
            await asyncio.sleep(tick)
            now = self.clock()
            lag_ms = max(0.0, (now - expected) * 1000.0)         # how late the loop woke up: host scheduling jitter
            expected = now + tick
            self.stats["loop_lag_ms_max"] = max(self.stats["loop_lag_ms_max"] * 0.999, lag_ms)
            try:
                if self.now() >= next_lag:                        # sample the lag signal at 10 Hz
                    self.mind.ingest("self.loop_lag_ms", round(self.now(), 4), round(lag_ms, 3))
                    self.dirty.add("self.loop_lag_ms")
                    next_lag = self.now() + 0.1
                self.drain()
                if self.now() >= next_self:
                    self.mind.tick_self(round(self.now(), 4))
                    next_self = self.now() + 1.0
                    self.dirty.update(n for n in self.mind.signals if n.startswith("self."))
                if self.clock() >= next_patch:                    # the single patch clock
                    next_patch = max(next_patch + 1.0 / self.patch_hz, self.clock() - 1.0 / self.patch_hz)
                    self.render_due(focus_now=True)
                    self.patch_event.set()                        # wake every surface at once...
                    self.patch_event.clear()                      # ...waiters are already released
                else:
                    self.render_due()
                if on_tick:
                    on_tick()
            except Exception:                                        # noqa: BLE001 the daemon must outlive any bug
                self.stats["ingest_errors"] += 1

    # ------------------------------------------------------------------ introspection
    def metrics(self) -> dict:
        r = self.stats["renders"] or 1
        return {"t": round(self.now(), 2), "signals": len(self.mind.signals), "queue_depth": len(self.queue),
                **{k: v for k, v in self.stats.items() if k != "render_ms_total"},
                "render_ms_mean": round(self.stats["render_ms_total"] / r, 3),
                "quarantined": dict(self.quarantined), "surfaces": len(self.surfaces), "rss_mb": kufre_rss_mb(),
                "senses": self.mind.senses()}

    def metrics_json(self) -> str:
        return json.dumps(self.metrics(), default=str)
