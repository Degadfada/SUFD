"""Render a Lens over a Signal as an SVG string. Pure strings, no dependencies.

The right edge is always SUFD's 'now' cursor. The human's pointer (if any) is a
dashed cursor with a readout. SUFD's notes are triangles; each carries its text as
a <title>, so hovering shows what SUFD noticed and why.
"""
from __future__ import annotations

import math
from html import escape
from typing import List, Optional, Tuple

from .follow import Follow
from .lens import Lens, decimate_minmax, nice_ticks
from .signal import Signal

STYLE = """<style>
.bg{fill:var(--sv-bg,transparent)} .ax{stroke:var(--sv-grid,#8884);stroke-width:1}
.tx{fill:var(--sv-ink,#555);font:10px system-ui,sans-serif}
.ln{fill:none;stroke:var(--sv-line,#2563eb);stroke-width:1.6;stroke-linejoin:round}
.fl{fill:var(--sv-line,#2563eb);opacity:.18}
.now{stroke:var(--sv-now,#e0701a);stroke-width:1.5}
.nowt{fill:var(--sv-now,#e0701a);font:600 10px system-ui,sans-serif}
.hum{stroke:var(--sv-hum,#7c3aed);stroke-width:1.2;stroke-dasharray:4 3}
.humt{fill:var(--sv-hum,#7c3aed);font:600 10px system-ui,sans-serif}
.nt{fill:var(--sv-now,#e0701a)} .nt.warn{fill:var(--sv-warn,#d1242f)}
</style>"""

ML, MR, MT, MB = 46, 14, 10, 20


def _fmt(v: float) -> str:
    return f"{v:.4g}"


def _frame(w: int, h: int, body: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" '
            f'role="img" preserveAspectRatio="xMidYMid meet">{STYLE}{body}</svg>')


def _time_axis(w: int, h: int, t0: float, t1: float) -> str:
    plot_w = w - ML - MR
    span = t1 - t0
    out = [f'<line class="ax" x1="{ML}" x2="{w - MR}" y1="{h - MB}" y2="{h - MB}"/>']
    for age in nice_ticks(0, span, 5):            # age = seconds before now
        x = ML + plot_w * (1 - age / span)
        out.append(f'<text class="tx" x="{x:.1f}" y="{h - 6}" text-anchor="{"end" if age == 0 else "middle"}">'
                   f'{"now" if age == 0 else "-" + _fmt(age) + "s"}</text>')
    return "".join(out)


def _overlays(w: int, h: int, sig: Signal, follow: Optional[Follow], t0: float, t1: float,
              xy) -> str:
    out = []
    plot_w = w - ML - MR
    if follow:
        for n in follow.notes:
            if t0 <= n.t <= t1:
                x = ML + plot_w * (n.t - t0) / (t1 - t0)
                cls = "nt warn" if n.level == "warn" else "nt"
                out.append(f'<path class="{cls}" d="M{x - 4:.1f} {MT} L{x + 4:.1f} {MT} L{x:.1f} {MT + 8}Z">'
                           f'<title>{escape(n.text)} — {escape(n.why)}</title></path>')
        if follow.human_t is not None and t0 <= follow.human_t <= t1:
            x = ML + plot_w * (follow.human_t - t0) / (t1 - t0)
            out.append(f'<line class="hum" x1="{x:.1f}" x2="{x:.1f}" y1="{MT}" y2="{h - MB}"/>')
            near = min(sig.buf, key=lambda s: abs(s[0] - follow.human_t))
            val = near[1] if not isinstance(near[1], float) else _fmt(near[1])
            out.append(f'<text class="humt" x="{x + 4:.1f}" y="{MT + 20}">{escape(str(val))}</text>')
    out.append(f'<line class="now" x1="{w - MR}" x2="{w - MR}" y1="{MT}" y2="{h - MB}"/>')
    return "".join(out)


def render_svg(sig: Signal, lens: Lens, follow: Optional[Follow] = None,
               now: Optional[float] = None, width: int = 560, height: int = 170) -> str:
    if lens.mark == "none" or not sig.buf:
        return _frame(width, 40, f'<text class="tx" x="8" y="24">observing… ({len(sig)} samples)</text>')
    t1 = sig.buf[-1][0] if now is None else now
    t0 = t1 - lens.window_s
    data = [s for s in sig.buf if t0 <= s[0] <= t1]
    if not data:
        return _frame(width, 40, '<text class="tx" x="8" y="24">no recent samples</text>')
    if lens.mark == "strip":
        return _strip(sig, lens, follow, data, t0, t1, width, height)
    if lens.mark == "steps":
        return _steps(sig, lens, follow, data, t0, t1, width, height)
    if lens.mark == "lanes":
        return _lanes(sig, lens, follow, data, t0, t1, width, height)
    if lens.mark == "trajectory":
        return _trajectory(sig, lens, data, width, 220)
    return _frame(width, 40, f'<text class="tx" x="8" y="24">no encoding for {escape(lens.mark)}</text>')


def _strip(sig, lens, follow, data, t0, t1, w, h) -> str:
    plot_w, plot_h = w - ML - MR, h - MT - MB
    pts = [(t, float(v)) for t, v in data]
    ys = [p[1] for p in pts]
    env = sig.env
    lo, hi = min(ys), max(ys)
    lens.axis.fit(lo, hi)
    a = lens.axis
    f = (lambda y: math.log10(max(y, 1e-12))) if a.log else (lambda y: y)
    flo, fhi = f(max(a.lo, 1e-12) if a.log else a.lo), f(a.hi)
    span = (fhi - flo) or 1.0
    yx = lambda y: MT + plot_h * (1 - (f(y) - flo) / span)
    xx = lambda t: ML + plot_w * (t - t0) / (t1 - t0)

    body = ['<rect class="bg" width="100%" height="100%"/>']
    for tk in nice_ticks(a.lo, a.hi, 5):
        if a.log and tk <= 0:
            continue
        y = yx(tk)
        body.append(f'<line class="ax" x1="{ML}" x2="{w - MR}" y1="{y:.1f}" y2="{y:.1f}"/>'
                    f'<text class="tx" x="{ML - 5}" y="{y + 3:.1f}" text-anchor="end">{_fmt(tk)}</text>')
    dec = decimate_minmax(pts, t0, t1, plot_w)
    path = " ".join(f"{xx(t):.1f},{yx(y):.1f}" for t, y in dec)
    body.append(f'<polyline class="ln" points="{path}"/>')
    body.append(_time_axis(w, h, t0, t1))
    body.append(_overlays(w, h, sig, follow, t0, t1, None))
    last = pts[-1][1]
    body.append(f'<text class="nowt" x="{w - MR - 4}" y="{max(yx(last) - 6, MT + 10):.1f}" text-anchor="end">{_fmt(last)}</text>')
    return _frame(w, h, "".join(body))


def _steps(sig, lens, follow, data, t0, t1, w, h) -> str:
    h = min(h, 110)
    plot_w, plot_h = w - ML - MR, h - MT - MB
    xx = lambda t: ML + plot_w * (t - t0) / (t1 - t0)
    lv = lambda v: MT + plot_h * (0.15 if float(v) else 0.85)
    d, prev = [], None
    for t, v in data:
        y = lv(v)
        if prev is not None and prev != y:
            d.append(f"{xx(t):.1f},{prev:.1f}")
        d.append(f"{xx(t):.1f},{y:.1f}")
        prev = y
    d.append(f"{w - MR},{prev:.1f}")
    body = ['<rect class="bg" width="100%" height="100%"/>',
            f'<text class="tx" x="{ML - 5}" y="{MT + plot_h * 0.15 + 3:.1f}" text-anchor="end">high</text>',
            f'<text class="tx" x="{ML - 5}" y="{MT + plot_h * 0.85 + 3:.1f}" text-anchor="end">low</text>',
            f'<polyline class="ln" points="{" ".join(d)}"/>',
            _time_axis(w, h, t0, t1), _overlays(w, h, sig, follow, t0, t1, None)]
    return _frame(w, h, "".join(body))


def _lanes(sig, lens, follow, data, t0, t1, w, h) -> str:
    cats = lens.categories or sorted({v for _, v in data}, key=str)
    lane_h = 22
    hh = MT + lane_h * len(cats) + MB
    plot_w = w - ML - MR
    xx = lambda t: ML + plot_w * (t - t0) / (t1 - t0)
    body = ['<rect class="bg" width="100%" height="100%"/>']
    for i, c in enumerate(cats):
        y = MT + i * lane_h
        body.append(f'<line class="ax" x1="{ML}" x2="{w - MR}" y1="{y + lane_h:.1f}" y2="{y + lane_h:.1f}"/>'
                    f'<text class="tx" x="{ML - 5}" y="{y + lane_h / 2 + 3:.1f}" text-anchor="end">{escape(str(c))}</text>')
    runs: List[Tuple[object, float, float]] = []
    for t, v in data:
        if runs and runs[-1][0] == v:
            runs[-1] = (v, runs[-1][1], t)
        else:
            if runs:
                runs[-1] = (runs[-1][0], runs[-1][1], t)
            runs.append((v, t, t))
    runs[-1] = (runs[-1][0], runs[-1][1], t1)
    for v, a, b in runs:
        if v in cats:
            y = MT + cats.index(v) * lane_h + 4
            body.append(f'<rect class="fl" style="opacity:.55" x="{xx(a):.1f}" y="{y:.1f}" '
                        f'width="{max(1.5, xx(b) - xx(a)):.1f}" height="{lane_h - 8}" rx="2"/>')
    body.append(_time_axis(w, hh, t0, t1))
    body.append(_overlays(w, hh, sig, follow, t0, t1, None))
    return _frame(w, hh, "".join(body))


def _trajectory(sig, lens, data, w, h) -> str:
    comps = sig.env.component_range
    if len(comps) < 2:
        return _frame(w, 40, '<text class="tx" x="8" y="24">observing…</text>')
    (x0, x1), (y0, y1) = comps[0], comps[1]
    side = min(w, h) - 24
    sx = lambda x: 12 + side * (x - x0) / ((x1 - x0) or 1)
    sy = lambda y: 12 + side * (1 - (y - y0) / ((y1 - y0) or 1))
    tail = data[-60:]
    body = ['<rect class="bg" width="100%" height="100%"/>']
    for i, ((_, a), (_, b)) in enumerate(zip(tail, tail[1:])):
        op = 0.08 + 0.92 * (i + 1) / len(tail)
        body.append(f'<line class="ln" style="opacity:{op:.2f}" x1="{sx(a[0]):.1f}" y1="{sy(a[1]):.1f}" '
                    f'x2="{sx(b[0]):.1f}" y2="{sy(b[1]):.1f}"/>')
    cur = tail[-1][1]
    body.append(f'<circle cx="{sx(cur[0]):.1f}" cy="{sy(cur[1]):.1f}" r="4" style="fill:var(--sv-now,#e0701a)"/>')
    body.append(f'<text class="tx" x="{12 + side + 8}" y="24">c0 {_fmt(x0)}…{_fmt(x1)}</text>'
                f'<text class="tx" x="{12 + side + 8}" y="40">c1 {_fmt(y0)}…{_fmt(y1)}</text>')
    return _frame(w, h, "".join(body))
