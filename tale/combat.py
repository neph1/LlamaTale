"""

Util class for combat related functions.

"""

import logging
import random
from typing import Any, List, Optional, Tuple
from tale.skills import weapon_type
from tale.story import CombatType
import tale.base as base
from tale.wearable import WearLocation, body_parts_for_bodytype
from tale.wearable import WearLocation
import random
from collections import Counter
import random

log = logging.getLogger(__name__)

LETHALITY_GUIDANCE = {
    CombatType.NONLETHAL: "Nobody dies. Serious injuries do not occur. Fights end with surrender, exhaustion, or knockout.",
    CombatType.SPARRING: "This is controlled practice. Describe technique and restraint. It ends before anyone is truly hurt.",
    CombatType.CARTOONY: "Describe slapstick, exaggerated, humorous action. Injuries are comedic and temporary.",
    CombatType.HISTORICAL: "Grounded and realistic. Injuries are painful and matter. Death is possible.",
    CombatType.ULTRAVIOLENT: "Graphic, visceral, brutal. Do not sanitize the violence.",
}


def apply_damage(target: 'base.Living', damage: int, lethal: bool = True) -> int:
    """Apply damage to a living, flooring hp at 1 when combat is non-lethal.
    Returns the damage actually applied."""
    if not lethal:
        damage = min(damage, max(target.stats.hp - 1, 0))
    target.stats.hp -= damage
    return damage


def parse_combat_type(value: Any) -> Optional[CombatType]:
    """Match a combat_type string case-insensitively against the CombatType enum.
    Returns None for free-text values (custom tone)."""
    if not value:
        return None
    text = str(value).strip().lower()
    for combat_type in CombatType:
        if text in (combat_type.value.lower(), combat_type.name.lower()):
            return combat_type
    return None


def lethality_guidance(combat_type: Any, lethal: bool) -> str:
    """Narration guidance sentence for the LLM prompt, based on the combat type
    (named level or free text) and the lethality flag."""
    parsed = parse_combat_type(combat_type)
    if parsed is not None:
        return LETHALITY_GUIDANCE[parsed]
    if combat_type:
        log.info("Using custom combat_type %r as free-text combat tone (lethal=%s)", combat_type, lethal)
    if lethal:
        return LETHALITY_GUIDANCE[CombatType.HISTORICAL]
    return LETHALITY_GUIDANCE[CombatType.NONLETHAL]


class Combat():

    def __init__(self, attackers: List['base.Living'], defenders: List['base.Living'], target_body_part: WearLocation = None, lethal: bool = True) -> None:
        self.attackers = attackers
        self.defenders = defenders
        self.target_body_part = target_body_part
        self.lethal = lethal

    def _apply_damage(self, actor: 'base.Living', damage: int) -> int:
        """Apply damage to an actor, honoring the non-lethal hp floor of 1.
        Returns the damage actually applied."""
        return apply_damage(actor, damage, lethal=self.lethal)

    def _defeat_text(self, actor: 'base.Living', applied_damage: int) -> str:
        """Mechanical end-of-fight narration for an actor that was just hit."""
        if actor.stats.hp < 1:
            return f'{actor.title} dies from their injuries.'
        if not self.lethal and applied_damage > 0 and actor.stats.hp == 1:
            return f'{actor.title} is knocked out and yields.'
        return ''
    
    def _calculate_attack_success(self, actor: 'base.Living') -> int:
        """ Calculate the success of an attack. <5 is a critical hit.
        Lower chance for attacker if trying to hit a specific body part."""
        chance = actor.stats.weapon_skills.get(actor.wielding.type)
        if self.target_body_part and actor == self.attacker:
            chance *= 1.2
        return random.randrange(0, 100) - chance
    
    def _calculate_block_success(self, actor1: 'base.Living', actor2: 'base.Living') -> int:
        """ Calculate the chance of blocking an attack.
        If the attacker is wielding a ranged weapon, the defender can't block.
        If the defender is wielding a ranged weapon, the defender can't block.
        """
        if actor1.wielding.type in weapon_type.ranged:
            # can't block ranged weapons
            return 100
        if actor2.wielding.type in weapon_type.ranged:
            # can't block with a ranged weapon
            return 100
        return random.randrange(0, 100) - actor2.stats.weapon_skills.get(actor2.wielding.type) * (0.8 if actor2.stats.action_points < 1 else 1)
    
    def _calculate_weapon_bonus(self, actor: 'base.Living'):
            weapon = actor.wielding
            return actor.stats.wc + 1 + random.randint(1, weapon.base_damage) + weapon.bonus_damage

    def _calculate_armor_bonus(self, actor: 'base.Living', body_part: WearLocation = None):
            if body_part:
                wearable = actor.get_wearable(body_part)
                return wearable.ac if wearable else 1
            return actor.stats.ac + 1
    
    def _subtract_armor_durability(self, actor: 'base.Living', body_part: WearLocation, amount: int):
        wearable = actor.get_wearable(body_part)
        if wearable:
            wearable.durability -= amount
    
    def resolve_body_part(self, defender: 'base.Living', size_factor: float, target_part: WearLocation = None) -> WearLocation:
        """ Resolve the body part that was hit. """
        body_parts = body_parts_for_bodytype(defender.stats.bodytype)
        if not body_parts:
            body_parts = [WearLocation.FULL_BODY]
        locations = body_parts
        probability_distribution = self.create_probability_distribution(locations, size_factor=size_factor, target_part=target_part)
        
        return random.choices(list(probability_distribution.keys()), list(probability_distribution.values()))[0]
            
    def create_probability_distribution(self, locations, size_factor: float = 1.0, target_part: WearLocation = None):
        distribution = Counter(locations)
        total_items = sum(distribution.values())
        
        if size_factor != 1.0:
            if WearLocation.HEAD in distribution:
                distribution[WearLocation.HEAD] *= size_factor
            if WearLocation.TORSO in distribution:
                distribution[WearLocation.TORSO] *= size_factor
            if WearLocation.LEGS in distribution:
                distribution[WearLocation.LEGS] /= size_factor
            if WearLocation.FEET in distribution:
                distribution[WearLocation.FEET] /= size_factor
        
        if target_part:
            distribution[target_part] *= 2

        probability_distribution = {location: count / (total_items + 2) for location, count in distribution.items()}
        total_probability = sum(probability_distribution.values())
        normalized_distribution = {location: probability / total_probability for location, probability in probability_distribution.items()}
        return normalized_distribution
    
    def resolve_attack(self) -> str:
        """ Both attacker and defender attack each other once.
        They get a chance to block, unless it's a critical hit, 5/100.
        Returns a textual representation of the combat and the damage done to each actor.
        """
        texts = []  # type: List[str]
        
        for attacker in self.attackers:
            random_defender = random.choice(self.defenders)
            text_result, damage_to_defender = self._round(attacker, random_defender)   
            texts.append(text_result)
            applied = self._apply_damage(random_defender, damage_to_defender)
            texts.append(self._defeat_text(random_defender, applied))

        for defender in self.defenders:
            if defender.stats.hp < 1:
                continue
            random_attacker = random.choice(self.attackers)
            text_result, damage_to_attacker = self._round(defender, random_attacker)
            texts.append(text_result)

            applied = self._apply_damage(random_attacker, damage_to_attacker)
            texts.append(self._defeat_text(random_attacker, applied))

        return '\n'.join(text for text in texts if text)
    
    def _round(self, actor1: 'base.Living', actor2: 'base.Living') -> Tuple[List[str], int]:
        attack_result = self._calculate_attack_success(actor1)
        attack_text = f'{actor1.title} attacks {actor2.title} with their {actor1.wielding.name}'
        if attack_result < 0:
            if attack_result < -actor1.stats.weapon_skills.get(actor1.wielding.type) + 5:
                attack_text += ' and hits critically'
                block_result = 100
            else:
                attack_text += ' and hits'
                block_result = self._calculate_block_success(actor1, actor2)

            if block_result < 0:
                attack_text += f', but {actor2.title} blocks with their {actor2.wielding.name}'
                actor2.wielding.durability -= random.randint(1, 10)
            else:
                actor1_attack = self._calculate_weapon_bonus(actor1) * actor1.stats.size.order
                body_part = self.resolve_body_part(actor2, actor1.stats.size.order / actor2.stats.size.order, target_part=self.target_body_part)
                actor2_defense = self._calculate_armor_bonus(actor2, body_part) * actor2.stats.size.order
                damage_to_defender = int(max(0, actor1_attack - actor2_defense))
                if damage_to_defender > 0:
                    attack_text += f', and {actor2.title} is injured in the {body_part.name.lower()}.'
                elif actor1_attack < actor2_defense:
                    attack_text += f', but {actor2.title}\' armor protects them.'
                    self._subtract_armor_durability(actor2, body_part, actor1_attack)
                else:
                    attack_text += f', but  {actor2.title} is unharmed.'
                return attack_text, damage_to_defender
        elif attack_result > 50:
            attack_text + f', but misses completely.'
        elif attack_result > 25:
            attack_text + f', but misses.'
        else:
            attack_text + f', and barely misses.'
        return attack_text, 0
