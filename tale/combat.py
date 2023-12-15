"""

Util class for combat related functions.

"""

import random
from tale import weapon_type
import tale.util as util
import tale.base as base
from tale.util import Context

class Combat():

    def __init__(self, attacker: 'base.Living', defender: 'base.Living') -> None:
        self.attacker = attacker
        self.defender = defender
    
    def _calculate_attack_success(self, actor: 'base.Living') -> int:
        """ Calculate the success of an attack. <5 is a critical hit."""
        return random.randrange(0, 100) - actor.stats.get_weapon_skill(actor.wielding.type)
    
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
        return random.randrange(0, 100) - actor2.stats.get_weapon_skill(actor2.wielding.type)
    
    def _calculate_weapon_bonus(self, actor: 'base.Living'):
            weapon = actor.wielding
            return actor.stats.wc + 1 + random.randint(1, weapon.base_damage) + weapon.bonus_damage

    def _calculate_armor_bonus(self, actor: 'base.Living'):
            return actor.stats.ac + 1
    
    def resolve_attack(self) -> (str, int, int):
        """ Both attacker and defender attack each other once.
        They get a chance to block, unless it's a critical hit, 5/100.
        Returns a textual representation of the combat and the damage done to each actor.
        """
        texts = []
        damage_to_defender = 0
        damage_to_attacker = 0
        
        text_result, damage_to_defender = self._round(self.attacker, self.defender)
        texts.extend(text_result)

        text_result, damage_to_attacker = self._round(self.defender, self.attacker)
        texts.extend(text_result)

        if self.defender.stats.hp - damage_to_defender < 0:
            texts.append(f'{self.defender.title} dies')
        if self.attacker.stats.hp - damage_to_attacker < 0:
            texts.append(f'{self.attacker.title} dies')
            
        return ', '.join(texts), damage_to_attacker, damage_to_defender
    
    def _round(self, actor1: 'base.Living', actor2: 'base.Living') -> ([str], int):
        attack_result = self._calculate_attack_success(actor1)
        texts = []
        if attack_result < 0:
            if attack_result < -actor1.stats.get_weapon_skill(actor1.wielding.type) + 5:
                texts.append(f'{actor1.title} performs a critical hit')
                block_result = 100
            else:
                texts.append(f'{actor1.title} hits')
                block_result = self._calculate_block_success(actor1, actor2)
            
            if block_result < 0:
                texts.append(f'{actor2.title} blocks')
            else:
                actor1_strength = self._calculate_weapon_bonus(actor1) * actor1.stats.size.order
                actor2_strength = self._calculate_armor_bonus(actor2) * actor2.stats.size.order
                damage_to_defender = int(max(0, actor1_strength - actor2_strength))
                if damage_to_defender > 0:
                    texts.append(f', {actor2.title} is injured')
                else:
                    texts.append(f', {actor2.title} is unharmed')
                return texts, damage_to_defender
        elif attack_result > 50:
            texts.append(f'{actor1.title} misses completely')
        elif attack_result > 25:
            texts.append(f'{actor1.title} misses')
        else:
            texts.append(f'{actor1.title} barely misses')
        return texts, 0

def produce_remains(context: Context, actor: 'base.Living'):
    """ Creates a container with the inventory of the Living
    and places it in the living's location. 
    """
    remains = base.Container(f"remains of {actor.title}")
    remains.init_inventory(actor.inventory)
    actor.location.insert(remains, None)
    actor.destroy(context)
    return remains
