"""eno — intake. A minimal RFC 6455 WebSocket codec on asyncio streams (stdlib only).

Server-side rules enforced: client frames must be masked, control frames must be short and unfragmented, message
size is capped, reserved bits and unknown opcodes are rejected. Anything else raises EnoProtocolError, which the
transport turns into a close — never a crash.
"""
from __future__ import annotations

import base64
import hashlib
import os
import struct
from typing import Tuple

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
OP_CONT, OP_TEXT, OP_BIN, OP_CLOSE, OP_PING, OP_PONG = 0x0, 0x1, 0x2, 0x8, 0x9, 0xA
MAX_CONTROL = 125


class EnoProtocolError(Exception):
    """The peer broke the protocol (close code 1002), sent too much (1009), or sent bad data (1007)."""

    def __init__(self, msg: str, code: int = 1002):
        super().__init__(msg)
        self.code = code


def eno_accept_key(key: str) -> str:
    return base64.b64encode(hashlib.sha1((key + GUID).encode()).digest()).decode()


def eno_encode(opcode: int, payload: bytes = b"", mask: bool = False) -> bytes:
    n = len(payload)
    head = bytes([0x80 | opcode])
    mbit = 0x80 if mask else 0
    if n < 126:
        head += bytes([mbit | n])
    elif n < 1 << 16:
        head += bytes([mbit | 126]) + struct.pack("!H", n)
    else:
        head += bytes([mbit | 127]) + struct.pack("!Q", n)
    if mask:
        key = os.urandom(4)
        payload = bytes(b ^ key[i & 3] for i, b in enumerate(payload))
        return head + key + payload
    return head + payload


def _unmask(payload: bytes, key: bytes) -> bytes:
    if not payload:
        return payload
    # XOR with a repeated key via int arithmetic: far faster than a per-byte Python loop
    n = len(payload)
    k = (key * (n // 4 + 1))[:n]
    return (int.from_bytes(payload, "big") ^ int.from_bytes(k, "big")).to_bytes(n, "big")


async def _read_frame(reader, max_size: int, require_mask: bool) -> Tuple[bool, int, bytes]:
    h = await reader.readexactly(2)
    fin, b1, b2 = bool(h[0] & 0x80), h[0], h[1]
    if b1 & 0x70:
        raise EnoProtocolError("reserved bits set")
    opcode = b1 & 0x0F
    if opcode not in (OP_CONT, OP_TEXT, OP_BIN, OP_CLOSE, OP_PING, OP_PONG):
        raise EnoProtocolError(f"unknown opcode {opcode}")
    masked, n = bool(b2 & 0x80), b2 & 0x7F
    if require_mask and not masked:
        raise EnoProtocolError("client frame not masked")
    if n == 126:
        n = struct.unpack("!H", await reader.readexactly(2))[0]
    elif n == 127:
        n = struct.unpack("!Q", await reader.readexactly(8))[0]
    if opcode >= 0x8 and (n > MAX_CONTROL or not fin):
        raise EnoProtocolError("bad control frame")
    if n > max_size:
        raise EnoProtocolError("frame too large", 1009)
    key = await reader.readexactly(4) if masked else b""
    payload = await reader.readexactly(n) if n else b""
    return fin, opcode, _unmask(payload, key) if masked else payload


async def eno_read_message(reader, max_size: int = 1 << 20, require_mask: bool = True) -> Tuple[int, bytes]:
    """Next complete message as (opcode, payload).

    Control frames come back immediately, even in the middle of a fragmented message (RFC 6455 §5.4), so the
    half-assembled message is kept on the reader and survives across calls."""
    opcode0, buf = getattr(reader, "_eno_frag", (None, b""))
    while True:
        fin, op, data = await _read_frame(reader, max_size, require_mask)
        if op >= 0x8:
            reader._eno_frag = (opcode0, buf)
            return op, data
        if op == OP_CONT:
            if opcode0 is None:
                raise EnoProtocolError("continuation without a start")
        else:
            if opcode0 is not None:
                raise EnoProtocolError("new message inside a fragmented one")
            opcode0 = op
        buf += data
        if len(buf) > max_size:
            raise EnoProtocolError("message too large", 1009)
        if fin:
            reader._eno_frag = (None, b"")
            return opcode0, buf
