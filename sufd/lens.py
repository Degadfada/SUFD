"""Compatibility shim: old import path for lens. Retires at the end of M4."""
from .edimek.lens import *               # noqa: F401,F403
from .edimek.lens import (EdimekAxis, EdimekLens, choose_window, decimate_minmax, edimek_choose_lens,
                          nice_num, nice_ticks)   # noqa: F401

Axis = EdimekAxis
Lens = EdimekLens
choose_lens = edimek_choose_lens
