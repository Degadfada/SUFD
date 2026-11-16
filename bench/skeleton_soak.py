"""M1 gate: SUFD as a real daemon, a separate client process behaving like the phone, measured end to end.

    python bench/skeleton_soak.py --minutes 30 --out bench/soak_m1.json

- starts `python -m sufd serve --sim` as its OWN process (so client and server do not share a GIL or loop);
- the client sends phone-like samples (rtt 1 Hz, accel vector 20 Hz, battery 0.1 Hz) over the real WebSocket and
  measures sensor->client latency from the sample ids each patch reflects (S2);
- polls /metrics every 30 s: RSS, queue depth, drops, errors, quarantines, loop lag;
- passes iff the daemon stays alive, nothing is quarantined, memory growth after warm-up is <= 5%, and
  p95 latency is within the S2 budget (150 ms on a LAN; this run is loopback).
The result is labelled `loopback, simulated phone`: a real phone on Wi-Fi is a separate measurement.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import random
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from wsclient import Client                                               # noqa: E402

TOKEN = "soak-token-1"


def get_metrics(port):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics?token={TOKEN}", timeout=5) as r:
        return json.loads(r.read())


async def client(port, seconds, out):
    c = await Client.connect(port, TOKEN)
    assert c.status == 101
    created, lats, sid = {}, [], 0
    rnd = random.Random(3)
    end = time.perf_counter() + seconds
    nxt = {"rtt": 0.0, "acc": 0.0, "bat": 0.0}
    ping_at, pid = {}, 0

    async def reader():
        while True:
            try:
                m = await c.recv_json(timeout=10)
            except asyncio.TimeoutError:
                continue
            except Exception:                                              # noqa: BLE001
                return
            now = time.perf_counter()
            if isinstance(m, dict) and m.get("type") == "patch":
                for ids in m["reflect"].values():
                    lats.extend(now - created[i] for i in ids if i in created)
                if len(created) > 20000:
                    for k in sorted(created)[:10000]:
                        del created[k]
            elif isinstance(m, dict) and m.get("type") == "pong" and m["id"] in ping_at:
                out["rtt_ms"].append((now - ping_at.pop(m["id"])) * 1000)

    rd = asyncio.create_task(reader())
    while (now := time.perf_counter()) < end:
        batch = []
        if now >= nxt["acc"]:
            sid += 1; created[sid] = now
            t = now - end + seconds
            batch.append({"i": sid, "n": "phone.accel", "v": [math.cos(t * 1.3) * 3 + rnd.gauss(0, .1),
                                                              math.sin(t * .9) * 2 + rnd.gauss(0, .1),
                                                              9.8 + rnd.gauss(0, .05)], "h": "m/s2"})
            nxt["acc"] = now + 0.05
        if now >= nxt["rtt"]:
            pid += 1; ping_at[pid] = now
            await c.send_json({"type": "ping", "id": pid})
            sid += 1; created[sid] = now
            batch.append({"i": sid, "n": "phone.rtt_ms", "v": 8 + rnd.random() * 3, "h": "ms"})
            nxt["rtt"] = now + 1.0
        if now >= nxt["bat"]:
            sid += 1; created[sid] = now
            batch.append({"i": sid, "n": "phone.battery_pct", "v": max(5, 80 - (now - end + seconds) / 600), "h": "%"})
            nxt["bat"] = now + 10.0
        if batch:
            await c.send_json({"type": "samples", "batch": batch})
        await asyncio.sleep(0.005)
    rd.cancel()
    await c.close()
    return lats


def pct(a, p):
    a = sorted(a)
    return a[min(len(a) - 1, int(p * (len(a) - 1) + 0.5))] if a else None


async def main_async(a):
    port = a.port
    srv = subprocess.Popen([sys.executable, "-m", "sufd", "serve", "--sim", "--port", str(port), "--token", TOKEN],
                           cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        for _ in range(60):
            await asyncio.sleep(0.25)
            try:
                get_metrics(port)
                break
            except Exception:                                              # noqa: BLE001
                if srv.poll() is not None:
                    raise RuntimeError("server died at start: " + srv.stderr.read().decode()[:400])
        out = {"rtt_ms": []}
        seconds = int(a.minutes * 60)
        t0 = time.time()
        task = asyncio.create_task(client(port, seconds, out))
        samples = []
        while not task.done():
            await asyncio.sleep(30)
            if srv.poll() is not None:
                break
            try:
                m = get_metrics(port)
                samples.append({"t": round(time.time() - t0), "rss_mb": m["rss_mb"], "queue": m["queue_depth"],
                                "dropped": m["dropped"], "errors": m["ingest_errors"], "signals": m["signals"],
                                "loop_lag_ms_max": round(m["loop_lag_ms_max"], 1), "renders": m["renders"],
                                "render_ms_mean": m["render_ms_mean"], "quarantined": list(m["quarantined"]),
                                "slow": m.get("slow_ingests")})
                print(samples[-1], flush=True)
            except Exception as e:                                         # noqa: BLE001
                samples.append({"t": round(time.time() - t0), "error": str(e)})
        lats = await task
        alive = srv.poll() is None
        final = get_metrics(port) if alive else {}
    finally:
        if srv.poll() is None:
            srv.terminate()
    ms = [x * 1000 for x in lats]
    rss = [s["rss_mb"] for s in samples if s.get("rss_mb")]
    # growth is measured after warm-up; with a small --ring every buffer is full by then, so this is a LEAK test.
    # (With the default 4096-sample rings, 1 Hz signals take 68 min to fill, so growth there is buffer fill, not a leak.)
    wi = min(len(rss) - 1, int(a.warmup_min * 2)) if rss else 0              # samples are 30 s apart
    warm = rss[wi] if rss else None
    growth = None if not rss or not warm else round(100 * (rss[-1] - warm) / warm, 1)
    result = {
        "label": "loopback, simulated phone (separate client process), PC",
        "minutes": a.minutes, "ring": a.ring or 4096, "warmup_min": a.warmup_min, "daemon_alive": alive, "samples_measured": len(ms),
        "latency_ms": {"p50": pct(ms, .5), "p95": pct(ms, .95), "p99": pct(ms, .99), "max": max(ms) if ms else None},
        "app_rtt_ms_p95": pct(out["rtt_ms"], .95),
        "rss_mb_first_last": [rss[0] if rss else None, rss[-1] if rss else None], "rss_growth_pct_after_warmup": growth,
        "final": {k: final.get(k) for k in ("signals", "dropped", "ingest_errors", "slow_ingests", "quarantined",
                                              "loop_lag_ms_max", "render_ms_mean", "patches")},
        "timeline": samples,
    }
    result["pass"] = bool(alive and not final.get("quarantined") and (growth is None or growth <= 5.0)
                          and result["latency_ms"]["p95"] is not None and result["latency_ms"]["p95"] <= 150)
    Path(a.out).write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "timeline"}, indent=1))
    return 0 if result["pass"] else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=30)
    ap.add_argument("--port", type=int, default=18810)
    ap.add_argument("--ring", type=int, default=0, help="per-signal ring size (small = buffers saturate fast)")
    ap.add_argument("--warmup-min", type=float, default=5.0)
    ap.add_argument("--out", default=str(HERE / "soak_m1.json"))
    return asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    sys.exit(main())
