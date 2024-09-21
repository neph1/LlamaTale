"""
Package for all mud commands (non-soul)

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""

import functools
import inspect
from typing import Dict, Callable, Tuple, Generator, Iterable, Optional
from ..player import Player
from ..story import GameMode
from ..base import ParseResult
from .. import util, errors


__all__ = ["cmd", "wizcmd", "disable_notify_action", "disabled_in_gamemode", "overrides_soul", "no_soul_parse"]


abbreviations = {
    "n": "north",
    "e": "east",
    "s": "south",
    "w": "west",
    "ne": "northeast",
    "nw": "northwest",
    "se": "southeast",
    "sw": "southwest",
    "u": "up",
    "d": "down",
    "?": "help",
    "i": "inventory",
    "l": "look",
    "x": "examine",
    "exa": "examine",
    "inv": "inventory",
    "'": "say"
}


# these will be filled by the @cmd and @wizcmd decorators when used
_all_commands = {}   # type: Dict[str, Callable]
_all_wizard_commands = {}   # type: Dict[str, Callable]
cmds_aliases = {}   # type: Dict[str, Tuple[str, ...]]  # commands -> tuple of one or more aliases


def all_registered_commands() -> Iterable[Tuple[str, Callable, str]]:
    """
    Produce all registered commands so they could be added to the command processor.
    (This is called from the game driver when it is starting up)
    Note that we are relying on the command function to add itself (via the @cmd decorator)
    to the collection above. This way you can define commands anywhere without this
    code having to know that modules to scan. This is required for user story packages!
    """
    from . import wizard
    from . import normal
    from . import spells
    for command, func in _all_wizard_commands.items():
        yield command, func, "wizard"
    for command, func in _all_commands.items():
        yield command, func, ""


def clear_registered_commands():
    # needed so a story can register its own additional commands afterwards
    _all_commands.clear()
    _all_wizard_commands.clear()


def cmd(command: str, *aliases: str) -> Callable:
    """
    Decorator to define a parser command function and its verb(s).
    """
    if not isinstance(command, str) or any(not isinstance(alias, str) for alias in aliases):
        raise TypeError("command name and aliases should be provided as string arguments")

    def cmd2(func: Callable) -> Callable:
        if command in _all_commands:
            raise ValueError("command defined more than once: " + command)
        func.is_generator = inspect.isgeneratorfunction(func)   # type: ignore   # contains async yields?
        if cmdfunc_signature_valid(func):
            func.__doc__ = util.format_docstring(func.__doc__ or "") or None
            func.is_tale_command_func = True     # type: ignore
            if not hasattr(func, "enable_notify_action"):
                func.enable_notify_action = True   # type: ignore   # by default the normal commands should be passed to notify_action
            _all_commands[command] = func
            cmds_aliases[command] = aliases
            for alias in aliases:
                if alias in _all_commands:
                    raise ValueError("command defined more than once: " + alias)
                _all_commands[alias] = func
            return func
        else:
            raise errors.TaleError("invalid cmd function signature or missing docstring: " + func.__name__)
    return cmd2


def wizcmd(command: str, *aliases: str) -> Callable:
    """
    Decorator to define a 'wizard' command function and verb.
    It will add a privilege check wrapper.
    Note that the wizard command (and the aliases) are prefixed by a '!' to make them stand out from normal commands.
    """
    if not isinstance(command, str) or any(not isinstance(alias, str) for alias in aliases):
        raise TypeError("command name and aliases should be provided as string arguments")
    prefixed_command = "!" + command
    prefixed_aliases = ["!" + alias for alias in aliases]

    def wizcmd2(func: Callable) -> Callable:
        func.enable_notify_action = False   # type: ignore # none of the wizard commands should be used with notify_action
        func.is_tale_command_func = True    # type: ignore
        func.is_generator = inspect.isgeneratorfunction(func)   # type: ignore   # contains async yields?

        @functools.wraps(func)
        def executewizcommand(player: Player, parsed: ParseResult, ctx: util.Context) \
                -> Callable[[Player, ParseResult, util.Context], None]:
            if "wizard" not in player.privileges:
                raise errors.SecurityViolation("Wizard privilege required for verb " + parsed.verb)
            return func(player, parsed, ctx)

        if prefixed_command in _all_commands:
            raise ValueError("Command defined more than once: " + prefixed_command)
        if cmdfunc_signature_valid(func):
            func.__doc__ = util.format_docstring(func.__doc__ or "") or None
            executewizcommand.__doc__ = func.__doc__
            _all_wizard_commands[prefixed_command] = executewizcommand
            for alias in prefixed_aliases:
                if alias in _all_wizard_commands:
                    raise ValueError("Command defined more than once: " + alias)
                _all_wizard_commands[alias] = executewizcommand
            return executewizcommand
        else:
            raise errors.TaleError("invalid wizcmd function signature or missing docstring: " + func.__name__)
    return wizcmd2


def cmdfunc_signature_valid(func: Callable) -> bool:
    # the signature of a command function must be exactly this:  def func(player, parsed, ctx) -> None
    # and it must have a docstring comment.
    if not func.__doc__:
        return False
    sig = inspect.signature(func)
    is_generator = inspect.isgeneratorfunction(func)
    if is_generator and sig.return_annotation is not Generator:
        return False
    elif not is_generator and sig.return_annotation not in [sig.empty, None]:
        return False
    expected_params = ["player", "parsed", "ctx"]
    if list(sig.parameters) != expected_params:
        print("params err")
        return False
    # if there is type information, it should be correct
    ann = sig.parameters["player"].annotation
    if ann is not sig.empty and ann is not Player:
        return False
    ann = sig.parameters["parsed"].annotation
    if ann is not sig.empty and ann is not ParseResult:
        return False
    ann = sig.parameters["ctx"].annotation
    if ann is not sig.empty and ann is not util.Context:
        return False
    # check param types
    return all(sig.parameters[p].default is sig.empty and
               sig.parameters[p].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD for p in expected_params)


def disable_notify_action(func: Callable) -> Callable:
    """decorator to prevent the command being passed to notify_action events"""
    func.enable_notify_action = False       # type: ignore
    return func


def disabled_in_gamemode(mode: GameMode) -> Callable:
    """decorator to disable a command in the given game mode"""
    def disable(func: Callable) -> Callable:
        func.disabled_in_mode = mode        # type: ignore
        return func
    assert isinstance(mode, GameMode)
    return disable


def overrides_soul(func: Callable) -> Callable:
    """decorator to let the command override (hide) the corresponding soul command"""
    func.overrides_soul = True      # type: ignore
    return func


def no_soul_parse(func: Callable) -> Callable:
    """decorator to tell the command processor to skip the soul parse step and just treat the whole input as plain string"""
    func.no_soul_parse = True       # type: ignore
    return func
