
import random
from typing import Optional
from tale import base, util, cmds
from tale.skills import magic
from tale.cmds import cmd
from tale.errors import ActionRefused, ParseError
from tale.skills.magic import MagicType, MagicSkill, Spell
from tale.player import Player


@cmd("heal")
def do_heal(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """ Heal someone or something """

    skillValue = player.stats.magic_skills.get(MagicType.HEAL, None)
    if not skillValue:
        raise ActionRefused("You don't know how to heal")
    spell =  magic.spells[MagicType.HEAL] # type: Spell

    num_args = len(parsed.args)

    level = player.stats.level
    if num_args == 2:
        level = int(parsed.args[1])

    if not spell.check_cost(player.stats.magic_points, level):
        raise ActionRefused("You don't have enough magic points")
    
    if num_args < 1:
        raise ParseError("You need to specify who or what to heal")
    try:
        entity = str(parsed.args[0])
    except ValueError as x:
        raise ActionRefused(str(x))
    
    result = player.location.search_living(entity) # type: Optional[base.Living]
    if not result or not isinstance(result, base.Living):
        raise ActionRefused("Can't heal that")
    
    
    player.stats.magic_points -= spell.base_cost * level

    if random.randint(1, 100) > skillValue:
        player.tell("Your healing spell fizzles out", evoke=True, short_len=True)
        return

    result.stats.replenish_hp(5 * level)
    player.tell("You cast a healing spell that heals %s for %d hit points" % (result.name, 5 * level), evoke=True)
    player.tell_others("%s casts a healing spell that heals %s" % (player.name, result.name), evoke=True)


@cmd("bolt")
def do_bolt(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """ Cast a bolt of energy """

    skillValue = player.stats.magic_skills.get(MagicType.BOLT, None)
    if not skillValue:
        raise ActionRefused("You don't know how to cast a bolt")
    
    spell =  magic.spells[MagicType.BOLT] # type: Spell

    num_args = len(parsed.args)

    level = player.stats.level
    if num_args == 2:
        level = int(parsed.args[1])

    if not spell.check_cost(player.stats.magic_points, level):
        raise ActionRefused("You don't have enough magic points")
    
    if num_args < 1:
        raise ParseError("You need to specify who or what to attack")
    
    try:
        entity = str(parsed.args[0])
    except ValueError as x:
        raise ActionRefused(str(x))
    
    result = player.location.search_living(entity) # type: Optional[base.Living]
    if not result or not isinstance(result, base.Living):
        raise ActionRefused("Can't attack that")

    player.stats.magic_points -= spell.base_cost * level

    if random.randint(1, 100) > skillValue:
        player.tell("Your bolt spell fizzles out", evoke=True, short_len=True)
        return

    hp = random.randint(1, level)
    result.stats.hp -= hp
    player.tell("You cast an energy bolt that hits %s for %d damage" % (result.name, hp), evoke=True)
    player.tell_others("%s casts an energy bolt that hits %s for %d damage" % (player.name, result.name, hp), evoke=True)

@cmd("drain")
def do_drain(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """ Drain energy from someone or something """

    skillValue = player.stats.magic_skills.get(MagicType.DRAIN, None)
    if not skillValue:
        raise ActionRefused("You don't know how to drain")
    
    spell =  magic.spells[MagicType.DRAIN] # type: Spell

    num_args = len(parsed.args)

    level = player.stats.level
    if num_args == 2:
        level = int(parsed.args[1])
    
    if not spell.check_cost(player.stats.magic_points, level):
        raise ActionRefused("You don't have enough magic points")
    
    if num_args < 1:
        raise ParseError("You need to specify who or what to drain")
    
    try:
        entity = str(parsed.args[0])
    except ValueError as x:
        raise ActionRefused(str(x))
    
    result = player.location.search_living(entity) # type: Optional[base.Living]
    if not result or not isinstance(result, base.Living):
        raise ActionRefused("Can't drain that")
    
    player.stats.magic_points -= spell.base_cost * level

    if random.randint(1, 100) > skillValue:
        player.tell("Your drain spell fizzles out", evoke=True, short_len=True)
        return
    
    points = random.randint(1, level)
    result.stats.combat_points -= points
    result.stats.magic_points -= points

    player.stats.magic_points += points

    player.tell("You cast a 'drain' spell that drains %s of %d combat and magic points" % (result.name, points), evoke=True)
    player.tell_others("%s casts a 'drain' spell that drains energy from %s" % (player.name, result.name), evoke=True)
    

