"""Compatibility shim: old import path for signal. Retires at the end of M4."""
from .eno.signal import EnoSignal, Sample, Value

Signal = EnoSignal
