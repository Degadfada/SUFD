"""eno — intake. EnoSignal: a named source of (t, value) samples whose meaning is not assumed.

Values may be numbers, bools, strings, or fixed-length numeric tuples (vectors).
A EnoSignal owns a bounded ring buffer and an IdeaEnvelope that learns from every push.
"""
from __future__ import annotations

from collections import deque
from typing import Deque, Iterable, List, Optional, Tuple, Union

Value = Union[float, int, bool, str, Tuple[float, ...]]
Sample = Tuple[float, Value]


class EnoSignal:
    def __init__(self, name: str, *, hint: Optional[str] = None, capacity: int = 4096):
        from ..idea.envelope import IdeaEnvelope  # local import: envelope needs no EnoSignal

        self.name = name
        self.hint = hint  # optional announcement from the source, e.g. "C", "bool"
        self.buf: Deque[Sample] = deque(maxlen=capacity)
        self.env = IdeaEnvelope()

    def push(self, t: float, v: Value) -> None:
        if isinstance(v, list):
            v = tuple(v)
        self.buf.append((t, v))
        self.env.update(t, v, self.buf)

    def extend(self, samples: Iterable[Sample]) -> None:
        for t, v in samples:
            self.push(t, v)

    def window(self, seconds: float, now: Optional[float] = None) -> List[Sample]:
        if not self.buf:
            return []
        end = self.buf[-1][0] if now is None else now
        lo = end - seconds
        return [s for s in self.buf if s[0] >= lo]

    def __len__(self) -> int:
        return len(self.buf)
