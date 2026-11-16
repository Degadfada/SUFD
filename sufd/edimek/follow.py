"""edimek — surface. Follow: the shared attention between SUFD and the human on one signal.

SUFD's side is a 'now' cursor and Notes (every note carries its reason). The human's side is a pointer at a
time; SUFD answers a pointer from the envelope. `explain` logic still lives on the follower (it needs the
confirmed baseline); `edimek_explain` is the surface-side entry point, so the surface does not reach into
judgement internals.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from ..akpaneka.notes import AkpanekaNote


@dataclass
class EdimekFollow:
    """What the two parties share about one signal right now."""
    notes: List[AkpanekaNote] = field(default_factory=list)
    human_t: Optional[float] = None


def edimek_explain(follower, t: float) -> str:
    """Answer the human pointing at time t, from the envelope. No language model."""
    return follower.explain(t)
