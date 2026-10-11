"""
Utility stuff

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""

import datetime
import functools
import inspect
import logging
import os
import random
import sys
import traceback
from decimal import Decimal
from types import MemberDescriptorType
from typing import List, Tuple, Dict, Union, Sequence, Any, Callable, Iterable, Type, Set, Optional

from . import lang, mud_context
from .errors import ParseError, ActionRefused, TaleError
from .story import MoneyType


def roll_dice(number: int=1, sides: int=6) -> Tuple[int, List[int]]:
    """rolls a number (max 300) of dice with configurable number of sides"""
    assert 1 <= number <= 300
    values = [random.randint(1, sides) for _ in range(number)]
    return sum(values), values


class MoneyFormatter:
    """Display and parsing of money. Supports 'fantasy' and 'modern' style money."""
    money_words = set()    # type: Set[str]
    money_name = ""
    smallest_amount = Decimal("1")

    @staticmethod
    def create_for(money_type: MoneyType) -> 'MoneyFormatter':
        if money_type == MoneyType.FANTASY:
            return MoneyFormatterFantasy()
        elif money_type == MoneyType.MODERN:
            return MoneyFormatterModern()
        else:
            raise ValueError("invalid money type " + str(money_type))

    def roundoff(self, amount: float) -> float:
        # make sure a floating point amount is rounded off to the correct maximum number of digits for this money type
        return round(amount, abs(self.smallest_amount.as_tuple().exponent))

    def parse(self, words: Sequence[str]) -> float:
        """Convert a parsed sequence of words to the amount of money it represents (float)"""
        if len(words) == 1:
            try:
                return self.to_float(words[0])
            except ValueError:
                pass
        elif len(words) == 2:
            try:
                return self.to_float(words[0] + words[1])
            except ValueError:
                pass
        coins = {}  # type: Dict[str, float]
        if set(words) & self.money_words:
            # check if all words are either a number (currency) or a money word
            amount = None
            for word in words:
                if word in self.money_words:
                    if amount:
                        if word in coins:
                            raise ParseError("What amount?")
                        coins[word] = amount
                        amount = None
                    else:
                        raise ParseError("What amount?")
                else:
                    try:
                        amount = float(word)
                    except ValueError:
                        raise ParseError("What amount?")
            return self.to_float(coins)
        raise ParseError("That is not an amount of money.")

    def display(self, amount: float, short: bool=False, zero_msg: str="nothing") -> str:
        raise NotImplementedError("use subclass")

    def to_float(self, coins: Union[str, Dict[str, float]]) -> float:
        raise NotImplementedError("use subclass")


class MoneyFormatterModern(MoneyFormatter):
    money_words = {"dollar", "dollars", "cent", "cents"}
    money_name = "money"
    smallest_amount = Decimal("0.01")  # 1 dollarcent

    def display(self, amount: float, short: bool=False, zero_msg: str="nothing") -> str:
        """
        Display amount of money in modern currency (dollars/cents).
        """
        if short:
            return "$ %.2f" % amount
        dollar, cents = divmod(amount, 1.0)
        cents = round(cents * 100.0)
        result = []
        if dollar:
            result.append("%d " % dollar + lang.pluralize("dollar", dollar))
        if cents:
            result.append("%d " % cents + lang.pluralize("cent", cents))
        if result:
            return lang.join(result)
        return zero_msg

    def to_float(self, coins: Union[str, Dict[str, float]]) -> float:
        """Either a dictionary containing the values per coin type, or a string '$1234.55' is converted to float."""
        if isinstance(coins, str):
            if coins.startswith("$"):
                return self.roundoff(float(coins[1:]))
            else:
                raise ValueError("That's not an amount of money.")
        result = coins.get("dollar", 0.0)
        result += coins.get("dollars", 0.0)
        result += coins.get("cent", 0.0) / 100.0
        result += coins.get("cents", 0.0) / 100.0
        return self.roundoff(result)


class MoneyFormatterFantasy(MoneyFormatter):
    money_words = {"gold", "silver", "copper", "coppers"}
    money_name = "coins"
    smallest_amount = Decimal("0.01")  # 1 copper (1/100th of 1 gold)

    def display(self, amount: float, short: bool=False, zero_msg: str="nothing") -> str:
        """
        Display amount of money in gold/silver/copper units,
        base unit=1 gold, 10 silver=1 gold, 10 copper=1 silver
        """
        gold, amount = divmod(amount, 1.0)
        silver, copper = divmod(amount, 0.1)
        copper = round(copper * 100.0)
        if short:
            return "%dg/%ds/%dc" % (gold, silver, copper)
        result = []
        if gold:
            result.append("%d gold" % gold)
        if silver:
            result.append("%d silver" % silver)
        if copper:
            result.append("%d copper" % copper)
        if result:
            return lang.join(result)
        return zero_msg

    def to_float(self, coins: Union[str, Dict[str, float]]) -> float:
        """Either a dictionary containing the values per coin type, or a string '11g/22s/33c' is converted to float."""
        if isinstance(coins, str):
            if not coins:
                raise ValueError("That's not an amount of money.")
            result = 0.0
            while coins:
                c, _, coins = coins.partition("/")
                try:
                    if c.endswith("g"):
                        result += float(c[:-1])
                    elif c.endswith("s"):
                        result += float(c[:-1]) / 10.0
                    elif c.endswith("c"):
                        result += float(c[:-1]) / 100.0
                    else:
                        raise ValueError("invalid coin letter")
                except ValueError:
                    raise ValueError("That's not an amount of money.")
            return self.roundoff(result)
        result = coins.get("gold", 0.0)
        result += coins.get("silver", 0.0) / 10.0
        result += coins.get("copper", 0.0) / 100.0
        result += coins.get("coppers", 0.0) / 100.0
        return self.roundoff(result)


def parse_time(args: Sequence[str]) -> datetime.time:
    """parses a time from args like: 13:44:59, or like a duration such as 1h 30m 15s"""
    try:
        duration = parse_duration(args)
        return (datetime.datetime.min + duration).time()
    except ParseError:
        if not args or len(args) > 1:
            raise ParseError("It's not clear what time you mean.")
        try:
            return datetime.datetime.strptime(args[0], "%H:%M:%S").time()
        except ValueError:
            try:
                return datetime.datetime.strptime(args[0], "%H:%M").time()
            except ValueError:
                if args[0] == "noon":
                    return datetime.time(hour=12)
                elif args[0] == "midnight":
                    return datetime.time(hour=0)
                elif args[0] in ("sunrise", "dawn"):
                    return datetime.time(hour=6)
                elif args[0] in ("sunset", "dusk"):
                    return datetime.time(hour=20)
                elif args[0] in ("evening", "morning", "later", "earlier", "future", "past"):
                    raise ParseError("You must be more specific about the time you mean.")
                else:
                    raise ParseError("It's not clear what time you mean.")


def parse_duration(args: Sequence[str]) -> datetime.timedelta:
    """parses a duration from args like: 1 hour 20 minutes 15 seconds (hour/h, minutes/min/m, seconds/sec/s)"""
    hours = minutes = seconds = 0.0
    if args:
        number = 0.0
        for arg in args:
            if len(arg) >= 2 and arg.endswith(("h", "m", "s")):
                try:
                    if arg[-1] == "h":
                        hours = int(arg[:-1])
                    elif arg[-1] == "m":
                        minutes = int(arg[:-1])
                    elif arg[-1] == "s":
                        seconds = int(arg[:-1])
                    continue
                except ValueError:
                    pass
            if arg in ("hours", "hour", "h"):
                hours = number
                number = 0.0
            elif arg in ("minutes", "minute", "min", "m"):
                minutes = number
                number = 0.0
            elif arg in ("seconds", "second", "sec", "s"):
                seconds = number
                number = 0.0
            else:
                try:
                    number = float(arg)
                except ValueError:
                    raise ParseError("It's not clear what duration you mean.")
    if hours == minutes == seconds == 0:
        raise ParseError("It's not clear what duration you mean.")
    try:
        return datetime.timedelta(hours=hours, minutes=minutes, seconds=seconds)
    except TypeError:
        raise ParseError("It's not clear what duration you mean.")


def duration_display(duration: datetime.timedelta) -> str:
    secs = duration.total_seconds()
    if secs == 0:
        return "no time at all"
    hours, secs = divmod(secs, 3600)
    minutes, secs = divmod(secs, 60)
    result = []
    if hours == 1:
        result.append("1 hour")
    elif hours > 1:
        result.append("%d hours" % hours)
    if minutes == 1:
        result.append("1 minute")
    elif minutes > 1:
        result.append("%d minutes" % minutes)
    if secs == 1:
        result.append("1 second")
    elif secs > 1:
        result.append("%d seconds" % secs)
    return lang.join(result)


def format_docstring(docstring: str) -> str:
    """Format a docstring according to the algorithm in PEP-257"""
    if not docstring:
        return ''
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxsize
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxsize:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return a single string:
    return '\n'.join(trimmed)


def storyname_to_filename(name: str) -> str:
    """converts the story name to a suitable name for a file on disk"""
    filename = name.lower()
    filename = filename.replace(" ", "_")
    filename = filename.replace(".", "_")
    filename = filename.replace("'", "")
    filename = filename.replace('"', "")
    filename = filename.replace("\\", "")
    filename = filename.replace("/", "")
    filename = filename.replace("*", "")
    return filename


class GameDateTime:
    """
    The datetime class that tracks game time.
    times_realtime means how much faster the game time is running than real time.
    The internal 'clock' tracks the time in game-time (not real-time).
    """
    def __init__(self, date_time: datetime.datetime, times_realtime: float=1) -> None:
        assert times_realtime >= 0
        self.times_realtime = times_realtime
        self.clock = date_time

    def __str__(self) -> str:
        return str(self.clock)

    def add_gametime(self, timedelta: datetime.timedelta) -> None:
        """advance the game clock by a time delta expressed in game time"""
        assert isinstance(timedelta, datetime.timedelta)
        self.clock += timedelta

    def sub_gametime(self, timedelta: datetime.timedelta) -> None:
        """rewind the game clock by a time delta expressed in game time"""
        assert isinstance(timedelta, datetime.timedelta)
        self.clock -= timedelta

    def plus_realtime(self, timedelta: datetime.timedelta) -> datetime.datetime:
        """return the game clock plus a time delta expressed in real time"""
        assert isinstance(timedelta, datetime.timedelta)
        return self.clock + timedelta * self.times_realtime

    def minus_realtime(self, timedelta: datetime.timedelta) -> datetime.datetime:
        """return the game clock minus a time delta expressed in real time"""
        assert isinstance(timedelta, datetime.timedelta)
        return self.clock - timedelta * self.times_realtime

    def add_realtime(self, timedelta: datetime.timedelta) -> None:
        """advance the game clock by a time delta expressed in real time"""
        assert isinstance(timedelta, datetime.timedelta)
        self.clock += timedelta * self.times_realtime

    def sub_realtime(self, timedelta: datetime.timedelta) -> None:
        """rewind the game clock by a time delta expressed in real time"""
        assert isinstance(timedelta, datetime.timedelta)
        self.clock -= timedelta * self.times_realtime


class Context:
    """
    A new instance of this context is passed to every command function and obj.destroy.
    Note that the player object isn't in here because it is already explicitly passed to these functions.
    """
    def __init__(self, driver: Any, clock: GameDateTime, config: Any, player_connection: Any) -> None:
        self.driver = driver
        self.clock = clock
        self.config = config
        self.conn = player_connection
        self.resources = driver.resources

    def __eq__(self, other: Any) -> bool:
        return vars(self) == vars(other)

    def __getstate__(self):
        raise RuntimeError("cannot serialize context - if you see this, some other object likely has a ref to us")

    @classmethod
    def from_global(cls, player_connection=None) -> 'Context':
        """
        Create a Context based on the current global mud_context
        Should only be used to (re)create a ctx where one is required,
        and you don't have a ctx argument provided already.
        """
        return cls(driver=mud_context.driver, clock=mud_context.driver.game_clock,
                   config=mud_context.config, player_connection=player_connection)


def authorized(*privileges: Sequence[str]) -> Callable:
    """
    Decorator for callables that need a privilege check.
    The callable should have an 'actor' argument that is passed an
    appropriate actor object with .privileges to check against.
    If they don't match with the privileges given in this decorator,
    an ActionRefused error is raised.
    """
    def checked(f):
        if "actor" not in inspect.signature(f).parameters:
            raise TaleError("callable requires 'actor' parameter: " + f.__name__)
        allowed_privs = set(privileges)

        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            # check if the supplied actor
            actor = inspect.getcallargs(f, *args, **kwargs)["actor"]
            try:
                if actor and allowed_privs & actor.privileges:
                    return f(*args, **kwargs)
            except AttributeError:
                # actors without .privileges, are also not allowed to do anything
                pass
            raise ActionRefused("You're not allowed to do that.")
        return wrapped
    if not privileges:
        raise ValueError("privileges must contain at least one value")
    return checked


def sorted_by_name(stuff: Iterable[Any]) -> Iterable[Any]:
    """Returns the objects sorted by their name attribute (case insensitive)"""
    return sorted(stuff, key=lambda thing: thing.name.lower())


def sorted_by_title(stuff: Iterable[Any]) -> Iterable[Any]:
    """Returns the objects sorted by their title attribute (case insensitive)"""
    return sorted(stuff, key=lambda thing: thing.title.lower())


def format_traceback(ex_type: Type=None, ex_value: Any=None, ex_tb: Any=None, detailed: bool=True, with_self: bool=False) -> List[str]:
    """Formats an exception traceback. If you ask for detailed formatting,
    the result will contain info on the variables in each stack frame.
    You don't have to provide the exception info objects, if you omit them,
    this function will obtain them itself using ``sys.exc_info()``."""
    if ex_type is not None and ex_value is None and ex_tb is None:
        # possible old (3.x) call syntax where caller is only providing exception object
        if type(ex_type) is not type:
            raise TypeError("invalid argument: ex_type should be an exception type, or just supply no arguments at all")
    width = 55
    result = ["\n\n", "-" * width + "\n", " CRASH OCCURRED! TIMESTAMP: %s\n" % datetime.datetime.now()]
    if ex_type is None and ex_tb is None:
        ex_type, ex_value, ex_tb = sys.exc_info()
    if detailed:
        def makestrvalue(value: Any) -> str:
            try:
                sval = repr(value)
            except:
                try:
                    sval = str(value)
                except:
                    return "<ERROR>"
            if len(sval) > 250:
                return sval[:250] + "   ...(truncated to 250)"
            return sval

        import linecache
        try:
            result.append("-" * width + "\n")
            if ex_type is None:
                result.append(" EXCEPTION: ???\n")
            else:
                result.append(" EXCEPTION: %s\n" % ex_type.__name__)
            result.append(" MESSAGE: %s\n" % ex_value)
            result.append(" Extended stacktrace follows (most recent call last):\n")
            skiplocals = True  # don't print the locals of the very first stack frame
            while ex_tb:
                frame = ex_tb.tb_frame
                sourcefilename = frame.f_code.co_filename
                if "self" in frame.f_locals:
                    location = "%s.%s" % (frame.f_locals["self"].__class__.__name__, frame.f_code.co_name)
                else:
                    location = frame.f_code.co_name
                result.append("   ----\n\n")
                result.append("File \"%s\", line %d, in %s\n" % (sourcefilename, ex_tb.tb_lineno, location))
                result.append("Source code:\n")
                result.append("    " + linecache.getline(sourcefilename, ex_tb.tb_lineno).strip() + "\n\n")
                if not skiplocals:
                    names = set()  # type: Set[str]
                    names.update(getattr(frame.f_code, "co_varnames", ()))
                    names.update(getattr(frame.f_code, "co_names", ()))
                    names.update(getattr(frame.f_code, "co_cellvars", ()))
                    names.update(getattr(frame.f_code, "co_freevars", ()))
                    result.append("Local values:\n")
                    for name2 in sorted(names):
                        if name2 in frame.f_locals:
                            value = frame.f_locals[name2]
                            result.append("    %s = %s\n" % (name2, makestrvalue(value)))
                            if name2 == "self" and with_self:
                                # print the local variables of the class instance
                                for name3, value in vars(value).items():
                                    result.append("        self.%s = %s\n" % (name3, makestrvalue(value)))
                skiplocals = False
                ex_tb = ex_tb.tb_next
            if ex_type is None:
                result.append("\n EXCEPTION HERE: ???: %s\n" % ex_value)
            else:
                result.append("\n EXCEPTION HERE: %s: %s\n" % (ex_type.__name__, ex_value))
            result.append("-" * width + "\n")
            return result
        except Exception:
            result.extend(["-" * width + "\nError building extended traceback!!! :\n",
                           "".join(traceback.format_exception(*sys.exc_info())) + '-' * width + '\n',
                           "Original Exception follows:\n",
                           "".join(traceback.format_exception(ex_type, ex_value, ex_tb))])
            return result
    else:
        # default traceback format.
        result.extend(traceback.format_exception(ex_type, ex_value, ex_tb))
        result.append("-" * width + "\n")
        return result


# Where crash/exception tracebacks are appended, instead of being dumped into the
# game window or console.
CRASH_LOG_FILENAME = "tale_crash.log"

_crash_logger: Optional[logging.Logger] = None


def _get_crash_logger() -> logging.Logger:
    """Return a module-level logger that appends crash tracebacks to a file."""
    global _crash_logger
    if _crash_logger is None:
        logger = logging.getLogger("tale.crash")
        if not len(logger.handlers):
            logger.setLevel(logging.INFO)
            try:
                handler = logging.FileHandler(os.path.join(os.getcwd(), CRASH_LOG_FILENAME), encoding="utf-8")
            except OSError:
                handler = logging.NullHandler()   # if we can't write a file, don't crash the reporter
            handler.setFormatter(logging.Formatter("%(asctime)s\n%(message)s"))
            logger.addHandler(handler)
            logger.propagate = False
        _crash_logger = logger
    return _crash_logger


def log_crash() -> str:
    """Append the traceback of the currently handled exception to the crash log file.

    Returns the formatted traceback string, so callers can refer to it (or show a
    short message) without re-formatting. Call this from within an ``except`` block.
    """
    ex_type, ex_value, ex_tb = sys.exc_info()
    text = "".join(format_traceback(ex_type, ex_value, ex_tb, detailed=True, with_self=False))
    name = ex_type.__name__ if ex_type is not None else "Unknown exception"
    _get_crash_logger().error("CRASH: %s: %s\n%s", name, ex_value, text)
    return text


def crash_report_message() -> str:
    """Short, player-facing message to show when a crash has been written to the log."""
    return "<rev><it>The details have been written to '%s'. Please report this problem.</>" % CRASH_LOG_FILENAME


def excepthook(ex_type, ex_value, ex_tb):
    """An exception hook you can use for ``sys.excepthook``, to write detailed tracebacks to the crash log"""
    name = ex_type.__name__ if ex_type is not None else "Unknown exception"
    _get_crash_logger().error("UNCAUGHT EXCEPTION: %s: %s\n%s",
                              name, ex_value, "".join(format_traceback(ex_type, ex_value, ex_tb, detailed=True, with_self=False)))
    sys.stderr.write("\n* Uncaught %s: %s. See %s for details.\n" % (name, ex_value, CRASH_LOG_FILENAME))


def call_periodically(period: float, max_period: float=None):
    """
    Decorator to mark a method of a MudObject class to be invoked periodically by the driver.
    You can set a fixed period (in real-time seconds) or a period interval in which a random
    next occurrence is then chosen for every call.
    Setting the period to 0 or None will stop the periodical calls.
    The method is called with a 'ctx' keyword argument set to a Context object.
    """
    def mark(func):
        if not period:
            func._tale_periodically = None
        else:
            initial = random.uniform(0.1, period)  # scatter initial calls
            func._tale_periodically = (initial, period, max_period or period)
        return func

    return mark


@functools.lru_cache()
def _periodicals_from_class(klass: type) -> Dict[MemberDescriptorType, Tuple[float, float, float]]:
    members = inspect.getmembers(klass, predicate=lambda x: inspect.ismethod(x) or inspect.isfunction(x))
    periodicals = {}
    for name, member in members:
        period = getattr(member, "_tale_periodically", 0.0)
        if period:
            periodicals[member] = period
    return periodicals


def get_periodicals(obj: Any) -> Dict[Callable, Tuple[float, float, float]]:
    """Get the (bound) member functions that are declared periodical via the @call_periodically decorator"""
    return {unbound.__get__(obj): period for unbound, period in _periodicals_from_class(type(obj)).items()}
