"""Ground-truth scenario corpus for SUFD (M0).

Every scenario is deterministic for a given seed and carries its truth, so every claim SUFD makes can be scored
instead of asserted. Nothing here imports SUFD: the corpus is independent of the implementation it judges.

Sample formats:
    samples  = [(t, value), ...]                     single signal
    arrivals = [(arrival_t, node_t, value), ...]     timing scenarios (node clock vs SUFD clock)
"""
from __future__ import annotations

import math
import random
import zlib
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

Sample = Tuple[float, object]


@dataclass
class Scenario:
    name: str
    samples: List[Sample]
    truth: Dict[str, object] = field(default_factory=dict)
    other: Optional[List[Sample]] = None          # second signal for pair scenarios
    arrivals: Optional[List[Tuple[float, float, object]]] = None


def _grid(n: int, dt: float, t0: float = 0.0) -> List[float]:
    return [t0 + i * dt for i in range(n)]


# ------------------------------------------------------------------ dynamics
def first_order_step(seed=0, tau=8.0, dt=0.5, n=200, step_at=40, lo=20.0, hi=30.0, noise=0.03):
    r = random.Random(seed)
    a = math.exp(-dt / tau)
    y, out = lo, []
    for i, t in enumerate(_grid(n, dt)):
        target = hi if i >= step_at else lo
        y = target + (y - target) * a
        out.append((t, y + r.gauss(0, noise)))
    return Scenario("first_order_step", out, {"tau": tau, "step_t": step_at * dt, "order": 1})


def underdamped_step(seed=0, zeta=0.2, wn=2.0, dt=0.05, n=600, step_at=100, noise=0.01):
    """Exact discretisation of a 2nd-order system's step response (AR(2) with complex poles)."""
    r = random.Random(seed)
    rr = math.exp(-zeta * wn * dt)
    wd = wn * math.sqrt(1 - zeta ** 2)
    a1, a2 = 2 * rr * math.cos(wd * dt), -rr * rr
    y1 = y2 = 0.0
    out = []
    for i, t in enumerate(_grid(n, dt)):
        u = 1.0 if i >= step_at else 0.0
        y = a1 * y1 + a2 * y2 + (1 - a1 - a2) * u
        y2, y1 = y1, y
        out.append((t, y + r.gauss(0, noise)))
    return Scenario("underdamped_step", out, {"zeta": zeta, "wn": wn, "step_t": step_at * dt, "order": 2})


def ramp(seed=0, n=600, dt=1.0, slope=0.02, noise=0.03):
    r = random.Random(seed)
    return Scenario("ramp", [(t, 20 + slope * t + r.gauss(0, noise)) for t in _grid(n, dt)],
                    {"events": [], "slope": slope})


def sine(seed=0, n=1200, dt=0.1, period=2.5, amp=1.0, noise=0.05, jitter=0.0):
    r = random.Random(seed)
    out, t = [], 0.0
    for _ in range(n):
        out.append((t, amp * math.sin(2 * math.pi * t / period) + r.gauss(0, noise)))
        t += dt if r.random() >= jitter else 2 * dt              # jitter = probability of a dropped tick
    return Scenario("sine_jitter" if jitter else "sine", out, {"period": period, "events": []})


def tone_above_nyquist(seed=0, n=600, dt=0.1, f=7.3, noise=0.02):
    """fs = 10 Hz, tone at 7.3 Hz aliases to 2.7 Hz. Truth: alias-suspect."""
    r = random.Random(seed)
    return Scenario("alias_tone", [(t, math.sin(2 * math.pi * f * t) + r.gauss(0, noise)) for t in _grid(n, dt)],
                    {"alias": True, "true_f": f, "apparent_f": abs(f - 1 / dt)})


# ------------------------------------------------------------------ noise
def quantised_blip(seed=0, n=400, dt=1.0, q=0.01, blip_at=300, lsb_flicker=0.0):
    """The hazard: a perfectly flat quantised trace (a real sensor in a stable room) then ONE 1-LSB blip.
    A 1-LSB change is the smallest event the sensor can report; it must not read as a 99x 'jump'."""
    r = random.Random(seed)
    out = []
    for i, t in enumerate(_grid(n, dt)):
        v = 21.5 + (q if i == blip_at else 0.0) + (q if r.random() < lsb_flicker else 0.0)
        out.append((t, round(round(v / q) * q, 6)))
    return Scenario("quantised_blip", out, {"q": q, "blip_t": blip_at * dt, "blip_lsb": 1, "events": []})


def gaussian(seed=0, n=5000, dt=1.0, sigma=1.0):
    r = random.Random(seed)
    return Scenario("gaussian", [(t, r.gauss(0, sigma)) for t in _grid(n, dt)], {"events": [], "sigma": sigma})


def heavy_tail(seed=0, n=5000, dt=1.0, nu=3):
    """Student-t with nu degrees of freedom (finite variance only for nu > 2)."""
    r = random.Random(seed)
    def t_draw():
        z = r.gauss(0, 1)
        chi2 = sum(r.gauss(0, 1) ** 2 for _ in range(nu))
        return z / math.sqrt(chi2 / nu)
    return Scenario("heavy_tail", [(t, t_draw()) for t in _grid(n, dt)], {"events": [], "nu": nu})


def flicker(seed=0, n=16384, dt=1.0, octaves=14):
    """1/f noise: sum of AR(1) processes with octave-spaced corner frequencies and equal variance per octave."""
    r = random.Random(seed)
    phis = [1 - 2.0 ** -(k + 1) for k in range(octaves)]
    gains = [math.sqrt(1 - p * p) for p in phis]
    state = [r.gauss(0, 1) for _ in phis]
    out = []
    for t in _grid(n, dt):
        for k, p in enumerate(phis):
            state[k] = p * state[k] + gains[k] * r.gauss(0, 1)
        out.append((t, sum(state) / math.sqrt(octaves)))
    return Scenario("flicker", out, {"events": [], "beta": 1.0})


def white(seed=0, n=2000, dt=1.0):
    s = gaussian(seed, n, dt)
    s.name, s.truth = "white", {"events": [], "unmodelled": True}
    return s


# ------------------------------------------------------------------ change
def mean_shift(seed=0, n=2000, dt=1.0, at=1000, delta=1.0):
    r = random.Random(seed)
    return Scenario("mean_shift", [(t, (delta if i >= at else 0.0) + r.gauss(0, 1)) for i, t in enumerate(_grid(n, dt))],
                    {"events": [at * dt], "delta_sigma": delta})


def ar1_mean_shift(seed=0, n=3000, dt=1.0, phi=0.9, at=1500, delta=1.0):
    """AR(1) with unit marginal variance; the mean jumps by delta (marginal-σ units) at `at`."""
    r = random.Random(seed)
    g = math.sqrt(1 - phi * phi)
    x, out = 0.0, []
    for i, t in enumerate(_grid(n, dt)):
        x = phi * x + g * r.gauss(0, 1)
        out.append((t, x + (delta if i >= at else 0.0)))
    return Scenario("ar1_mean_shift", out, {"events": [at * dt], "phi": phi, "delta_sigma": delta})


def chatter_near_threshold(seed=0, n=1600, dt=1.0, level=20.0, noise=0.05, calib=300, peak=1.5):
    """Calm calibration, then a slow rise to `peak`, a long hold, and a slow fall. Wherever the learned threshold
    sits inside (level, level+peak), the noisy trace straddles it for a long time on the way up and on the way
    down. Truth: exactly ONE alarm episode; every extra activation is chatter."""
    r = random.Random(seed)
    out = []
    up0, up1, dn0, dn1 = calib, calib + 400, calib + 800, calib + 1200
    for i, t in enumerate(_grid(n, dt)):
        if i < up0:
            f = 0.0
        elif i < up1:
            f = (i - up0) / (up1 - up0)
        elif i < dn0:
            f = 1.0
        elif i < dn1:
            f = 1 - (i - dn0) / (dn1 - dn0)
        else:
            f = 0.0
        out.append((t, level + peak * f + r.gauss(0, noise)))
    return Scenario("chatter", out, {"events": [up0 * dt], "true_episodes": 1, "calib": calib})


# ------------------------------------------------------------------ data quality
def stuck(seed=0, n=600, dt=1.0, at=300):
    r = random.Random(seed)
    out, last = [], 20.0
    for i, t in enumerate(_grid(n, dt)):
        if i < at:
            last = 20 + 0.5 * math.sin(t / 30) + r.gauss(0, 0.05)
        out.append((t, round(last, 3)))
    return Scenario("stuck", out, {"stuck_from": at * dt})


def clipped(seed=0, n=800, dt=1.0, rail=4095.0):
    r = random.Random(seed)
    out = [(t, min(rail, 2000 + 1500 * math.sin(t / 40) + 900 * (t > 400) + r.gauss(0, 20))) for t in _grid(n, dt)]
    return Scenario("clipped", out, {"rail": rail})


def gaps(seed=0, n=600, dt=1.0):
    r = random.Random(seed)
    out = [(t, 20 + r.gauss(0, 0.1)) for t in _grid(n, dt) if not (200 <= t < 260 or 400 <= t < 405)]
    return Scenario("gaps", out, {"gaps": [(200.0, 260.0), (400.0, 405.0)]})


def hostile(seed=0):
    """Inputs that must never crash SUFD."""
    nan, inf = float("nan"), float("inf")
    vals = [(0.0, 1.0), (1.0, nan), (2.0, inf), (3.0, -inf), (2.5, 2.0), (2.5, 2.0), (4.0, 1e300),
            (5.0, -1e300), (6.0, True), (7.0, "on"), (8.0, (1.0, 2.0)), (9.0, None), (10.0, 3.0)]
    vals += [(11.0 + i, float(i % 3)) for i in range(60)]
    return Scenario("hostile", vals, {"must_not_crash": True})


# ------------------------------------------------------------------ discrete
def binary_dwell(seed=0, n=1200, dt=1.0, mean_dwell=60.0):
    r = random.Random(seed)
    out, state, next_flip = [], False, r.expovariate(1 / mean_dwell)
    for t in _grid(n, dt):
        if t >= next_flip:
            state, next_flip = not state, t + r.expovariate(1 / mean_dwell)
        out.append((t, state))
    return Scenario("binary_dwell", out, {"mean_dwell": mean_dwell})


# ------------------------------------------------------------------ pairs
def lead_lag(seed=0, n=3000, dt=1.0, lag=5, coupling=0.8):
    r = random.Random(seed)
    a = [0.0]
    for _ in range(n + lag):
        a.append(0.7 * a[-1] + r.gauss(0, 1))
    b = [coupling * a[i - lag] + 0.6 * r.gauss(0, 1) for i in range(lag, n + lag)]
    ts = _grid(n, dt)
    return Scenario("lead_lag", list(zip(ts, a[lag:lag + n])), {"edge": "A->B", "lag": lag}, other=list(zip(ts, b)))


def common_cause(seed=0, n=3000, dt=1.0):
    r = random.Random(seed)
    c, a, b = 0.0, [], []
    for _ in range(n):
        c = 0.95 * c + r.gauss(0, 1)
        a.append(c + r.gauss(0, 0.8))
        b.append(c + r.gauss(0, 0.8))
    ts = _grid(n, dt)
    return Scenario("common_cause", list(zip(ts, a)), {"edge": "none-causal", "shared": True}, other=list(zip(ts, b)))


def independent(seed=0, n=3000, dt=1.0):
    r = random.Random(seed)
    ts = _grid(n, dt)
    return Scenario("independent", [(t, r.gauss(0, 1)) for t in ts], {"edge": "none"},
                    other=[(t, r.gauss(0, 1)) for t in ts])


# ------------------------------------------------------------------ timing / links
def link_vs_sensor_jitter(seed=0, n=2000, period=1.0, sensor_jitter=0.002, link_rate=0.05):
    """Node samples at `period` with tiny sensor jitter; the link adds an M/M/1-like exponential queue delay."""
    r = random.Random(seed)
    arr = []
    for i in range(n):
        node_t = i * period + r.gauss(0, sensor_jitter)
        arr.append((node_t + 0.004 + r.expovariate(1 / link_rate), node_t, 20 + r.gauss(0, 0.1)))
    arr.sort()
    return Scenario("link_jitter", [(a, v) for a, _, v in arr],
                    {"sensor_jitter": sensor_jitter, "link_mean_excess": link_rate, "floor": 0.004}, arrivals=arr)


def clock_skew(seed=0, n=3000, period=1.0, skew_ppm=80.0, offset=12.5):
    r = random.Random(seed)
    arr = []
    for i in range(n):
        true_t = i * period
        node_t = offset + true_t * (1 + skew_ppm * 1e-6)
        arr.append((true_t + 0.003 + r.expovariate(1 / 0.01), node_t, r.gauss(0, 1)))
    return Scenario("clock_skew", [(a, v) for a, _, v in arr], {"skew_ppm": skew_ppm, "offset": offset},
                    arrivals=arr)


def ble_quantised(seed=0, n=1000, period=0.1, conn_interval=0.0375):
    """Sensor samples every 100 ms; BLE delivers only at connection events every 37.5 ms."""
    r = random.Random(seed)
    arr = []
    for i in range(n):
        node_t = i * period
        k = math.ceil(node_t / conn_interval)
        arr.append((k * conn_interval + 0.001 * r.random(), node_t, r.gauss(0, 1)))
    return Scenario("ble_quantised", [(a, v) for a, _, v in arr], {"conn_interval": conn_interval}, arrivals=arr)


def mqtt_duplicates(seed=0, n=600, period=1.0, dup_p=0.03):
    r = random.Random(seed)
    arr = []
    for i in range(n):
        node_t, v = i * period, 20 + r.gauss(0, 0.1)
        a = node_t + 0.01 + r.expovariate(1 / 0.01)
        arr.append((a, node_t, v))
        if r.random() < dup_p:                                    # redelivered after a reconnect
            arr.append((a + 2.0 + r.random(), node_t, v))
    arr.sort()
    return Scenario("mqtt_dupes", [(a, v) for a, _, v in arr], {"duplicates": sum(1 for _ in arr) - n}, arrivals=arr)


# ------------------------------------------------------------------ thermal
def thermal_step_throttle(seed=0, n=1800, dt=1.0, ta=35.0, p_idle=2.0, p_load=6.5,
                          r1=4.0, c1=6.0, r2=4.0, c2=60.0, load_at=300, throttle_c=80.0):
    """Two-node Foster-like host: die (fast) + sink (slow). The throttle clamps power above 80 °C."""
    r = random.Random(seed)
    t_die, t_sink, out, flags = ta, ta, [], []
    for i, t in enumerate(_grid(n, dt)):
        p = p_load if i >= load_at else p_idle
        throttled = t_die >= throttle_c
        if throttled:
            p = min(p, p_idle + 1.5)
        q12 = (t_die - t_sink) / r1
        t_die += dt * (p - q12) / c1
        t_sink += dt * (q12 - (t_sink - ta) / r2) / c2
        out.append((t, round(t_die + r.gauss(0, 0.05), 2)))
        flags.append(throttled)
    return Scenario("thermal", out, {"tau_fast": r1 * c1, "tau_slow": r2 * c2, "throttled": flags,
                                     "load_t": load_at * dt})


# ------------------------------------------------------------------ S1 signature set (frozen)
CLASSES = ["temperature", "light_ldr", "photodiode", "battery", "switch", "accelerometer", "microphone_level",
           "rssi", "current", "humidity", "distance_tof", "cpu_temp"]
NOISE_LEVELS = {"low": 0.5, "mid": 1.0, "high": 2.0}


def signature(cls: str, seed: int, noise: str) -> Scenario:
    """One case of the frozen S1 evaluation set: 12 physical classes x 5 seeds x 3 noise levels = 180 cases.

    Signatures follow the physical-signatures table in spec/knowledge-base.md (each row tagged [B]/[D]/[FP]).
    """
    r = random.Random(zlib.crc32(f"{cls}|{seed}|{noise}".encode()))   # stable across processes (hash() is not)
    k = NOISE_LEVELS[noise]
    out: List[Sample] = []
    if cls == "temperature":                       # slow first-order, ≤1 Hz, bounded, no overshoot
        y = 21 + r.random() * 3
        tgt = y
        for i, t in enumerate(_grid(240, 1.0)):
            if i % 80 == 40:
                tgt = 21 + r.uniform(-1, 4)
            y = tgt + (y - tgt) * math.exp(-1 / 20)
            out.append((t, round(y + r.gauss(0, 0.03 * k), 2)))
    elif cls == "light_ldr":                       # log-ish lux response, slow asymmetric, wide range
        lux = 200.0
        for i, t in enumerate(_grid(300, 0.5)):
            tgt = 800.0 if (i // 60) % 2 else 50.0
            a = math.exp(-0.5 / (0.3 if tgt > lux else 1.5))
            lux = tgt + (lux - tgt) * a
            out.append((t, max(1.0, lux * (1 + r.gauss(0, 0.02 * k)))))
    elif cls == "photodiode":                      # fast, linear, instant steps
        for i, t in enumerate(_grid(600, 0.01)):
            lvl = 1.0 if (i // 100) % 2 else 0.1
            out.append((t, lvl + r.gauss(0, 0.005 * k)))
    elif cls == "battery":                         # slow decline, plateau then knee, load sag
        for i, t in enumerate(_grid(300, 10.0)):
            soc = 1 - i / 300
            v = 3.6 + 0.5 * soc - 0.4 * math.exp(-soc * 12)
            sag = 0.08 if (i // 25) % 3 == 0 else 0.0
            out.append((t, round(v - sag + r.gauss(0, 0.003 * k), 3)))
    elif cls == "switch":                          # two levels, long dwell, sharp edges
        state = False
        for i, t in enumerate(_grid(300, 1.0)):
            if r.random() < 0.02:
                state = not state
            out.append((t, state))
    elif cls == "accelerometer":                   # 3-vector, |a| ≈ 1 g at rest, ringing on taps
        ring = 0.0
        for i, t in enumerate(_grid(500, 0.02)):
            if i % 150 == 75:
                ring = 0.8
            ring *= 0.9
            osc = ring * math.sin(2 * math.pi * 12 * t)
            out.append((t, (r.gauss(0, 0.01 * k) + osc, r.gauss(0, 0.01 * k), 1.0 + r.gauss(0, 0.01 * k) + osc / 2)))
    elif cls == "microphone_level":                # RMS level feature at 20 Hz: bursty, positive, fast
        for i, t in enumerate(_grid(600, 0.05)):
            speech = 1.0 if (i // 40) % 3 == 1 else 0.0
            out.append((t, max(0.0, 0.02 + speech * abs(r.gauss(0.3, 0.15)) + abs(r.gauss(0, 0.01 * k)))))
    elif cls == "rssi":                            # dBm, -100..-30, slow drift plus fading dips
        for i, t in enumerate(_grid(300, 1.0)):
            base = -60 - 6 * math.sin(t / 60)
            fade = -12 if r.random() < 0.05 else 0
            out.append((t, round(base + fade + r.gauss(0, 2 * k))))
    elif cls == "current":                         # steps with inrush that decays (tau = L/R)
        inrush = 0.0
        lvl = 0.2
        for i, t in enumerate(_grid(600, 0.05)):
            if i % 120 == 60:
                lvl = 1.5 if lvl < 1 else 0.2
                if lvl > 1:
                    inrush = 3.0
            inrush *= math.exp(-0.05 / 0.15)
            out.append((t, lvl + inrush + r.gauss(0, 0.01 * k)))
    elif cls == "humidity":                        # 0..100 %, slow, bounded, saturating
        h = 45.0
        for i, t in enumerate(_grid(300, 1.0)):
            tgt = 45 if (i // 100) % 2 == 0 else 85
            h = tgt + (h - tgt) * math.exp(-1 / 30)
            out.append((t, round(min(100.0, h + r.gauss(0, 0.2 * k)), 1)))
    elif cls == "distance_tof":                    # cm, piecewise smooth, jumps, dropouts
        d = 120.0
        for i, t in enumerate(_grid(400, 0.05)):
            if i % 100 == 50:
                d = r.uniform(30, 250)
            d += r.gauss(0, 0.3)
            v = 0.0 if r.random() < 0.02 else d + r.gauss(0, 0.5 * k)
            out.append((t, round(v, 1)))
    elif cls == "cpu_temp":                        # first-order lag to load steps, clamps near 80-85
        y = 45.0
        for i, t in enumerate(_grid(600, 1.0)):
            tgt = 72.0 if (i // 150) % 2 else 48.0
            y = tgt + (y - tgt) * math.exp(-1 / 40)
            out.append((t, round(min(85.0, y + r.gauss(0, 0.2 * k)), 1)))
    else:
        raise KeyError(cls)
    return Scenario(f"sig_{cls}_{seed}_{noise}", out, {"class": cls})


def signature_set() -> List[Scenario]:
    return [signature(c, s, nz) for c in CLASSES for s in range(5) for nz in NOISE_LEVELS]


# ------------------------------------------------------------------ registry
SINGLE: Dict[str, Callable[..., Scenario]] = {
    "first_order_step": first_order_step, "underdamped_step": underdamped_step, "ramp": ramp, "sine": sine,
    "sine_jitter": lambda seed=0: sine(seed, jitter=0.2), "alias_tone": tone_above_nyquist,
    "quantised_blip": quantised_blip, "gaussian": gaussian, "heavy_tail": heavy_tail, "flicker": flicker,
    "white": white, "mean_shift": mean_shift, "ar1_mean_shift": ar1_mean_shift, "chatter": chatter_near_threshold,
    "stuck": stuck, "clipped": clipped, "gaps": gaps, "hostile": hostile, "binary_dwell": binary_dwell,
    "thermal": thermal_step_throttle,
}
PAIRS = {"lead_lag": lead_lag, "common_cause": common_cause, "independent": independent}
TIMING = {"link_jitter": link_vs_sensor_jitter, "clock_skew": clock_skew, "ble_quantised": ble_quantised,
          "mqtt_dupes": mqtt_duplicates}
