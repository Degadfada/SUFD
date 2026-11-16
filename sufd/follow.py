"""Compatibility shim: old import path for follow. Retires at the end of M4."""
from .akpaneka.notes import (DEBOUNCE, JUMP_AT, AkpanekaFollower, AkpanekaNote,   # noqa: F401
                             AkpanekaWatch)
from .edimek.follow import EdimekFollow

Note = AkpanekaNote
Follower = AkpanekaFollower
Watch = AkpanekaWatch
Follow = EdimekFollow
