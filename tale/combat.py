"""

Util class for combat related functions.

"""

import random
from typing import List, Tuple
from tale.skills import weapon_type
import tale.base as base
from tale.wearable import WearLocation, body_parts_for_bodytype
from tale.wearable import WearLocation
import random
from collections import Counter
import random

class Combat():

    def __init__(self, attackers: List['base.Living'], defenders: List['base.Living'], target_body_part: WearLocation = None) -> None:
        self.attackers = attackers
        self.defenders = defenders
        self.target_body_part = target_body_part
    
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
        texts = []
        
        for attacker in self.attackers:
            random_defender = random.choice(self.defenders)
            text_result, damage_to_defender = self._round(attacker, random_defender)   
            texts.extend(text_result)
            random_defender.stats.hp -= damage_to_defender
            if random_defender.stats.hp < 1:
                texts.append(f'{random_defender.title} dies')

        for defender in self.defenders:
            random_attacker = random.choice(self.attackers)
            text_result, damage_to_attacker = self._round(defender, random_attacker)
            texts.extend(text_result)

            random_attacker.stats.hp -= damage_to_attacker
            if random_attacker.stats.hp < 1:
                texts.append(f'{random_attacker.title} dies')
            
        return ', '.join(texts)
    
    def _round(self, actor1: 'base.Living', actor2: 'base.Living') -> Tuple[List[str], int]:
        attack_result = self._calculate_attack_success(actor1)
        texts = []
        if attack_result < 0:
            if attack_result < -actor1.stats.weapon_skills.get(actor1.wielding.type) + 5:
                texts.append(f'{actor1.title} performs a critical hit on {actor2.title}')
                block_result = 100
            else:
                texts.append(f'{actor1.title} hits {actor2.title}')
                block_result = self._calculate_block_success(actor1, actor2)
            
            if block_result < 0:
                texts.append(f'but {actor2.title} blocks')
            else:
                actor1_strength = self._calculate_weapon_bonus(actor1) * actor1.stats.size.order
                body_part = self.resolve_body_part(actor2, actor1.stats.size.order / actor2.stats.size.order, target_part=self.target_body_part)
                actor2_strength = self._calculate_armor_bonus(actor2, body_part) * actor2.stats.size.order
                damage_to_defender = int(max(0, actor1_strength - actor2_strength))
                if damage_to_defender > 0:
                    texts.append(f', {actor2.title} is injured in the {body_part.name.lower()}')
                else:
                    texts.append(f', {actor2.title} is unharmed')
                return texts, damage_to_defender
        elif attack_result > 50:
            texts.append(f'{actor1.title} misses {actor2.title} completely')
        elif attack_result > 25:
            texts.append(f'{actor1.title} misses {actor2.title}')
        else:
            texts.append(f'{actor1.title} barely misses {actor2.title}')
        return texts, 0
