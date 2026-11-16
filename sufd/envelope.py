"""Compatibility shim: old import path for envelope. Retires at the end of M4."""
from .idea.envelope import *            # noqa: F401,F403
from .idea.envelope import (IdeaEnvelope, MAX_CATEGORIES, REFRESH, SURPRISE_CAP, WARMUP,
                            WINDOW, _median, _quantile)   # noqa: F401

Envelope = IdeaEnvelope
