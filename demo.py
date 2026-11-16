"""Run the first-contact story with simulated sources and write out/demo.html.

    python demo.py

t=0    phone senses, a mic, an IMU and SUFD's own vitals are already flowing
t=60   an unlabeled ESP32 channel appears (esp32.adc0). SUFD has never seen it.
t=~92  SUFD has described it and asks what it is, offering reasoned candidates
t=100  the human confirms "temperature sensor"; SUFD binds a learned watch
t=200  a heater turns on; SUFD flags it, with the reason, before the human asks
"""
from __future__ import annotations

import sys
from html import escape
from pathlib import Path

from sufd import Mind
from sufd.sim import make_sources

SNAPSHOTS = [(75, "t=75 s — first sight"), (99, "t=99 s — described, waiting for the human"),
             (150, "t=150 s — named and in use"), (290, "t=290 s — after the heater came on")]
SENSE = "esp32.adc0"


def run() -> dict:
    mind = Mind()
    src = make_sources()
    next_at = {k: v[0] for k, v in src.items()}
    snaps, t, next_self, confirmed = {}, 0.0, 0.0, False
    pending = [s[0] for s in SNAPSHOTS]
    while t <= 290:
        for k, (_, period, fn, hint) in src.items():
            if t >= next_at[k]:
                mind.ingest(k, round(t, 3), fn(t), hint)
                next_at[k] = t + period
        if t >= next_self:
            mind.tick_self(round(t, 3))
            next_self = t + 1.0
        if not confirmed and t >= 100:
            mind.confirm(SENSE, "temperature sensor", t)
            confirmed = True
        if pending and t >= pending[0] and SENSE in mind.signals:
            snaps[pending.pop(0)] = mind.panel(SENSE, now=t)
        t = round(t + 0.1, 3)
    return {"mind": mind, "snaps": snaps}


CSS = """
:root{--bg:#fafaf7;--card:#fff;--ink:#1c1c1a;--mut:#6b6b64;--rule:#e4e2da;--sv-line:#2563eb;--sv-now:#d9650f;
--sv-hum:#7c3aed;--sv-warn:#c62828;--sv-grid:#0002;--sv-ink:#6b6b64}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#141412;--card:#1c1c1a;--ink:#ecebe5;--mut:#9a998f;
--rule:#2f2e2a;--sv-line:#6ea0ff;--sv-now:#ff9a4d;--sv-hum:#b79bff;--sv-warn:#ff6b6b;--sv-grid:#fff3;--sv-ink:#9a998f}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,sans-serif}
main{max-width:1040px;margin:0 auto;padding:32px 16px 64px}
h1{font-size:28px;margin:0 0 4px}h2{font-size:18px;margin:36px 0 10px}
.lede{color:var(--mut);max-width:62ch;margin:0 0 8px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,440px),1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--rule);border-radius:10px;padding:12px 14px}
.card h3{margin:0;font-size:14px;font-weight:600}.sub{color:var(--mut);font-size:12.5px;margin:2px 0 6px}
.why{color:var(--mut);font-size:12px;margin-top:4px}
.tag{display:inline-block;font-size:11px;border:1px solid var(--rule);border-radius:99px;padding:0 8px;margin-left:6px;color:var(--mut)}
.note{font-size:12.5px;margin:2px 0}.note b{color:var(--sv-now)}.note.warn b{color:var(--sv-warn)}
ol.log{margin:0;padding-left:0;list-style:none;font-size:13.5px}
ol.log li{padding:5px 0;border-bottom:1px solid var(--rule);display:flex;gap:12px}
ol.log time{color:var(--mut);min-width:54px;font-variant-numeric:tabular-nums}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--rule);vertical-align:top}
th{color:var(--mut);font-weight:600}.bar{height:6px;border-radius:3px;background:var(--sv-now)}
@media (max-width:520px){table{font-size:12px}}
"""


def card(p: dict, title: str = "") -> str:
    notes = "".join(f'<div class="note {n.level}"><b>t={n.t:.0f}</b> {escape(n.text)} '
                    f'<span class="why">— {escape(n.why)}</span></div>' for n in p["notes"])
    label = f'<span class="tag">{escape(p["label"])}</span>' if p["label"] else ""
    return (f'<div class="card"><h3>{escape(title or p["name"])}{label}<span class="tag">{p["state"]}</span></h3>'
            f'<div class="sub">{escape(p["summary"])}</div>{p["svg"]}'
            f'<div class="why">lens: {escape(p["mark"])} — {escape(p["reason"])}</div>{notes}</div>')


def build(out: Path) -> None:
    r = run()
    mind: Mind = r["mind"]
    # the human points at the heater event on the live heat panel
    final = {n: mind.panel(n, now=290, human_t=(250.0 if n == SENSE else None)) for n in mind.signals}

    log = "".join(f"<li><time>t={t:.0f}</time><span>{escape(x)}</span></li>"
                  for t, x in mind.events if not x.startswith("self."))
    snaps = "".join(card(p, title) for (_, title), p in zip(SNAPSHOTS, (r["snaps"][k] for k, _ in SNAPSHOTS)))
    live = "".join(card(final[n]) for n in final if not n.startswith("self.") and n != SENSE)
    selfs = "".join(card(final[n]) for n in final if n.startswith("self."))
    point = final[SENSE]["pointer"]
    rows = mind.attention(20.0)
    top = max(r_[2] for r_ in rows) or 1
    att = "".join(f"<tr><td>{escape(n)}</td><td><div class='bar' style='width:{h / top * 100:.0f}%'></div></td>"
                  f"<td>{h:.1f} Hz</td></tr>" for n, _, h in rows)
    led = "".join(f"<tr><td>{escape(s['name'])}</td><td>{s['state']}</td><td>{escape(str(s['label'] or '—'))}"
                  f"{' ('+s['by']+')' if s['by'] else ''}</td><td>{escape('; '.join(s['uses']) or '—')}</td></tr>"
                  for s in mind.senses() if not s["name"].startswith("self."))

    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>SUFD first contact</title>
<style>{CSS}</style></head><body><main>
<h1>SUFD — first contact</h1>
<p class="lede">An unlabeled ESP32 channel joins at t=60. No app exists for it. SUFD reads it,
describes what it saw, asks once, then puts it to use and shows the human what it sees.</p>

<h2>What SUFD narrated</h2><ol class="log">{log}</ol>

<h2>One sense, four moments</h2>
<p class="lede">Orange triangles are SUFD's notes (hover for the reason); the orange line is SUFD's “now”;
the dashed violet line is where the human pointed.</p>
<div class="grid">{snaps}</div>
<div class="card" style="margin-top:14px"><h3>The human points at t=250 on the heat sensor</h3>
<div class="sub">answered from the envelope, no language model</div><div>{escape(point or '')}</div></div>

<h2>The same pipeline reads everything else</h2><div class="grid">{live}</div>

<h2>…including SUFD itself</h2><div class="grid">{selfs}</div>

<h2>What can you sense?</h2>
<p class="lede">Answered from SUFD's own ledger.</p>
<table><tr><th>signal</th><th>state</th><th>label</th><th>uses</th></tr>{led}</table>

<h2>Where the human's attention budget (20 Hz) goes</h2>
<table><tr><th>signal</th><th>share</th><th>render rate</th></tr>{att}</table>
</main></body></html>"""
    out.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    target = Path(__file__).parent / "out" / "demo.html"
    target.parent.mkdir(exist_ok=True)
    build(target)
    print(f"wrote {target}")
    sys.exit(0)
