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
        return random.randrange(0, 100) - actor.stats.get_weapon_skill(actor.wielding.type)
    
    def _calculate_block_success(self, actor1: 'base.Living', actor2: 'base.Living') -> int:
        if actor1.wielding.type in weapon_type.ranged:
            # can't block ranged weapons
            return 100
        if actor2.wielding.type in weapon_type.ranged:
            # can't block with a ranged weapon
            return 100
        return random.randrange(0, 100) - actor2.stats.get_weapon_skill(actor2.wielding.type)
    
    def resolve_attack(self):

        damage_to_defender = 0
        damage_to_attacker = 0
        attack_result = self._calculate_attack_success(self.attacker)
        texts = []
        if attack_result < 0:
            # Attacker hits
            block_result = self._calculate_block_success(self.attacker, self.defender)
            texts.append(f'{self.attacker.title} hits')
            if block_result < 0:
                texts.append(f'{self.defender.title} blocks')
            else:
                damage_to_defender = self._combat(self.attacker, self.defender)
                if damage_to_defender > 0:
                    texts.append(f', {self.defender.title} is injured')
                if self.defender.stats.hp - damage_to_defender < 1:
                    texts.append(f', {self.defender.title} dies')
        elif attack_result > 50:
            texts.append(f'{self.attacker.title} misses completely')
        elif attack_result > 25:
            texts.append(f'{self.attacker.title} misses')
        else:
            texts.append(f'{self.attacker.title} barely misses')

        attack_result = self._calculate_attack_success(self.defender)

        if attack_result < 0:
            # Defender hits
            texts.append(f'{self.defender.title} hits')
            block_result = self._calculate_block_success(self.defender, self.attacker)
            if block_result < 0:
                texts.append(f'{self.attacker.title} blocks')
            else:
                damage_to_attacker = self._combat(self.defender, self.attacker)
                if damage_to_attacker > 0:
                    texts.append(f'{self.attacker.title} is injured')
                if self.attacker.stats.hp - damage_to_attacker < 1:
                    texts.append(f'{self.attacker.title} dies')
        elif attack_result > 50:
            texts.append(f'{self.defender.title} misses completely')
        elif attack_result > 25:
            texts.append(f'{self.defender.title} misses')
        else:
            texts.append(f'{self.defender.title} barely misses')
            
        return ', '.join(texts), damage_to_attacker, damage_to_defender

    def _combat(self, actor1: 'base.Living', actor2: 'base.Living'):
        
        def calculate_weapon_bonus(actor: 'base.Living'):
            # The weapon bonus is a random factor between 0 and 1. If the actor has no weapon, bonus is 1.
            return actor.stats.wc + 1 + actor.wielding.base_damage

        def calculate_armor_bonus(actor: 'base.Living'):
            # The armor bonus is a random factor between 0 and 1. If the actor has no armor, bonus is 1.
            return actor.stats.ac + 1

        # Calculate the damage done by the attacker to the defender
        actor1_strength = calculate_weapon_bonus(actor1) * actor1.stats.size.order
        actor2_strength = calculate_armor_bonus(actor2) * actor2.stats.size.order
        return int(max(0, actor1_strength - actor2_strength))
        

def produce_remains(context: Context, actor: 'base.Living'):
    # Produce the remains of the actor
    remains = base.Container(f"remains of {actor.title}")
    remains.init_inventory(actor.inventory)
    actor.location.insert(remains, None)
    actor.destroy(context)
    return remains
