"""SUFD: an interface that interprets any signal as a visual a human can follow.

Six keyword packages (see glossary.py): eno intake, emem baseline and noise, idea understanding,
akpaneka judgement and action, kufre self, edimek surface. The slice-1 names below are compatibility aliases.
"""
from .akpaneka.notes import AkpanekaFollower, AkpanekaNote, AkpanekaWatch
from .edimek.follow import EdimekFollow
from .edimek.lens import EdimekLens, edimek_choose_lens
from .edimek.render import edimek_render_svg
from .eno.signal import EnoSignal
from .idea.envelope import IdeaEnvelope
from .kufre.mind import KufreMind, KufreProbe, KufreSense

# slice-1 names (retire at the end of M4)
Envelope = IdeaEnvelope
Follow = EdimekFollow
Follower = AkpanekaFollower
Lens = EdimekLens
Mind = KufreMind
Note = AkpanekaNote
SelfProbe = KufreProbe
Signal = EnoSignal
Watch = AkpanekaWatch
choose_lens = edimek_choose_lens
render_svg = edimek_render_svg

__all__ = ["AkpanekaFollower", "AkpanekaNote", "AkpanekaWatch", "EdimekFollow", "EdimekLens", "EnoSignal",
           "IdeaEnvelope", "KufreMind", "KufreProbe", "KufreSense", "edimek_choose_lens", "edimek_render_svg",
           "Envelope", "Follow", "Follower", "Lens", "Mind", "Note", "SelfProbe", "Signal", "Watch",
           "choose_lens", "render_svg"]
