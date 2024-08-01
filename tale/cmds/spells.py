
import random
from typing import Optional
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

    if not skill.spell.check_cost(player, level):
        raise ActionRefused("You don't have enough magic points")
    
    num_args = len(parsed.args)
    if num_args < 1:
        raise ParseError("You need to specify who or what to heal")
    try:
        entity = str(parsed.args[0])
    except ValueError as x:
        raise ActionRefused(str(x))
    
    result = player.location.search_living(entity) # type: Optional[base.Living]
    if not result or not isinstance(result, base.Living):
        raise ActionRefused("Can't heal that")
    
    level = player.stats.level
    if num_args == 2:
        level = int(parsed.args[1])
    
    player.stats.magic_points -= skill.spell.base_cost * level

    if random.randint(1, 100) > skill.skill:
        player.tell("Your healing spell fizzles out", evoke=True)
        return

    result.stats.replenish_hp(5 * level)
    player.tell("You heal %s for %d hit points" % (result.name, 5 * level), evoke=True)
    player.tell_others("%s heals %s" % (player.name, result.name), evoke=True)


@cmd("bolt")
def do_bolt(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """ Cast a bolt of energy """

    skill = player.stats.magic_skills.get(MagicType.BOLT)   # type: MagicSkill
    if not skill:
        raise ActionRefused("You don't know how to cast a bolt")
    
    if not skill.spell.check_cost(player, level):
        raise ActionRefused("You don't have enough magic points")
    
    num_args = len(parsed.args)
    if num_args < 1:
        raise ParseError("You need to specify who or what to attack")
    
    try:
        entity = str(parsed.args[0])
    except ValueError as x:
        raise ActionRefused(str(x))
    
    result = player.location.search_living(entity) # type: Optional[base.Living]
    if not result or not isinstance(result, base.Living):
        raise ActionRefused("Can't attack that")
    
    level = player.stats.level
    if num_args == 2:
        level = int(parsed.args[1])

    
    player.stats.magic_points -= skill.spell.base_cost * level

    if random.randint(1, 100) > skill.skill:
        player.tell("Your bolt spell fizzles out", evoke=True)
        return

    hp = random.randrange(1, level)
    result.stats.hp -= hp
    player.tell("Your energy bolt hits %s for %d damage" % (result.name, hp), evoke=True)
    player.tell_others("%s's energy bolt hits %s for %d damage" % (player.name, result.name, hp), evoke=True)

@cmd("drain")
def do_drain(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """ Drain energy from someone or something """

    skill = player.stats.magic_skills.get(MagicType.DRAIN)
    if not skill:
        raise ActionRefused("You don't know how to drain")
    
    if not skill.spell.check_cost(player, level):
        raise ActionRefused("You don't have enough magic points")
    
    num_args = len(parsed.args)
    if num_args < 1:
        raise ParseError("You need to specify who or what to drain")
    
    try:
        entity = str(parsed.args[0])
    except ValueError as x:
        raise ActionRefused(str(x))
    
    result = player.location.search_living(entity) # type: Optional[base.Living]
    if not result or not isinstance(result, base.Living):
        raise ActionRefused("Can't drain that")
    
    level = player.stats.level
    if num_args == 2:
        level = int(parsed.args[1])
    
    
    player.stats.magic_points -= skill.spell.base_cost * level

    if random.randint(1, 100) > skill.skill:
        player.tell("Your drain spell fizzles out", evoke=True)
        return
    
    points = random.randrange(1, level)
    result.stats.combat_points -= points
    result.stats.magic_points -= points

    player.stats.magic_points += points

    player.tell("Your drain spell drains %s of %d combat and magic points" % (result.name, points), evoke=True)
    player.tell_others("%s casts a drain spell that drains energy from %s" % (player.name, result.name), evoke=True)
    

