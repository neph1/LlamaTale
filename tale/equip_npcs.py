


import random
from tale import wearable
from tale.items.basic import Money
from tale.llm.LivingNpc import LivingNpc
from tale.load_items import load_item
from tale.wearable import WearLocation


def equip_npc(npc: LivingNpc, world_items: list[dict], setting: str = 'fantasy') -> None:
    """ Parse the occupation of the npc."""
    if not world_items or npc.stats.bodytype not in wearable.dressable_body_types:
        return
    weapons = [item for item in world_items if item['type'] == 'Weapon']
    one_handed = {item['name']: item for item in weapons if item['weapon_type'] == 'ONE_HANDED'}
    two_handed = {item['name']: item for item in weapons if item['weapon_type'] == 'TWO_HANDED'}
    ranged = {item['name']: item for item in weapons if item['weapon_type'] == 'TWO_HANDED_RANGED' or item['weapon_type'] == 'ONE_HANDED_RANGED'}

    money = Money('Money', value=random.randint(5, 10 * npc.stats.level))
    npc.money += money.value

    occupation = npc.occupation.lower()
    dress_npc(npc, setting)
    if occupation in ['soldier', 'guard', 'mercenary', 'knight', 'warrior']: # Warrior
        if random.random() > 0.3:
            weapon = _get_item_by_name_or_random('Sword', one_handed)
            if weapon:
                npc.insert(load_item(weapon), npc)
                npc.wielding = npc.locate_item(weapon['name'])[0]
        else:
            weapon = _get_item_by_name_or_random('Spear', two_handed)
            if weapon:
                npc.insert(load_item(weapon), npc)
                npc.wielding = npc.locate_item(weapon['name'])[0]
        if random.random() > 0.5:
            helmet = wearable.random_wearable_for_body_part(WearLocation.HEAD, setting, armor_only=True)
            if helmet:
                npc.insert(load_item(helmet), npc)
                npc.set_wearable(npc.locate_item(helmet['name'])[0],  wearable.WearLocation.HEAD)
        if random.random() > 0.5:
            torso = wearable.random_wearable_for_body_part(WearLocation.TORSO, setting, armor_only=True)
            if torso:
                npc.insert(load_item(torso), npc)
                npc.set_wearable(npc.locate_item(torso['name'])[0],  wearable.WearLocation.TORSO)
        return
    if occupation in ['archer', 'ranger', 'hunter', 'marksman']: # Archer
        weapon = _get_item_by_name_or_random('Bow', ranged.values)
        if weapon:
            npc.insert(load_item(weapon), npc)
            npc.wielding = npc.locate_item(weapon['name'])[0]
        return
    if occupation in ['mage', 'sorcerer', 'wizard', 'warlock']: # Caster
        weapon = two_handed.get('Staff', npc)
        if weapon:
            npc.insert(load_item(weapon), npc)
            npc.wielding = npc.locate_item(weapon['name'])[0]
        return
    if occupation in ['healer', 'cleric', 'priest', 'monk']: # Healer
        potion = random.choice([item for item in world_items if item and item['type'] == 'Health'])
        if potion:
            npc.insert(load_item(potion), npc)
        return
    if occupation in ['thief', 'rogue', 'assassin', 'bandit']: # Rogue
        weapon = _get_item_by_name_or_random('Dagger', one_handed)
        if weapon:
            npc.insert(load_item(weapon), npc)
            npc.wielding = npc.locate_item(weapon['name'])[0]
        return
    if occupation in ['peasant', 'farmer', 'commoner', 'villager']:
        if random.random() > 0.3:
            weapon = _get_item_by_name_or_random('Pitchfork', one_handed)
            if weapon:
                npc.insert(load_item(weapon), npc)
                npc.wielding = npc.locate_item(weapon['name'])[0]

def _get_item_by_name_or_random(name: str, items: dict) -> dict:
    if not items:
        return None
    return items.get(name, random.choice(list(items.values())))


def dress_npc(npc: LivingNpc, setting: str = 'fantasy', max_attempts = 5) -> None:
    """ Dress the npc with random wearables."""
    wearables = {}
    while max_attempts > 0 and not (wearables.get(WearLocation.FULL_BODY, None) or (wearables.get(WearLocation.TORSO, None) and wearables.get(WearLocation.LEGS, None))):
        bodypart = random.choice(wearable.body_parts_for_bodytype(npc.stats.bodytype))
        if wearables.get(bodypart):
            continue
        wearable_name = wearable.random_wearable_for_body_part(bodypart, setting)
        if not wearable_name:
            max_attempts -= 1
            continue
        wearable_item = load_item(wearable_name)
        if not wearable_item:
            max_attempts -= 1
            continue
        npc.insert(wearable_item, npc)
        npc.set_wearable(wearable_item, wear_location=wearable_item.wear_location)
    return