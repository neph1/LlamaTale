"""
Player code

Snakepit mud driver and mudlib - Copyright by Irmen de Jong (irmen@razorvine.net)
"""

from __future__ import print_function, division
from . import base, soul
from . import lang
from .errors import SecurityViolation


class Player(base.Living):
    """
    Player controlled entity.
    Has a Soul for social interaction.
    """
    def __init__(self, name, gender, race="human", description=None):
        title = lang.capital(name)
        super(Player, self).__init__(name, gender, title, description, race)
        self.soul = soul.Soul()
        self.__output = []
        self.installed_wiretaps = set()

    def __repr__(self):
        return "<%s.%s '%s' @ 0x%x, privs:%s>" % (self.__class__.__module__, self.__class__.__name__,
            self.name, id(self), ",".join(self.privileges) or "-")

    def set_title(self, title, includes_name_param=False):
        if includes_name_param:
            self.title = title % lang.capital(self.name)
        else:
            self.title = title

    def parse(self, commandline):
        """Parse the commandline into something that can be processed by the soul (soul.ParseResult)"""
        return self.soul.parse(self, commandline)

    def socialize_parsed(self, parsed):
        """Don't re-parse the command string, but directly feed the parse results we've already got into the Soul"""
        return self.soul.process_verb_parsed(self, parsed)

    def tell(self, *messages):
        """
        A message sent to a player (or multiple messages). They are meant to be printed on the screen.
        For efficiency, messages are gathered in a buffer and printed later.
        Notice that the signature and behavior of this method resembles that of the print() function,
        which means you can easily do: print=player.tell, and use print(..) everywhere as usual.
        """
        super(Player, self).tell(*messages)
        self.__output.append(" ".join(str(msg) for msg in messages))
        self.__output.append("\n")

    def get_output_lines(self):
        """gets the accumulated output lines and clears the buffer"""
        lines = self.__output
        self.__output = []
        return lines

    def look(self, short=False):
        """look around in your surroundings (exclude player from livings)"""
        if self.location:
            look = self.location.look(exclude_living=self, short=short)
            if "wizard" in self.privileges:
                return repr(self.location) + "\n" + look
            return look
        else:
            return "You see nothing."

    def create_wiretap(self, target):
        if "wizard" not in self.privileges:
            raise SecurityViolation("wiretap requires wizard privilege")
        tap = Wiretap(self, target)
        self.installed_wiretaps.add(tap)  # hold on to the wiretap otherwise it's garbage collected immediately
        target.wiretaps.add(tap)  # install the wiretap on the target

    def destroy(self, ctx):
        super(Player, self).destroy(ctx)
        self.installed_wiretaps.clear()
        self.soul = None   # truly die ;-)
        # @todo: remove heartbeat, deferred, etc.


class Wiretap(object):
    """wiretap that can be installed on a location or a living, to tap into the messages they're receiving"""
    def __init__(self, observer, target):
        self.observer = observer
        self.target_name = target.name
        self.target_type = target.__class__.__name__

    def __str__(self):
        return "%s '%s'" % (self.target_type, self.target_name)

    def tell(self, *messages):
        for msg in messages:
            self.observer.tell("[wiretap on '%s': %s]" % (self.target_name, msg))
