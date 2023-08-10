"""

Util class for combat related functions.

"""

import random
import tale.util as util
import tale.base as base

def resolve_attack(attacker, victim):
    damage_to_attacker, damage_to_defender = combat(attacker, victim)
      
    text = 'After a fierce exchange of attacks '
    if damage_to_attacker > 0:
        text = text + f', {attacker.title} is injured '
    if damage_to_defender > 0:
        text = text + f', {victim.title} is injured '
    if victim.stats.hp - damage_to_defender < 1:
        text = text + f', {victim.title} dies.'
    if attacker.stats.hp - damage_to_attacker < 1:
        text = text + f', {attacker.title} dies.'
    
    return text, damage_to_attacker, damage_to_defender

def combat(actor1: 'Living', actor2: 'Living'):
    """ Simple combat, but rather complex logic. Credit to ChatGPT."""
    
    def calculate_attack(actor: 'Living'):
        # The attack strength depends on the level and strength of the actor
        return actor.stats.level

    def calculate_defense(actor: 'Living'):
        # The defense strength depends on the level and dexterity of the actor
        return actor.stats.level * actor.stats.dexterity

    def calculate_weapon_bonus(actor: 'Living'):
        # The weapon bonus is a random factor between 0 and 1. If the actor has no weapon, bonus is 1.
        return actor.stats.wc + 1

    def calculate_armor_bonus(actor: 'Living'):
        # The armor bonus is a random factor between 0 and 1. If the actor has no armor, bonus is 1.
        return actor.stats.ac + 1

    def calculate_damage(attacker: 'Living', defender: 'Living'):
        # Calculate the damage done by the attacker to the defender
        attack_strength = calculate_attack(attacker) * calculate_weapon_bonus(attacker) * attacker.stats.strength * attacker.stats.size.order
        defense_strength = calculate_defense(defender) * calculate_armor_bonus(defender) * defender.stats.strength * defender.stats.size.order
        damage = max(0, attack_strength - defense_strength)
        return damage

    # Calculate the chances of actor1 and actor2 winning
    damage_to_actor1 = calculate_damage(actor2, actor1)
    damage_to_actor2 = calculate_damage(actor1, actor2)

    # Use some randomness to introduce unpredictability
    damage_to_actor1 *= random.uniform(0.9, 1.1)
    damage_to_actor2 *= random.uniform(0.9, 1.1)

    # Calculate the normalized factor
    #total_damage = damage_to_actor1 + damage_to_actor2
    #if total_damage == 0:
    #    return 0.5
    return int(damage_to_actor1), int(damage_to_actor2)
    

def produce_remains(actor: 'Living'):
    # Produce the remains of the actor
    remains = base.Container(f"remains of {actor.title}")
    remains.init_inventory(actor.inventory)
    actor.location.insert(remains, None)
    actor.destroy(util.Context)