import math
import random
import xml.etree.ElementTree as ET

import pytest

from sufd import Mind, SelfProbe, Signal, choose_lens, render_svg
from sufd.lens import Axis, decimate_minmax, nice_ticks
from sufd.sim import make_sources


def feed(sig, fn, seconds, hz):
    n = int(seconds * hz)
    for i in range(n):
        t = i / hz
        sig.push(t, fn(t))
    return sig


# --------------------------------------------------------------- envelope
def test_smooth_slow_scalar_is_described_as_such():
    rnd = random.Random(1)
    s = feed(Signal("x"), lambda t: 22 + 0.02 * t + rnd.gauss(0, 0.03), 120, 1)
    e = s.env
    assert e.kind == "scalar"
    assert e.r1 > 0.9
    assert e.trend == "rising"
    assert "rising" in e.describe()
    assert any(c[0].startswith("temperature") for c in e.candidates())


def test_period_is_recovered():
    rnd = random.Random(2)
    s = feed(Signal("mic"), lambda t: math.sin(2 * math.pi * t / 2.5) + rnd.gauss(0, 0.05), 60, 10)
    assert s.env.period == pytest.approx(2.5, abs=0.2)


def test_binary_and_categorical_kinds():
    b = feed(Signal("door"), lambda t: int(t) % 20 < 10, 80, 1)       # bools
    assert b.env.kind == "binary" and b.env.toggles >= 6
    c = feed(Signal("mode"), lambda t: ("a", "b", "c")[int(t // 10) % 3], 80, 1)
    assert c.env.kind == "categorical"
    n = feed(Signal("nb"), lambda t: float(int(t) % 20 < 10), 80, 1)   # numeric 0/1
    assert n.env.kind == "binary"


def test_vector_kind():
    s = feed(Signal("imu"), lambda t: (math.cos(t), math.sin(t), 9.8), 30, 10)
    assert s.env.kind == "vector" and s.env.dims == 3
    assert len(s.env.component_range) == 3


def test_surprise_spikes_on_a_jump():
    rnd = random.Random(3)
    s = Signal("x")
    for i in range(100):
        s.push(i, 20 + rnd.gauss(0, 0.05))
    quiet = s.env.surprise
    s.push(100, 26.0)
    assert s.env.surprise > 6 > quiet


def test_constant_signal_does_not_crash():
    s = feed(Signal("c"), lambda t: 5.0, 60, 1)
    s.push(60, 9.0)
    assert s.env.surprise <= 99


# ------------------------------------------------------------------- lens
def test_lens_grammar_follows_the_envelope():
    rnd = random.Random(4)
    scalar = feed(Signal("s"), lambda t: 20 + rnd.gauss(0, 0.1), 60, 1)
    assert choose_lens(scalar.env).mark == "strip"
    assert choose_lens(feed(Signal("b"), lambda t: int(t) % 20 < 10, 60, 1).env).mark == "steps"
    assert choose_lens(feed(Signal("c"), lambda t: ("a", "b")[int(t // 7) % 2] + "x" * (int(t // 14) % 2), 60, 1).env).mark == "lanes"
    assert choose_lens(feed(Signal("v"), lambda t: (t, -t), 30, 1).env).mark == "trajectory"
    assert choose_lens(Signal("empty").env).mark == "none"


def test_periodic_window_is_three_periods():
    s = feed(Signal("m"), lambda t: math.sin(2 * math.pi * t / 4.0), 90, 10)
    assert choose_lens(s.env).window_s == pytest.approx(12.0, abs=1.0)


def test_nice_ticks_are_round():
    t = nice_ticks(18.3, 24.9, 5)
    assert t[0] >= 18.3 and t[-1] <= 24.9 + 1e-9
    steps = {round(b - a, 6) for a, b in zip(t, t[1:])}
    assert len(steps) == 1 and steps.pop() in (0.5, 1.0, 2.0, 1.5 - 0.5)


def test_decimation_keeps_a_single_sample_spike():
    pts = [(i, 1.0) for i in range(5000)]
    pts[2500] = (2500, 50.0)
    dec = decimate_minmax(pts, 0, 5000, 100)
    assert len(dec) <= 220
    assert max(v for _, v in dec) == 50.0


def test_axis_widens_now_but_narrows_only_after_evidence():
    a = Axis()
    a.fit(0, 10)
    hi0 = a.hi
    a.fit(0, 40)
    assert a.hi > hi0                       # widened immediately
    wide = a.hi
    for _ in range(Axis.SHRINK_AFTER - 1):
        a.fit(0, 10)
    assert a.hi == wide                     # not yet
    a.fit(0, 10)
    assert a.hi < wide                      # now


# ----------------------------------------------------------------- render
def run_demo(until, confirm_at=None, mind=None):
    mind = mind or Mind(SelfProbe(clock=iter(range(10**6)).__next__, cpu=lambda: 0.0))
    src = make_sources()
    next_at = {k: v[0] for k, v in src.items()}
    t, next_self = 0.0, 0.0
    confirmed = False
    while t <= until:
        for k, (start, period, fn, hint) in src.items():
            if t >= next_at[k]:
                mind.ingest(k, round(t, 3), fn(t), hint)
                next_at[k] = t + period
        if t >= next_self:
            mind.tick_self(round(t, 3))
            next_self = t + 1.0
        if confirm_at is not None and not confirmed and t >= confirm_at:
            mind.confirm("esp32.adc0", "temperature sensor", t)
            confirmed = True
        t = round(t + 0.1, 3)
    return mind


@pytest.fixture(scope="module")
def full():
    return run_demo(290, confirm_at=100)


def test_every_panel_renders_valid_svg(full):
    for name in full.signals:
        p = full.panel(name)
        ET.fromstring(p["svg"])             # well-formed XML
        assert p["mark"] in ("strip", "steps", "lanes", "trajectory", "none")


def test_marks_chosen_for_simulated_sources(full):
    marks = {n: full.lens(n).mark for n in full.signals}
    assert marks["esp32.adc0"] == "strip"
    assert marks["phone.door"] == "steps"
    assert marks["phone.mode"] == "lanes"
    assert marks["imu.accel"] == "trajectory"
    assert marks["mic.level"] == "strip"


# ------------------------------------------------- first contact end to end
def test_new_sense_walks_the_ledger_states():
    m = run_demo(95)
    rec = m.ledger["esp32.adc0"]
    assert rec.state == "described"                     # not yet named: SUFD asks, doesn't presume
    assert rec.label is None
    assert any("what is this" in text for _, text in m.events)
    assert any(c[0].startswith("temperature") for c in rec.candidates)
    m.confirm("esp32.adc0", "temperature sensor", 96)
    assert rec.state == "in_use"
    assert any("thermal safety" in u for u in rec.uses)
    assert any("learned" in u for u in rec.uses)


def test_announced_hint_skips_the_question():
    m = Mind(SelfProbe(clock=iter(range(10**6)).__next__, cpu=lambda: 0.0))
    for i in range(60):
        m.ingest("esp32.t", float(i), 22 + 0.01 * i, hint="temperature (C)")
    assert m.ledger["esp32.t"].label_source == "announced"
    assert m.ledger["esp32.t"].state == "in_use"
    assert not any("what is this" in text for _, text in m.events)


def test_watch_flags_the_heater_and_explains_why(full):
    notes = full.followers["esp32.adc0"].follow.notes
    warns = [n for n in notes if n.level == "warn"]
    assert warns and warns[0].t >= 200
    assert "learned" in warns[0].why                     # every alarm carries its reason


def test_no_watch_without_a_label():
    m = run_demo(290)                                    # never confirmed
    notes = m.followers["esp32.adc0"].follow.notes
    assert not [n for n in notes if n.level == "warn"]   # SUFD does not act on an unconfirmed guess
    assert m.ledger["esp32.adc0"].uses == []


def test_pointer_is_answered_from_the_envelope(full):
    txt = full.followers["esp32.adc0"].explain(260.0)
    assert "high" in txt and "σ" in txt


def test_self_signals_flow_through_the_same_pipeline(full):
    for n in ("self.cpu_load", "self.signals", "self.notes"):
        assert n in full.signals and full.signals[n].env.n > 100
        assert full.ledger[n].state in ("described", "named", "in_use")
    assert any(r["name"] == "self.signals" for r in full.senses())


def test_attention_budget_goes_to_the_surprising_signal(full):
    rows = full.attention(20.0)
    assert sum(r[2] for r in rows) == pytest.approx(20.0, abs=1e-6)
    assert all(r[2] >= 0.5 for r in rows)               # nothing is starved to zero
    rates = {r[0]: r[2] for r in rows}
    assert max(rates.values()) > min(rates.values())    # but it is not uniform


def test_pointer_inside_the_plateau_is_judged_against_the_baseline_not_history(full):
    txt = full.followers["esp32.adc0"].explain(250.0)
    assert "confirmed baseline" in txt and "high" in txt and "typical" not in txt


def test_unlabeled_guess_is_revised_as_the_envelope_matures():
    m = run_demo(200)                       # never confirmed
    assert any("revised guess" in text for _, text in m.events if text.startswith("mic.level"))
    assert m.ledger["mic.level"].candidates[0][0].startswith("oscillating")


# ---- regressions found by looking at the rendered page
def test_axis_always_covers_the_data():
    for lo, hi in [(21.98, 27.01), (0.115, 0.92), (79.6, 80.0), (-3.3, 41.7)]:
        a = Axis()
        a.fit(lo, hi)
        assert a.lo <= lo and a.hi >= hi, (lo, hi, a.lo, a.hi)


def test_time_axis_puts_now_on_the_right():
    s = feed(Signal("x"), lambda t: 20 + math.sin(t / 5), 60, 1)
    svg = render_svg(s, choose_lens(s.env))
    root = ET.fromstring(svg)
    ns = "{http://www.w3.org/2000/svg}"
    xs = {t.text: float(t.get("x")) for t in root.iter(ns + "text") if t.text and (t.text == "now" or t.text.endswith("s"))}
    assert xs["now"] == max(xs.values())


def test_a_guess_does_not_flap_once_the_period_is_seen():
    m = run_demo(120)
    tops = [text for _, text in m.events if text.startswith("mic.level") and "revised" in text]
    assert len(tops) <= 1


def test_heater_is_noticed_within_a_few_samples():
    m = run_demo(290, confirm_at=100)
    warn = next(n for n in m.followers["esp32.adc0"].follow.notes if n.level == "warn")
    assert 200 <= warn.t <= 215


def test_period_survives_irregular_sampling():
    rnd = random.Random(5)
    s, t = Signal("j"), 0.0
    while t < 60:
        s.push(t, math.sin(2 * math.pi * t / 2.5))
        t += 0.1 if rnd.random() < 0.8 else 0.2          # dropped ticks, like a real radio
    assert s.env.period == pytest.approx(2.5, abs=0.25)


def test_no_trend_notes_on_oscillating_or_vector_signals(full):
    for name in ("mic.level", "imu.accel"):
        assert not [n for n in full.followers[name].follow.notes if "started" in n.text], name
