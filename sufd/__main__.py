"""SUFD command line.

    python -m sufd serve                       # daemon on 127.0.0.1:8810, simulated senses off
    python -m sufd serve --sim                 # also feed the simulated demo senses (heater story)
    python -m sufd serve --host 0.0.0.0        # LAN (the phone): prints a URL with the pairing token

The pairing token is generated per run unless --token is given. The server is bound to localhost unless the
owner opts in to the LAN, because anything that can reach the port and knows the token can feed samples.
"""
from __future__ import annotations

import argparse
import asyncio
import secrets
import socket
import sys

from .eno.transport import EnoServer
from .kufre.runtime import KufreRuntime


def _lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))                  # no packet is sent; this only selects the interface
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:                                      # noqa: BLE001
        return "127.0.0.1"


async def _feed_sim(rt: KufreRuntime, stop: asyncio.Event) -> None:
    """Replay the simulated demo senses in real time (so the page is alive without any hardware)."""
    from .sim import make_sources
    src = make_sources()
    next_at = {k: v[0] for k, v in src.items()}
    t0 = rt.now()
    while not stop.is_set():
        t = rt.now() - t0
        for k, (_, period, fn, hint) in src.items():
            if t >= next_at[k]:
                rt.submit("sim." + k, fn(t), hint)
                next_at[k] = t + period
        await asyncio.sleep(0.02)


async def serve(a) -> int:
    rt = KufreRuntime(patch_hz=a.patch_hz, ring_capacity=a.ring or None)
    token = a.token or secrets.token_urlsafe(9)
    srv = EnoServer(rt, host=a.host, port=a.port, token=token)
    port = await srv.start()
    stop = asyncio.Event()
    host = _lan_ip() if a.host in ("0.0.0.0", "::") else a.host
    print(f"SUFD serving on {a.host}:{port}")
    print(f"  open:    http://{host}:{port}/?token={token}")
    print(f"  metrics: http://{host}:{port}/metrics?token={token}")
    if a.host in ("0.0.0.0", "::"):
        print("  NOTE: reachable from your LAN; anyone with the token can feed samples. Ctrl+C to stop.")
    tasks = [asyncio.create_task(rt.run(stop))]
    if a.sim:
        tasks.append(asyncio.create_task(_feed_sim(rt, stop)))
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass
    finally:
        stop.set()
        await srv.stop()
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="sufd")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve", help="run the SUFD daemon and phone surface")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8810)
    s.add_argument("--token", default="")
    s.add_argument("--patch-hz", type=float, default=10.0)
    s.add_argument("--ring", type=int, default=0, help="samples kept per signal (default 4096)")
    s.add_argument("--sim", action="store_true", help="feed the simulated demo senses")
    a = ap.parse_args(argv)
    try:
        return asyncio.run(serve(a))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
