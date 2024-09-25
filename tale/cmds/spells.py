
from typing import Optional
from tale import base, util
from tale.skills import spells
from tale.cmds import cmd
from tale.errors import ActionRefused
from tale.player import Player

not_enough_magic_points = "You don't have enough magic points"

@cmd("cast_heal")
def do_heal(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """ Heal someone or something """

    level = _parse_level(player, parsed)

    target = _parse_target(player, parsed) # type: base.Living
    
    spells.cast_heal(player, target, level)


@cmd("cast_bolt")
def do_bolt(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """ Cast a bolt of energy """

    level = _parse_level(player, parsed)

    result = _parse_target(player, parsed) # type: base.Living

    spells.cast_bolt(player, result, level)

@cmd("cast_drain")
def do_drain(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """ Drain energy from someone or something """

    level = _parse_level(player, parsed)
    
    result = _parse_target(player, parsed) # type: base.Living
    
    spells.cast_drain(player, result, level)
    

@cmd("cast_rejuvenate")
def do_rejuvenate(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """ Rejuvenate someone or something """

    level = _parse_level(player, parsed)

    result = _parse_target(player, parsed) # type: base.Living

    spells.cast_rejuvenate(player, result, level)


@cmd("cast_hide")
def do_hide(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """ Hide from view """

    level = _parse_level(player, parsed)

    result = _parse_target(player, parsed) # type: base.Living

    spells.cast_hide(player, result, level)

@cmd("cast_reveal")
def do_reveal(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """ Reveal hidden things. """

    level = _parse_level(player, parsed, 0)

    spells.cast_reveal(player, level)

def _parse_level(player: Player,parsed: base.ParseResult, arg_pos: int = 1) -> int:
    num_args = len(parsed.args)
    level = player.stats.level
    if num_args > arg_pos:
        level = int(parsed.args[arg_pos])
    return level

def _parse_target(player: Player, parsed: base.ParseResult) -> base.Living:
    num_args = len(parsed.args)
    if num_args < 1:
        raise ActionRefused("You need to specify who or what to target")
    
    try:
        entity = str(parsed.args[0])
    except ValueError as x:
        raise ActionRefused(str(x))
    
    if entity.lower() == "self" or entity.lower() == "me":
        return player
    
    result = player.location.search_living(entity) # type: Optional[base.Living]
    if not result or not isinstance(result, base.Living):
        raise ActionRefused("Can't target that")
    
    return result
