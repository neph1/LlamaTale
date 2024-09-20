
import random
from typing import Optional
from tale import base, util, cmds
from tale.skills import magic
from tale.cmds import cmd
from tale.errors import ActionRefused, ParseError
from tale.skills.magic import MagicType, MagicSkill, Spell
from tale.player import Player
from tale.skills.skills import SkillType

not_enough_magic_points = "You don't have enough magic points"

@cmd("cast_heal")
def do_heal(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """ Heal someone or something """

    skillValue, spell = _check_spell_skill(player, MagicType.HEAL, "You don't know how to heal")
    level = _parse_level(player, parsed)

    if not spell.check_cost(player.stats.magic_points, level):
        raise ActionRefused(not_enough_magic_points)
    
    result = _parse_target(player, parsed) # type: base.Living
    
    player.stats.magic_points -= spell.base_cost * level

    if random.randint(1, 100) > skillValue:
        player.tell("Your healing spell fizzles out", evoke=True, short_len=True)
        return

    result.stats.replenish_hp(5 * level)
    player.tell("You cast a healing spell that heals %s for %d hit points" % (result.name, 5 * level), evoke=True)
    player.tell_others("%s casts a healing spell on %s" % (player.name, result.name), evoke=True)


@cmd("cast_bolt")
def do_bolt(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """ Cast a bolt of energy """

    skillValue, spell = _check_spell_skill(player, MagicType.BOLT, "You don't know how to cast a bolt")
    level = _parse_level(player, parsed)

    if not spell.check_cost(player.stats.magic_points, level):
        raise ActionRefused(not_enough_magic_points)
    
    result = _parse_target(player, parsed) # type: base.Living

    player.stats.magic_points -= spell.base_cost * level

    if random.randint(1, 100) > skillValue:
        player.tell("Your bolt spell fizzles out", evoke=True, short_len=True)
        return

    hp = random.randint(1, level)
    result.stats.hp -= hp
    player.tell("You cast an energy bolt that hits %s for %d damage" % (result.name, hp), evoke=True)
    player.tell_others("%s casts an energy bolt that hits %s for %d damage" % (player.name, result.name, hp), evoke=True)

@cmd("cast_drain")
def do_drain(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """ Drain energy from someone or something """

    skillValue, spell = _check_spell_skill(player, MagicType.DRAIN, "You don't know how to drain")
    level = _parse_level(player, parsed)
    
    if not spell.check_cost(player.stats.magic_points, level):
        raise ActionRefused(not_enough_magic_points)
    
    result = _parse_target(player, parsed) # type: base.Living
    
    player.stats.magic_points -= spell.base_cost * level

    if random.randint(1, 100) > skillValue:
        player.tell("Your drain spell fizzles out", evoke=True, short_len=True)
        return
    
    points = random.randint(1, level)
    result.stats.action_points -= points
    result.stats.magic_points -= points

    player.stats.magic_points += points

    player.tell("You cast a 'drain' spell that drains %s of %d combat and magic points" % (result.name, points), evoke=True)
    player.tell_others("%s casts a 'drain' spell that drains energy from %s" % (player.name, result.name), evoke=True)
    

@cmd("cast_rejuvenate")
def do_rejuvenate(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """ Rejuvenate someone or something """

    skillValue, spell = _check_spell_skill(player, MagicType.REJUVENATE, "You don't know how to rejuvenate")
    level = _parse_level(player, parsed)

    if not spell.check_cost(player.stats.magic_points, level):
        raise ActionRefused(not_enough_magic_points)
    
    result = _parse_target(player, parsed) # type: base.Living

    player.stats.magic_points -= spell.base_cost * level

    if random.randint(1, 100) > skillValue:
        player.tell("Your rejuvenate spell fizzles out", evoke=True, short_len=True)
        return

    result.stats.replenish_hp(5 * level)
    player.tell("You cast a rejuvenate spell that replenishes %s for %d action points" % (result.name, 5 * level), evoke=True)
    player.tell_others("%s casts a rejuvenate spell on %s" % (player.name, result.name), evoke=True)


@cmd("cast_hide")
def do_hide(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """ Hide from view """

    skillValue, spell = _check_spell_skill(player, MagicType.HIDE, "You don't know how the 'hide' spell.")
    level = _parse_level(player, parsed)

    if not spell.check_cost(player.stats.magic_points, level):
        raise ActionRefused(not_enough_magic_points)
    
    result = _parse_target(player, parsed) # type: base.Living
    
    player.stats.magic_points -= spell.base_cost * level

    if random.randint(1, 100) > skillValue:
        player.tell("Your hide spell fizzles out", evoke=True, short_len=True)
        return
    
    result.hidden = True
    player.tell(f"You cast a 'hide' spell and %s disappears from view", evoke=True)
    player.tell_others(f"{player.name} casts a 'hide' spell and %s disappears from view", evoke=True)


@cmd("cast_reveal")
def do_reveal(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """ Reveal hidden things. """

    skillValue, spell = _check_spell_skill(player, MagicType.REVEAL, "You don't know how the 'reveal' spell.")
    level = _parse_level(player, parsed, 0)

    if not spell.check_cost(player.stats.magic_points, level):
        raise ActionRefused(not_enough_magic_points)
    
    player.stats.magic_points -= spell.base_cost * level
    
    if random.randint(1, 100) > skillValue:
        player.tell("Your reveal spell fizzles out", evoke=True, short_len=True)
        return
    
    livings = player.location.livings

    if len(player.location.livings) == 1:
        player.tell("Your spell reveals nothing.")
        return

    found = False
        
    for living in livings:
        if living != player and living.hidden:
            if random.randint(1, 100) < level * 10 - living.stats.skills.get(SkillType.HIDE, 0):
                living.hidden = False
                player.tell("Your spell reveals %s." % living.title)
                player.location.tell("%s's spell reveals %s" % (player.title, living.title), exclude_living=player)
                found = True

    if not found:
        player.tell("Your spell reveals nothing.")

def _parse_level(player: Player,parsed: base.ParseResult, arg_pos: int = 1) -> int:
    num_args = len(parsed.args)
    level = player.stats.level
    if num_args > arg_pos:
        level = int(parsed.args[arg_pos])
    return level

def _check_spell_skill(player: Player, spell_type: MagicType, no_skill_message: str) -> int:
    skillValue = player.stats.magic_skills.get(spell_type, None)
    if not skillValue:
        raise ActionRefused(no_skill_message)
    
    spell =  magic.spells[spell_type] # type: Spell
    return skillValue, spell

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
