"""A tiny stdlib WebSocket client for testing the SUFD server (masked frames, like a browser)."""
import asyncio
import base64
import json
import os

from sufd.eno.wsproto import OP_CLOSE, OP_TEXT, eno_accept_key, eno_encode, eno_read_message


class Client:
    def __init__(self, reader, writer):
        self.r, self.w = reader, writer

    @classmethod
    async def connect(cls, port, token="", origin=None, host=None, path="/ws"):
        r, w = await asyncio.open_connection("127.0.0.1", port)
        key = base64.b64encode(os.urandom(16)).decode()
        lines = [f"GET {path}?token={token} HTTP/1.1", f"Host: {host or '127.0.0.1:%d' % port}",
                 "Upgrade: websocket", "Connection: Upgrade", f"Sec-WebSocket-Key: {key}",
                 "Sec-WebSocket-Version: 13"]
        if origin:
            lines.append(f"Origin: {origin}")
        w.write(("\r\n".join(lines) + "\r\n\r\n").encode())
        await w.drain()
        head = await r.readuntil(b"\r\n\r\n")
        status = int(head.split(b" ", 2)[1])
        c = cls(r, w)
        c.status = status
        if status == 101:
            assert eno_accept_key(key).encode() in head
        return c

    async def send_json(self, obj):
        self.w.write(eno_encode(OP_TEXT, json.dumps(obj).encode(), mask=True))
        await self.w.drain()

    async def send_raw_text(self, s: bytes):
        self.w.write(eno_encode(OP_TEXT, s, mask=True))
        await self.w.drain()

    async def recv(self, timeout=2.0):
        op, data = await asyncio.wait_for(eno_read_message(self.r, 1 << 22, require_mask=False), timeout)
        return op, data

    async def recv_json(self, timeout=2.0):
        op, data = await self.recv(timeout)
        return json.loads(data) if op == OP_TEXT else (op, data)

    async def close(self):
        try:
            self.w.close()
            await self.w.wait_closed()
        except Exception:
            pass


async def http_get(port, path, host=None):
    r, w = await asyncio.open_connection("127.0.0.1", port)
    w.write(f"GET {path} HTTP/1.1\r\nHost: {host or '127.0.0.1:%d' % port}\r\n\r\n".encode())
    await w.drain()
    data = await asyncio.wait_for(r.read(1 << 20), 3)
    w.close()
    head, _, body = data.partition(b"\r\n\r\n")
    return int(head.split(b" ", 2)[1]), body
