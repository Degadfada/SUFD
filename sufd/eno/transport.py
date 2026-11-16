"""eno — intake. HTTP + WebSocket transport for the phone surface (stdlib asyncio only).

Security posture (threat model in spec/knowledge-base.md §7):
- a pairing token is required for the socket (constant-time compare); wrong token -> 403, nothing else is revealed;
- a browser Origin, if present, must match the Host (blocks cross-site WebSocket hijacking);
- bound to 127.0.0.1 unless the owner opts in to the LAN;
- caps everywhere: header bytes, message size, batch size, name length, per-connection sample rate, connections;
- sensor-supplied names/values are validated here, never trusted: they become DOM text via textContent only.
"""
from __future__ import annotations

import asyncio
import hmac
import json
import math
import re
import time
from pathlib import Path
from typing import Optional, Tuple

from .wsproto import (OP_CLOSE, OP_PING, OP_PONG, OP_TEXT, EnoProtocolError, eno_accept_key, eno_encode,
                      eno_read_message)

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:\-]{0,63}$")
MAX_HEADER = 16 * 1024
MAX_MSG = 256 * 1024
MAX_BATCH = 200
MAX_STR = 64
MAX_VEC = 8
RATE_LIMIT_PER_S = 2000


def _reject_constant(name: str):
    raise ValueError(f"non-finite JSON constant {name}")           # json.loads accepts NaN/Infinity by default


def eno_validate_value(v) -> Tuple[bool, object]:
    """Accept a finite number, bool, short string, or a short list of finite numbers (a vector)."""
    if isinstance(v, bool):
        return True, v
    if isinstance(v, (int, float)):
        return (True, v) if math.isfinite(v) and abs(v) < 1e15 else (False, None)
    if isinstance(v, str):
        return (True, v) if len(v) <= MAX_STR else (False, None)
    if isinstance(v, list) and 1 <= len(v) <= MAX_VEC and all(
            isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and abs(x) < 1e15
            for x in v):
        return True, tuple(float(x) for x in v)
    return False, None


class EnoServer:
    def __init__(self, runtime, *, host: str = "127.0.0.1", port: int = 8810, token: str = "",
                 max_conns: int = 8, page: Optional[Path] = None):
        self.rt, self.host, self.port, self.token = runtime, host, port, token
        self.max_conns = max_conns
        self.page = page or Path(__file__).resolve().parent.parent / "edimek" / "web" / "phone.html"
        self.conns = 0
        self.stats = {"rejected_auth": 0, "rejected_origin": 0, "bad_samples": 0, "protocol_errors": 0,
                      "rate_limited": 0, "bad_json": 0}
        self._server: Optional[asyncio.AbstractServer] = None

    async def start(self) -> int:
        self._server = await asyncio.start_server(self._handle, self.host, self.port)
        self.port = self._server.sockets[0].getsockname()[1]
        return self.port

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    # ---------------------------------------------------------------- HTTP
    async def _read_head(self, reader) -> Tuple[str, str, dict]:
        raw = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 5.0)
        if len(raw) > MAX_HEADER:
            raise ValueError("header too large")
        lines = raw.decode("latin-1").split("\r\n")
        method, target, _ = lines[0].split(" ", 2)
        headers = {}
        for ln in lines[1:]:
            if ":" in ln:
                k, v = ln.split(":", 1)
                headers[k.strip().lower()] = v.strip()
        return method, target, headers

    @staticmethod
    def _http(writer, code: int, body: bytes, ctype: str = "text/plain; charset=utf-8", extra: str = "") -> None:
        reason = {200: "OK", 403: "Forbidden", 404: "Not Found", 400: "Bad Request", 503: "Service Unavailable"}[code]
        writer.write(f"HTTP/1.1 {code} {reason}\r\nContent-Type: {ctype}\r\nContent-Length: {len(body)}\r\n"
                     f"Cache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\nConnection: close\r\n{extra}\r\n"
                     .encode() + body)

    def _origin_ok(self, headers: dict) -> bool:
        origin = headers.get("origin")
        if not origin:
            return True                                              # non-browser client (the tests, a node)
        host = headers.get("host", "")
        return re.sub(r"^https?://", "", origin).rstrip("/") == host

    def _token_ok(self, query: str) -> bool:
        if not self.token:
            return True
        m = re.search(r"(?:^|&)token=([A-Za-z0-9_\-]{1,128})(?:&|$)", query)
        return bool(m) and hmac.compare_digest(m.group(1), self.token)

    async def _handle(self, reader, writer) -> None:
        try:
            method, target, headers = await self._read_head(reader)
            path, _, query = target.partition("?")
            if method != "GET":
                return self._http(writer, 400, b"bad request")
            if headers.get("upgrade", "").lower() == "websocket" and path == "/ws":
                return await self._socket(reader, writer, headers, query)
            if path == "/healthz":
                return self._http(writer, 200, b"ok")
            if not self._token_ok(query):
                self.stats["rejected_auth"] += 1
                return self._http(writer, 403, b"forbidden")
            if path == "/":
                return self._http(writer, 200, self.page.read_bytes(), "text/html; charset=utf-8")
            if path == "/metrics":
                return self._http(writer, 200, json.dumps({**self.rt.metrics(), "transport": self.stats},
                                                          default=str).encode(), "application/json")
            self._http(writer, 404, b"not found")
        except (asyncio.TimeoutError, asyncio.IncompleteReadError, asyncio.LimitOverrunError, ValueError,
                ConnectionError, UnicodeDecodeError):
            pass
        finally:
            try:
                await writer.drain()
            except Exception:                                        # noqa: BLE001
                pass
            writer.close()

    # ---------------------------------------------------------------- WebSocket
    async def _socket(self, reader, writer, headers: dict, query: str) -> None:
        if not self._origin_ok(headers):
            self.stats["rejected_origin"] += 1
            return self._http(writer, 403, b"bad origin")
        if not self._token_ok(query):
            self.stats["rejected_auth"] += 1
            return self._http(writer, 403, b"forbidden")
        key = headers.get("sec-websocket-key")
        if not key or self.conns >= self.max_conns:
            return self._http(writer, 503 if key else 400, b"unavailable")
        writer.write(("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                      f"Sec-WebSocket-Accept: {eno_accept_key(key)}\r\n\r\n").encode())
        await writer.drain()
        self.conns += 1
        surface = self.rt.new_surface()
        sender = asyncio.create_task(self._push(writer, surface))
        bucket, last = float(RATE_LIMIT_PER_S), time.monotonic()
        try:
            while True:
                op, data = await eno_read_message(reader, MAX_MSG)
                if op == OP_CLOSE:
                    writer.write(eno_encode(OP_CLOSE, data[:2]))
                    break
                if op == OP_PING:
                    writer.write(eno_encode(OP_PONG, data))
                    continue
                if op != OP_TEXT:
                    continue
                now = time.monotonic()
                bucket = min(RATE_LIMIT_PER_S, bucket + (now - last) * RATE_LIMIT_PER_S)
                last = now
                try:
                    msg = json.loads(data.decode("utf-8"), parse_constant=_reject_constant)
                except (ValueError, UnicodeDecodeError):
                    self.stats["bad_json"] += 1
                    continue
                bucket = self._message(msg, surface, writer, bucket)
        except EnoProtocolError as e:
            self.stats["protocol_errors"] += 1
            try:
                writer.write(eno_encode(OP_CLOSE, e.code.to_bytes(2, "big")))
            except Exception:                                        # noqa: BLE001
                pass
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        finally:
            sender.cancel()
            self.conns -= 1
            self.rt.drop_surface(surface)

    def _message(self, msg, surface, writer, bucket: float) -> float:
        if not isinstance(msg, dict):
            return bucket
        kind = msg.get("type")
        if kind == "samples":
            batch = msg.get("batch")
            if not isinstance(batch, list):
                return bucket
            for item in batch[:MAX_BATCH]:
                if bucket < 1:
                    self.stats["rate_limited"] += 1
                    continue
                bucket -= 1
                if not isinstance(item, dict) or not isinstance(item.get("n"), str) or not NAME_RE.match(item["n"]):
                    self.stats["bad_samples"] += 1
                    continue
                ok, v = eno_validate_value(item.get("v"))
                hint = item.get("h") if isinstance(item.get("h"), str) and len(item["h"]) <= 16 else None
                sid = item.get("i") if isinstance(item.get("i"), int) and 0 < item["i"] < 1 << 40 else 0
                if not ok:
                    self.stats["bad_samples"] += 1
                    continue
                self.rt.submit(item["n"], v, hint, surface.conn_id, sid)
        elif kind == "ping" and isinstance(msg.get("id"), int):
            writer.write(eno_encode(OP_TEXT, json.dumps({"type": "pong", "id": msg["id"]}).encode()))
        elif kind == "point" and isinstance(msg.get("name"), str) and isinstance(msg.get("t"), (int, float)):
            self.rt.point(msg["name"], float(msg["t"]))
        elif kind == "latency" and isinstance(msg.get("p95"), (int, float)):
            self.rt.stats["client_latency"] = {k: msg.get(k) for k in ("n", "p50", "p95", "p99")
                                               if isinstance(msg.get(k), (int, float))}
        return bucket

    async def _push(self, writer, surface) -> None:
        """Send a patch whenever the runtime's single patch clock fires and this surface has something new."""
        try:
            writer.write(eno_encode(OP_TEXT, json.dumps({"type": "hello", "patch_hz": self.rt.patch_hz}).encode()))
            while True:
                try:
                    await asyncio.wait_for(self.rt.patch_event.wait(), 1.0)   # timeout only guards a stopped runtime
                except asyncio.TimeoutError:
                    continue
                patch = surface.patch(self.rt)
                if patch:
                    patch["server_t"] = round(self.rt.now(), 4)
                    writer.write(eno_encode(OP_TEXT, json.dumps(patch, separators=(",", ":")).encode()))
                    self.rt.stats["patches"] += 1
                    await asyncio.wait_for(writer.drain(), 2.0)        # a stalled phone is dropped, not waited on
        except (asyncio.CancelledError, ConnectionError, asyncio.TimeoutError):
            pass
