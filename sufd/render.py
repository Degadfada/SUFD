"""Compatibility shim: old import path for render. Retires at the end of M4."""
from .edimek.render import *             # noqa: F401,F403
from .edimek.render import edimek_render_svg

render_svg = edimek_render_svg
