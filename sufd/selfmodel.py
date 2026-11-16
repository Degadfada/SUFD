"""Compatibility shim: old import path for selfmodel. Retires at the end of M4."""
from .kufre.mind import NEEDS, KufreMind, KufreProbe, KufreSense   # noqa: F401

Mind = KufreMind
SenseRecord = KufreSense
SelfProbe = KufreProbe
