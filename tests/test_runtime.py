"""M1 walking skeleton: the daemon, the transport and the phone surface, driven by a real socket client."""
import asyncio
import contextlib
import json
import math
import time

from sufd.eno.transport import EnoServer, eno_validate_value
from sufd.eno.wsproto import OP_CLOSE, OP_TEXT, eno_encode
from sufd.kufre.runtime import KufreRuntime
from wsclient import Client, http_get

TOKEN = "tok_123-ABC"


@contextlib.asynccontextmanager
async def running(**rt_kw):
    rt = KufreRuntime(**rt_kw)
    srv = EnoServer(rt, port=0, token=TOKEN)
    port = await srv.start()
    stop = asyncio.Event()
    task = asyncio.create_task(rt.run(stop))
    try:
        yield rt, srv, port
    finally:
        stop.set()
        await task
        await srv.stop()


async def until(pred, timeout=3.0, step=0.02):
    t = time.monotonic()
    while time.monotonic() - t < timeout:
        if pred():
            return True
        await asyncio.sleep(step)
    return False


def run(coro):
    return asyncio.run(coro)


# ------------------------------------------------------------------ http + auth
def test_http_routes_and_pairing_token():
    async def go():
        async with running() as (rt, srv, port):
            assert (await http_get(port, "/healthz"))[0] == 200
            assert (await http_get(port, "/"))[0] == 403                          # no token
            assert (await http_get(port, "/?token=wrong"))[0] == 403
            code, body = await http_get(port, f"/?token={TOKEN}")
            assert code == 200 and b"SUFD surface" in body
            code, body = await http_get(port, f"/metrics?token={TOKEN}")
            assert code == 200 and "signals" in json.loads(body)
            assert (await http_get(port, f"/nope?token={TOKEN}"))[0] == 404
            assert srv.stats["rejected_auth"] == 2
    run(go())


def test_websocket_rejects_wrong_token_and_foreign_origin():
    async def go():
        async with running() as (rt, srv, port):
            assert (await Client.connect(port, "wrong")).status == 403
            assert (await Client.connect(port, TOKEN, origin="http://evil.example")).status == 403
            ok = await Client.connect(port, TOKEN, origin=f"http://127.0.0.1:{port}")
            assert ok.status == 101
            await ok.close()
            assert srv.stats["rejected_origin"] == 1 and srv.stats["rejected_auth"] == 1
    run(go())


# ------------------------------------------------------------------ the loop: sensor -> pixel
def test_samples_become_a_rendered_panel_and_latency_is_measured():
    async def go():
        async with running() as (rt, srv, port):
            c = await Client.connect(port, TOKEN)
            assert (await c.recv_json())["type"] == "hello"
            created, lats, panel_seen, i = {}, [], {}, 0
            t_end = time.perf_counter() + 3.0
            nxt = time.perf_counter()
            while time.perf_counter() < t_end:
                if time.perf_counter() >= nxt:                                   # 50 Hz sensor
                    i += 1
                    created[i] = time.perf_counter()
                    await c.send_json({"type": "samples", "batch": [
                        {"i": i, "n": "phone.test", "v": 20 + math.sin(i / 8.0), "h": "C"}]})
                    nxt += 0.02
                try:
                    m = await asyncio.wait_for(c.recv_json(), 0.005)
                except asyncio.TimeoutError:
                    continue
                if m.get("type") == "patch":
                    now = time.perf_counter()
                    panel_seen.update(m["panels"])
                    for ids in m["reflect"].values():
                        lats += [now - created[x] for x in ids if x in created]
            await c.close()
            assert "phone.test" in panel_seen and panel_seen["phone.test"]["svg"].startswith("<svg")
            assert len(lats) > 100
            lats.sort()
            p50, p95 = lats[len(lats) // 2] * 1000, lats[int(0.95 * len(lats))] * 1000
            print(f"\nloopback sensor->client latency: n={len(lats)} p50={p50:.0f} ms p95={p95:.0f} ms")
            assert p95 < 300, p95                      # patch coalescing is 100 ms; the LAN target is p95 <= 150 ms
    run(go())


def test_the_human_pointer_is_answered_from_the_envelope():
    async def go():
        async with running() as (rt, srv, port):
            c = await Client.connect(port, TOKEN)
            await c.recv_json()
            for i in range(1, 80):
                await c.send_json({"type": "samples", "batch": [{"i": i, "n": "phone.p", "v": 20 + (i % 7) * 0.1}]})
                await asyncio.sleep(0.01)
            assert await until(lambda: "phone.p" in rt.panels and rt.panels["phone.p"]["t1"] > 0)
            p = rt.panels["phone.p"]
            await c.send_json({"type": "point", "name": "phone.p", "t": (p["t0"] + p["t1"]) / 2})
            got = None
            for _ in range(60):
                try:
                    m = await asyncio.wait_for(c.recv_json(), 0.2)
                except asyncio.TimeoutError:
                    continue
                if m.get("type") == "patch" and (m["panels"].get("phone.p") or {}).get("pointer"):
                    got = m["panels"]["phone.p"]["pointer"]
                    break
            await c.close()
            assert got and got.startswith("at t=")
    run(go())


def test_round_trip_ping_is_answered():
    async def go():
        async with running() as (rt, srv, port):
            c = await Client.connect(port, TOKEN)
            await c.recv_json()
            await c.send_json({"type": "ping", "id": 7})
            for _ in range(20):
                m = await c.recv_json()
                if m.get("type") == "pong":
                    assert m["id"] == 7
                    break
            else:
                raise AssertionError("no pong")
            await c.close()
    run(go())


# ------------------------------------------------------------------ hostile input never hurts the daemon
def test_validation_of_sensor_supplied_values():
    assert eno_validate_value(3.5) == (True, 3.5)
    assert eno_validate_value(True) == (True, True)
    assert eno_validate_value([1, 2, 3]) == (True, (1.0, 2.0, 3.0))
    for bad in (float("nan"), float("inf"), 1e30, "x" * 65, [1] * 9, [], [1, "a"], {"a": 1}, None, [[1]]):
        assert eno_validate_value(bad)[0] is False, bad


def test_hostile_messages_are_counted_and_ignored():
    async def go():
        async with running() as (rt, srv, port):
            c = await Client.connect(port, TOKEN)
            await c.recv_json()
            await c.send_raw_text(b"not json at all")
            await c.send_raw_text(b'{"type":"samples","batch":[{"n":"a.b","v":NaN}]}')         # NaN literal
            await c.send_raw_text(b"\xff\xfe\x00")                                               # invalid UTF-8
            await c.send_json({"type": "samples", "batch": [
                {"n": "<script>alert(1)</script>", "v": 1}, {"n": "x" * 100, "v": 1}, {"n": "ok.name", "v": 1e30},
                {"n": "ok.name", "v": {"a": 1}}, {"n": 5, "v": 1}, "junk", None]})
            await c.send_json({"type": "samples", "batch": "nope"})
            await c.send_json([1, 2, 3])
            await c.send_json({"type": "point", "name": 7, "t": "x"})
            await c.send_json({"type": "samples", "batch": [{"i": 1, "n": "phone.fine", "v": 21.5}] * 3})
            assert await until(lambda: "phone.fine" in rt.mind.signals)                          # still alive
            assert srv.stats["bad_json"] >= 3 and srv.stats["bad_samples"] >= 5
            assert not any("<" in n for n in rt.mind.signals)
            await c.close()
    run(go())


def test_protocol_violation_closes_that_connection_only():
    async def go():
        async with running() as (rt, srv, port):
            bad = await Client.connect(port, TOKEN)
            await bad.recv_json()
            bad.w.write(eno_encode(OP_TEXT, b"{}", mask=False))                       # clients must mask
            await bad.w.drain()
            op, data = await bad.recv()
            while op == OP_TEXT:                                                      # skip any queued text
                op, data = await bad.recv()
            assert op == OP_CLOSE and int.from_bytes(data[:2], "big") == 1002
            good = await Client.connect(port, TOKEN)
            assert good.status == 101
            await good.close()
            assert srv.stats["protocol_errors"] == 1
    run(go())


def test_oversize_batches_and_floods_are_bounded():
    async def go():
        async with running() as (rt, srv, port):
            c = await Client.connect(port, TOKEN)
            await c.recv_json()
            big = [{"i": k + 1, "n": "flood.x", "v": float(k)} for k in range(1000)]
            await c.send_json({"type": "samples", "batch": big})                      # only the first 200 are read
            for _ in range(40):
                await c.send_json({"type": "samples", "batch": big[:200]})
            await asyncio.sleep(0.5)
            assert srv.stats["rate_limited"] > 0
            assert len(rt.queue) <= rt.queue_max
            await c.close()
    run(go())


def test_connection_cap():
    async def go():
        async with running() as (rt, srv, port):
            srv.max_conns = 2
            a, b = await Client.connect(port, TOKEN), await Client.connect(port, TOKEN)
            assert (a.status, b.status) == (101, 101)
            assert (await Client.connect(port, TOKEN)).status == 503
            await a.close()
            await b.close()
    run(go())


# ------------------------------------------------------------------ runtime: bounded queue, fault isolation
def test_queue_is_bounded_and_drops_the_oldest():
    rt = KufreRuntime(queue_max=10)
    for k in range(50):
        rt.submit("x.y", float(k))
    assert len(rt.queue) == 10 and rt.stats["dropped"] == 40
    assert [q[2] for q in rt.queue] == [float(k) for k in range(40, 50)]


def test_a_poisoned_signal_is_quarantined_and_the_rest_keep_working():
    async def go():
        async with running(quarantine_after=5) as (rt, srv, port):
            for k in range(60):
                rt.submit("good.a", 20 + math.sin(k / 5))
                rt.submit("poison.b", None if k >= 10 else 1.0)                       # None crashes slice-1 ingest
            assert await until(lambda: "poison.b" in rt.quarantined)
            for k in range(30):
                rt.submit("good.a", 21.0)
            assert await until(lambda: rt.mind.signals["good.a"].env.n >= 80)
            assert await until(lambda: rt.panels.get("poison.b", {}).get("state") == "quarantined")
            assert rt.panels["good.a"]["state"] != "quarantined"
            assert rt.stats["ingest_errors"] >= 5
    run(go())


def test_host_self_signals_flow_through_the_same_pipeline():
    async def go():
        async with running() as (rt, srv, port):
            assert await until(lambda: "self.loop_lag_ms" in rt.mind.signals
                               and rt.mind.signals["self.loop_lag_ms"].env.n > 5, timeout=4.0)    # sampled at ~10 Hz
            assert await until(lambda: {"self.cpu_load", "self.signals"} <= set(rt.mind.signals), timeout=4.0)
            assert await until(lambda: "self.loop_lag_ms" in rt.panels)
    run(go())


def test_a_panel_is_not_resent_when_nothing_changed():
    async def go():
        async with running() as (rt, srv, port):
            c = await Client.connect(port, TOKEN)
            await c.recv_json()
            for k in range(40):
                rt.submit("phone.q", 20.0 + 0.01 * k)
            first = None
            for _ in range(30):
                m = await asyncio.wait_for(c.recv_json(), 1.0)
                if m.get("type") == "patch" and "phone.q" in m["panels"]:
                    first = m
                    break
            assert first
            await asyncio.sleep(0.6)                                                  # drain any in-flight patch
            extra = 0
            while True:
                try:
                    m = await asyncio.wait_for(c.recv_json(), 0.4)
                except asyncio.TimeoutError:
                    break
                if m.get("type") == "patch" and "phone.q" in m["panels"]:
                    extra += 1
            assert extra <= 1                                                         # at most one late in-flight patch
            await c.close()
    run(go())
