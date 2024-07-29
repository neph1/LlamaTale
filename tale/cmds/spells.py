
import random
from tale import base, util, cmds
from tale.cmds import cmd
from tale.errors import ActionRefused, ParseError
from tale.magic import MagicType, MagicSkill
from tale.player import Player


@cmd("heal")
def do_heal(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """ Heal someone or something """

    skill = player.stats.magic_skills.get(MagicType.HEAL) # type: MagicSkill
    if not skill:
        raise ActionRefused("You don't know how to heal")
    
    num_args = len(parsed.args)
    if num_args < 1:
        raise ParseError("You need to specify who or what to heal")
    try:
        entity = str(parsed.args[0])
    except ValueError as x:
        raise ActionRefused(str(x))
    
    result = player.location.search_living(entity) # type: base.Living
    if not result or not isinstance(result, base.Living):
        raise ActionRefused("Can't heal that")
    
    level = player.stats.level
    if num_args == 2:
        level = int(parsed.args[1])

    if player.stats.magic_points < skill.spell.base_cost * level:
        raise ActionRefused("You don't have enough magic points")
    
    player.stats.magic_points -= skill.spell.base_cost * level

    if random.randint(1, 100) > skill.skill:
        player.tell("Your healing spell fizzles out", evoke=True)
        return

    result.stats.replenish_hp(5 * level)


@cmd("bolt")
def do_bolt(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """ Cast a bolt of energy """

    skill = player.stats.magic_skills.get(MagicType.BOLT)   # type: MagicSkill
    if not skill:
        raise ActionRefused("You don't know how to cast a bolt")
    
    num_args = len(parsed.args)
    if num_args < 1:
        raise ParseError("You need to specify who or what to attack")
    
    try:
        entity = str(parsed.args[0])
    except ValueError as x:
        raise ActionRefused(str(x))
    
    result = player.location.search_living(entity) # type: base.Living
    if not result or not isinstance(result, base.Living):
        raise ActionRefused("Can't attack that")
    
    level = player.stats.level
    if num_args == 2:
        level = int(parsed.args[1])

    if player.stats.magic_points < skill.spell.base_cost * level:
        raise ActionRefused("You don't have enough magic points")
    
    player.stats.magic_points -= skill.spell.base_cost * level

    if random.randint(1, 100) > skill.skill:
        player.tell("Your healing spell fizzles out", evoke=True)
        return

    result.stats.hp -= random.randrange(1, level)
