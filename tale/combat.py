"""

Util class for combat related functions.

"""

import random

def resolve_attack(attacker, victim):
    result = combat(attacker, victim)
      
    text = 'After a fierce battle'
    if result < 0.5:
        return text + ', %s dies.' % (victim.title), victim
    elif result > 0.5:
        return text + ', %s dies.' % (attacker.title), attacker
    else:
        return text + 'both retreat.'

def combat(actor1: 'Living', actor2: 'Living'):
    """ Simple combat, but rather complex logic. Credit to ChatGPT.
        < 0.5 actor2 'victim' dies
        > 0.5 actor1 'attacker' dies"""
    
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
    total_damage = damage_to_actor1 + damage_to_actor2
    if total_damage == 0:
        return 0.5
    return damage_to_actor1 / total_damage
    