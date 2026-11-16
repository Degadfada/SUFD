"""SUFD: an interface that interprets any signal as a visual a human can follow."""
from .envelope import Envelope
from .follow import Follow, Follower, Note, Watch
from .lens import Lens, choose_lens
from .render import render_svg
from .selfmodel import Mind, SelfProbe
from .signal import Signal

__all__ = ["Envelope", "Follow", "Follower", "Note", "Watch", "Lens", "choose_lens",
           "render_svg", "Mind", "SelfProbe", "Signal"]
