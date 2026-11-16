"""Record real host signals to CSV for replay through the scoreboard (levels only; no content, no network names).

    python bench/record.py --seconds 3600 --out data/pc_trace.csv

Columns: t, cpu_load, battery_pct, ac_online, wifi_signal_pct, cpu_temp_c, loop_lag_ms
Missing sources are left blank (no Wi-Fi, no battery, no thermal sensor is not an error). Runs unchanged on
Windows (this PC) and Linux (the Raspberry Pi: /proc, /sys, vcgencmd).
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import subprocess
import sys
import time
from pathlib import Path


# ---------------------------------------------------------------- Windows
class _Win:
    def __init__(self):
        import ctypes
        from ctypes import wintypes
        self.ct, self.wt = ctypes, wintypes
        self._prev = None

        class FT(ctypes.Structure):
            _fields_ = [("lo", wintypes.DWORD), ("hi", wintypes.DWORD)]
        self.FT = FT

        class SPS(ctypes.Structure):
            _fields_ = [("AC", ctypes.c_ubyte), ("flag", ctypes.c_ubyte), ("pct", ctypes.c_ubyte),
                        ("sv", ctypes.c_ubyte), ("lt", wintypes.DWORD), ("ft", wintypes.DWORD)]
        self.SPS = SPS

    def cpu_load(self):
        idle, kern, user = self.FT(), self.FT(), self.FT()
        self.ct.windll.kernel32.GetSystemTimes(self.ct.byref(idle), self.ct.byref(kern), self.ct.byref(user))
        v = [(x.hi << 32) | x.lo for x in (idle, kern, user)]
        if self._prev is None:
            self._prev = v
            return None
        di, dk, du = (a - b for a, b in zip(v, self._prev))
        self._prev = v
        total = dk + du                                               # kernel time includes idle
        return None if total <= 0 else max(0.0, min(1.0, 1 - di / total))

    def battery(self):
        s = self.SPS()
        if not self.ct.windll.kernel32.GetSystemPowerStatus(self.ct.byref(s)):
            return None, None
        pct = None if s.pct == 255 else s.pct
        return pct, (None if s.AC == 255 else s.AC)

    def wifi(self):
        try:
            out = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True,
                                 timeout=4, errors="replace").stdout
            m = re.search(r"^\s*Signal\s*:\s*(\d+)\s*%", out, re.M)       # signal quality only; SSID discarded
            return int(m.group(1)) if m else None
        except Exception:                                             # noqa: BLE001
            return None

    def cpu_temp(self):
        return None                                                   # no portable CPU-temp API without WMI/admin


# ---------------------------------------------------------------- Linux / Raspberry Pi
class _Lin:
    def __init__(self):
        self._prev = None

    def cpu_load(self):
        with open("/proc/stat") as f:
            v = [int(x) for x in f.readline().split()[1:]]
        idle, total = v[3] + v[4], sum(v)
        if self._prev is None:
            self._prev = (idle, total)
            return None
        di, dt = idle - self._prev[0], total - self._prev[1]
        self._prev = (idle, total)
        return None if dt <= 0 else max(0.0, min(1.0, 1 - di / dt))

    def battery(self):
        base = Path("/sys/class/power_supply")
        try:
            for d in base.iterdir():
                if (d / "capacity").exists():
                    return int((d / "capacity").read_text()), None
        except Exception:                                             # noqa: BLE001
            pass
        return None, None

    def wifi(self):
        try:
            for line in open("/proc/net/wireless").read().splitlines()[2:]:
                parts = line.split()
                return int(float(parts[2].rstrip(".")))               # link quality (0-70)
        except Exception:                                             # noqa: BLE001
            return None

    def cpu_temp(self):
        try:
            return int(open("/sys/class/thermal/thermal_zone0/temp").read()) / 1000.0
        except Exception:                                             # noqa: BLE001
            return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=600)
    ap.add_argument("--out", default="data/pc_trace.csv")
    ap.add_argument("--wifi-every", type=int, default=5, help="seconds between Wi-Fi reads (netsh is slow)")
    a = ap.parse_args()
    src = _Win() if os.name == "nt" else _Lin()
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    with out.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["t", "cpu_load", "battery_pct", "ac_online", "wifi_signal_pct", "cpu_temp_c", "loop_lag_ms"])
        src.cpu_load()
        nxt, last_wifi = t0 + 1.0, None
        i = 0
        while time.perf_counter() - t0 < a.seconds:
            time.sleep(max(0.0, nxt - time.perf_counter()))
            now = time.perf_counter()
            lag = (now - nxt) * 1000.0
            nxt += 1.0
            i += 1
            if i % a.wifi_every == 1:
                last_wifi = src.wifi()
            bat, ac = src.battery()
            load = src.cpu_load()
            row = [round(now - t0, 3), None if load is None else round(load, 4), bat, ac, last_wifi,
                   src.cpu_temp(), round(lag, 2)]
            w.writerow(["" if x is None else x for x in row])
            fh.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
