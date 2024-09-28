


import random
from tale.items.basic import Money
from tale.llm.LivingNpc import LivingNpc
from tale.load_items import load_item


def equip_npc(npc: LivingNpc, world_items: list[dict]) -> None:
    """ Parse the occupation of the npc."""
    weapons = [item for item in world_items if item['type'] == 'Weapon']
    one_handed = {item['name']: item for item in weapons if item['weapon_type'] == 'ONE_HANDED'}
    two_handed = {item['name']: item for item in weapons if item['weapon_type'] == 'TWO_HANDED'}
    ranged = {item['name']: item for item in weapons if item['weapon_type'] == 'TWO_HANDED_RANGED' or item['weapon_type'] == 'ONE_HANDED_RANGED'}

    money = Money('Money', value=random.randint(5, 10 * npc.stats.level))
    npc.money += money.value

    occupation = npc.occupation.lower()
    if occupation in ['soldier', 'guard', 'mercenary', 'knight', 'warrior']: # Warrior
        if random.random() > 0.3:
            weapon = one_handed.get('Sword', random.choice(list(one_handed.values())))
            npc.insert(load_item(weapon), npc)
        else:
            weapon = random.choice(list(two_handed.values()))
            npc.insert(load_item(weapon), npc)
        return
    if occupation in ['archer', 'ranger', 'hunter', 'marksman']: # Archer
        weapon = random.choice(list(ranged.values()))
        npc.insert(load_item(weapon), npc)
        return
    if occupation in ['mage', 'sorcerer', 'wizard', 'warlock']: # Caster
        weapon = two_handed.get('Staff', npc)
        if weapon:
            npc.insert(load_item(weapon), npc)
        return
    if occupation in ['healer', 'cleric', 'priest', 'monk']: # Healer
        potion = random.choice([item for item in world_items if item['type'] == 'Health'])
        npc.insert(load_item(potion), npc)
        return
    if occupation in ['thief', 'rogue', 'assassin', 'bandit']: # Rogue
        weapon = one_handed.get('Dagger', random.choice(list(one_handed.values())))
        npc.insert(load_item(weapon), npc)
        return
    if occupation in ['peasant', 'farmer', 'commoner', 'villager']:
        if random.random() > 0.3:
            weapon = one_handed.get('Pitchfork', list(one_handed.values()))
            npc.insert(load_item(weapon), npc)
        return
