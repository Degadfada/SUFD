"""Hostile-timing regressions found while building the M1 skeleton (a burst could freeze the daemon)."""
import time

from sufd.idea.envelope import WINDOW, IdeaEnvelope, _resample
from sufd.kufre.runtime import KufreRuntime


def test_resample_grid_is_capped_for_microscopic_intervals():
    xs = [0.0] * 100 + [1.0 + k * 1e-6 for k in range(100)]            # a long gap then a burst
    ys = [float(i % 5) for i in range(200)]
    grid, dt_used = _resample(xs, ys, 1e-6)                               # median dt of a burst is ~1 us
    assert len(grid) <= 2 * WINDOW + 2
    assert dt_used > 1e-6                                                 # coarsened so the span fits the cap


def test_resample_is_unchanged_for_regular_data():
    xs = [i * 0.5 for i in range(100)]
    ys = [float(i) for i in range(100)]
    grid, dt_used = _resample(xs, ys, 0.5)
    assert dt_used == 0.5 and len(grid) == 100 and grid[10] == 10.0


def test_bursty_arrivals_do_not_blow_up_the_estimator():
    env = IdeaEnvelope()
    buf, t = [], 0.0
    t0 = time.perf_counter()
    for burst in range(20):
        t += 1.0                                                           # one second between bursts
        for k in range(200):                                              # 200 samples land within 1 ms
            t_k = t + k * 5e-6
            buf.append((t_k, float((burst * 200 + k) % 97)))
            env.update(t_k, buf[-1][1], buf[-256:])
    assert time.perf_counter() - t0 < 5.0                                  # was: tens of seconds, then a hang


def test_a_flood_cannot_monopolise_the_loop_in_one_drain():
    rt = KufreRuntime()
    for k in range(5000):
        rt.submit("flood.x", float(k % 97))
    t0 = time.perf_counter()
    n = rt.drain(limit=5000, budget_s=0.006)
    spent = time.perf_counter() - t0
    assert 0 < n < 5000 and len(rt.queue) == 5000 - n                     # sliced: the rest waits, bounded
    assert spent < 0.5                                                     # one slice never holds the loop long


def test_a_pathologically_slow_signal_earns_strikes_and_is_quarantined():
    rt = KufreRuntime()
    rt.slow_ingest_s = 0.0                                                 # every ingest counts as slow
    for k in range(10):
        rt.submit("slow.s", 1.0 + k)
        rt.submit("fine.f", 1.0 + k)
        rt.drain(budget_s=1.0)
        rt.slow["fine.f"] = 0                                              # only slow.s keeps its strikes
    assert "slow.s" in rt.quarantined and "too slow" in rt.quarantined["slow.s"]
    assert rt.stats["slow_ingests"] >= 3


def test_a_sender_cannot_grow_memory_by_inventing_signal_names():
    rt = KufreRuntime(max_signals=20)
    for k in range(500):
        rt.submit(f"junk.{k}", 1.0)
        rt.drain(budget_s=1.0)
    assert len(rt.mind.signals) == 20 and rt.stats["refused_new_signals"] >= 400


def test_ring_capacity_bounds_each_signal_and_the_narration_is_bounded():
    rt = KufreRuntime(ring_capacity=64)
    for k in range(500):
        rt.submit("a.b", 20.0 + 0.01 * (k % 7))
        rt.drain(budget_s=1.0)
    assert len(rt.mind.signals["a.b"].buf) == 64
    assert rt.mind.events.maxlen == 2000
