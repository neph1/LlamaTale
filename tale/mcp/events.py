"""
Story event ring buffer for polling the live world (Stage 2).

A :class:`StoryEvents` listener subscribes to the ``wiretap`` pubsub topics of
every known location, NPC and player. Each wiretap carries the structured
messages the LLM reasons over: ``Location.tell`` sends
``("wiretap-location", "<name>#<vnum>")`` with a ``(name, message)`` event, and
``Living.tell`` does the same on ``("wiretap-living", ...)``.

Events are buffered in a bounded ring buffer with a monotonically increasing
sequence number, so an agent can poll them with ``since(cursor)`` without
missing anything (and without being re-sent what it already saw).

'Tale' mud driver, mudlib and interactive fiction framework
"""

import collections
import threading
import time

from tale import pubsub

__all__ = ["StoryEvents"]


class StoryEvents(pubsub.Listener):
    """Captures wiretap messages into a bounded ring buffer for polling.

    Subclass of :class:`tale.pubsub.Listener`: it is meant to be subscribed to
    wiretap topics. Only wiretap topics are recorded; everything else is
    ignored so the listener can be attached anywhere without side effects.
    """

    def __init__(self, maxlen: int = 500) -> None:
        self._buffer = collections.deque(maxlen=maxlen)
        self._cursor = 0  # monotonically increasing sequence number
        self._lock = threading.Lock()

    def pubsub_event(self, topicname, event) -> None:
        """Record a wiretap event (``event = (name, message)``) into the ring buffer."""
        # only capture wiretap topics; the topic name is ("wiretap-location"/"wiretap-living", "<name>#<vnum>")
        if not (isinstance(topicname, tuple) and len(topicname) >= 2 and topicname[0].startswith("wiretap-")):
            return
        source, message = event
        with self._lock:
            self._cursor += 1
            self._buffer.append({
                "index": self._cursor,
                "time": time.time(),
                "kind": topicname[0],   # "wiretap-location" | "wiretap-living"
                "source": source,
                "text": message,
            })

    def since(self, cursor: int = 0) -> list:
        """All records with ``index > cursor`` (newest last).

        Records that have been pushed out of the ring buffer are gone; an agent
        that has not polled in time may see gaps in the index sequence.
        """
        with self._lock:
            return [record for record in self._buffer if record["index"] > cursor]

    @property
    def cursor(self) -> int:
        """The index of the most recently recorded event (0 if none yet)."""
        with self._lock:
            return self._cursor
