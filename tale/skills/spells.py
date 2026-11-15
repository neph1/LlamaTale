
import random
from tale import stealth
from tale.base import Living
from tale.cmds import spells
from tale.errors import ActionRefused
from tale.skills import magic
from tale.skills.magic import MagicType, Spell
from tale.skills.skills import SkillType


def _risky_spellcast(caster: Living) -> None:
    """Casting while hidden (any spell except hide) triggers an immediate
    perception contest with a penalty on the caster."""
    if caster.hidden:
        stealth.risky_action(caster, hider_penalty=stealth.SPELL_WHILE_HIDDEN_PENALTY)


not_enough_magic_points = "You don't have enough magic points"

def cast_heal(caster: Living, target: Living, level: int = 1) -> None:
    """ Heal someone or something """

    skillValue, spell = _check_spell_skill(caster, MagicType.HEAL, "You don't know how to heal")

    if not spell.check_cost(caster.stats.magic_points, level):
        raise ActionRefused(not_enough_magic_points)
        
    caster.stats.magic_points -= spell.base_cost * level

    if random.randint(1, 100) > skillValue:
        caster.tell("Your healing spell fizzles out", evoke=True, short_len=True)
        return

    target.stats.replenish_hp(5 * level)
    _risky_spellcast(caster)
    caster.tell("You cast a healing spell that heals %s for %d hit points" % (target.name, 5 * level), evoke=True)
    caster.tell_others("%s casts a healing spell on %s" % (caster.name, target.name), evoke=True)


def cast_bolt(caster: Living, target: Living, level: int = 1) -> None:
    """ Cast a bolt of energy """

    skillValue, spell = _check_spell_skill(caster, MagicType.BOLT, "You don't know how to cast a bolt")

    if not spell.check_cost(caster.stats.magic_points, level):
        raise ActionRefused(not_enough_magic_points)
    
    caster.stats.magic_points -= spell.base_cost * level

    if random.randint(1, 100) > skillValue:
        caster.tell("Your bolt spell fizzles out", evoke=True, short_len=True)
        return

    hp = random.randint(1, level)
    _risky_spellcast(caster)
    target.stats.hp -= hp
    caster.tell("You cast an energy bolt that hits %s for %d damage" % (target.name, hp), evoke=True)
    caster.tell_others("%s casts an energy bolt that hits %s for %d damage" % (caster.name, target.name, hp), evoke=True)

def cast_drain(caster: Living, target: Living, level: int = 1) -> None:
    """ Drain energy from someone or something """

    skillValue, spell = _check_spell_skill(caster, MagicType.DRAIN, "You don't know how to drain")
    
    if not spell.check_cost(caster.stats.magic_points, level):
        raise ActionRefused(not_enough_magic_points)
    
    caster.stats.magic_points -= spell.base_cost * level

    if random.randint(1, 100) > skillValue:
        caster.tell("Your drain spell fizzles out", evoke=True, short_len=True)
        return
    
    points = random.randint(1, level)
    target.stats.action_points -= points
    target.stats.magic_points -= points

    caster.stats.magic_points += points
    _risky_spellcast(caster)

    caster.tell("You cast a 'drain' spell that drains %s of %d combat and magic points" % (target.name, points), evoke=True)
    caster.tell_others("%s casts a 'drain' spell that drains energy from %s" % (caster.name, target.name), evoke=True)
    
def cast_rejuvenate(caster: Living, target: Living, level: int = 1) -> None:
    """ Rejuvenate someone or something """

    skillValue, spell = _check_spell_skill(caster, MagicType.REJUVENATE, "You don't know how to rejuvenate")

    if not spell.check_cost(caster.stats.magic_points, level):
        raise ActionRefused(not_enough_magic_points)
    
    caster.stats.magic_points -= spell.base_cost * level

    if random.randint(1, 100) > skillValue:
        caster.tell("Your rejuvenate spell fizzles out", evoke=True, short_len=True)
        return

    target.stats.replenish_hp(5 * level)
    _risky_spellcast(caster)
    caster.tell("You cast a rejuvenate spell that replenishes %s for %d action points" % (target.name, 5 * level), evoke=True)
    caster.tell_others("%s casts a rejuvenate spell on %s" % (caster.name, target.name), evoke=True)


def cast_hide(caster: Living, target: Living, level: int = 1) -> None:
    """ Hide from view """

    skillValue, spell = _check_spell_skill(caster, MagicType.HIDE, "You don't know the 'hide' spell.")

    if not spell.check_cost(caster.stats.magic_points, level):
        raise ActionRefused(not_enough_magic_points)
    
    caster.stats.magic_points -= spell.base_cost * level

    # magic bypasses the skill contest: the stance is set without a throw
    target.hidden = True
    caster.tell(f"You cast a 'hide' spell and %s disappears from view", evoke=True)
    caster.tell_others(f"{caster.name} casts a 'hide' spell and %s disappears from view", evoke=True)


def cast_reveal(caster: Living, level: int = 1) -> None:
    """ Reveal hidden things. """

    skillValue, spell = _check_spell_skill(caster, MagicType.REVEAL, "You don't know the 'reveal' spell.")

    if not spell.check_cost(caster.stats.magic_points, level):
        raise ActionRefused(not_enough_magic_points)

    caster.stats.magic_points -= spell.base_cost * level

    if random.randint(1, 100) > skillValue:
        caster.tell("Your reveal spell fizzles out", evoke=True, short_len=True)
        return

    hidden_livings = [living for living in caster.location.livings
                     if living != caster and living.hidden and living.visible]

    if not hidden_livings:
        caster.tell("Your spell reveals nothing.")
        return

    found = False

    for living in hidden_livings:
        result = stealth.resolve_contest(living, caster, searcher_bonus=stealth.REVEAL_SPELL_BONUS + level * 10)
        if result.band == stealth.DetectionBand.DETECTED:
            caster.tell("Your spell reveals %s." % living.title)
            found = True

    if not found:
        caster.tell("Your spell reveals nothing.")

def _check_spell_skill(caster: Living, spell_type: MagicType, no_skill_message: str) -> int:
    skillValue = caster.stats.magic_skills.get(spell_type)
    if not skillValue:
        raise ActionRefused(no_skill_message)
    
    spell =  magic.spells[spell_type] # type: Spell
    return skillValue, spell