"""
Global context object (thread-safe) for the server

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""

from __future__ import print_function, division, unicode_literals
import threading

_threadlocal = threading.local()


class __MudContextProxy(object):
    def __getattr__(self, item):
        ctx = getattr(_threadlocal, "mud_context", None)
        if ctx is None:
            ctx = _threadlocal.mud_context = {}
        return ctx.get(item)

    def __setattr__(self, key, value):
        ctx = getattr(_threadlocal, "mud_context", None)
        if ctx is None:
            ctx = _threadlocal.mud_context = {}
        ctx[key] = value


mud_context = __MudContextProxy()