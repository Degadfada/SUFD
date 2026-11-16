import asyncio

import pytest

from sufd.eno.wsproto import (OP_BIN, OP_CLOSE, OP_PING, OP_TEXT, EnoProtocolError, eno_accept_key, eno_encode,
                              eno_read_message)


def feed(data: bytes):
    r = asyncio.StreamReader()
    r.feed_data(data)
    r.feed_eof()
    return r


def read(data: bytes, **kw):
    async def go():
        return await eno_read_message(feed(data), **kw)
    return asyncio.run(go())


def test_rfc6455_accept_key_vector():
    assert eno_accept_key("dGhlIHNhbXBsZSBub25jZQ==") == "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="


@pytest.mark.parametrize("n", [0, 1, 125, 126, 127, 65535, 65536, 200_000])
def test_masked_roundtrip_at_every_length_class(n):
    payload = bytes((i * 7) & 0xFF for i in range(n))
    op, got = read(eno_encode(OP_BIN, payload, mask=True), max_size=1 << 20)
    assert (op, got) == (OP_BIN, payload)


def test_unmasked_client_frame_is_rejected():
    with pytest.raises(EnoProtocolError, match="not masked"):
        read(eno_encode(OP_TEXT, b"hi", mask=False))


def test_reserved_bits_and_unknown_opcodes_are_rejected():
    frame = bytearray(eno_encode(OP_TEXT, b"hi", mask=True))
    frame[0] |= 0x40
    with pytest.raises(EnoProtocolError, match="reserved"):
        read(bytes(frame))
    frame = bytearray(eno_encode(OP_TEXT, b"hi", mask=True))
    frame[0] = 0x80 | 0x3
    with pytest.raises(EnoProtocolError, match="opcode"):
        read(bytes(frame))


def test_oversize_message_is_rejected_with_1009():
    with pytest.raises(EnoProtocolError) as e:
        read(eno_encode(OP_TEXT, b"x" * 5000, mask=True), max_size=1000)
    assert e.value.code == 1009


def test_fragmented_message_reassembles_and_control_frames_may_interleave():
    f1 = bytearray(eno_encode(OP_TEXT, b"hel", mask=True)); f1[0] &= 0x7F          # FIN off
    ping = eno_encode(OP_PING, b"p", mask=True)
    f2 = bytearray(eno_encode(0x0, b"lo", mask=True))                               # continuation, FIN on
    data = bytes(f1) + ping + bytes(f2)

    async def go():
        r = feed(data)                                  # a StreamReader needs a running loop (Python 3.13)
        a = await eno_read_message(r)
        b = await eno_read_message(r)
        return a, b
    a, b = asyncio.run(go())
    assert a == (OP_PING, b"p") and b == (OP_TEXT, b"hello")


def test_bad_fragmentation_is_rejected():
    with pytest.raises(EnoProtocolError, match="continuation"):
        read(eno_encode(0x0, b"x", mask=True))
    long_ping = eno_encode(OP_PING, b"x" * 126, mask=True)
    with pytest.raises(EnoProtocolError, match="control"):
        read(long_ping)
    frag_close = bytearray(eno_encode(OP_CLOSE, b"", mask=True)); frag_close[0] &= 0x7F
    with pytest.raises(EnoProtocolError, match="control"):
        read(bytes(frag_close))


def test_truncated_input_raises_incomplete_not_hang():
    with pytest.raises(asyncio.IncompleteReadError):
        read(eno_encode(OP_TEXT, b"hello", mask=True)[:4])
