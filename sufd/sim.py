"""Simulated sources, so the first-contact story can run with no hardware.

Each source is a function t -> value. A node 'appears' at a chosen time, the way an
ESP32 joining the network would.
"""
from __future__ import annotations

import math
import random
from typing import Callable, Dict, Tuple

Source = Tuple[float, float, Callable[[float], object], object]   # (appears_at, period_s, fn, hint)


def make_sources(seed: int = 7) -> Dict[str, Source]:
    rnd = random.Random(seed)
    state = {"heat": 22.0}

    def heat(t: float) -> float:
        # slow, smooth, bounded; a heater switches on at t=200 and the reading climbs
        target = 22.0 + (5.5 if t >= 200 else 0.0) + 0.3 * math.sin(t / 40.0)
        state["heat"] += (target - state["heat"]) * 0.03 + rnd.gauss(0, 0.04)
        return round(state["heat"], 2)

    door_events = {40, 95, 100, 230}

    def door(t: float) -> bool:
        return sum(1 for e in door_events if e <= t) % 2 == 1

    def mode(t: float) -> str:
        return ("idle", "walk", "idle", "run", "walk")[min(int(t // 60), 4)]

    return {
        "phone.battery": (0.0, 1.0, lambda t: round(80 - 0.012 * t, 2), None),
        "phone.door": (0.0, 1.0, door, None),
        "phone.mode": (0.0, 1.0, mode, None),
        "mic.level": (0.0, 0.1, lambda t: 0.5 + 0.4 * math.sin(2 * math.pi * t / 2.5) + rnd.gauss(0, 0.05), None),
        "imu.accel": (0.0, 0.1, lambda t: (math.cos(t * 1.3) * 3 + rnd.gauss(0, 0.1),
                                            math.sin(t * 0.9) * 2 + rnd.gauss(0, 0.1),
                                            9.8 + rnd.gauss(0, 0.05)), None),
        # the new sense: an unlabeled ESP32 heat sensor that joins at t=60
        "esp32.adc0": (60.0, 1.0, heat, None),
    }
