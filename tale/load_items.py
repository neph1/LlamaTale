


import random
import sys
from tale.base import Weapon, Wearable
from tale.items.basic import Boxlike, Drink, Food, Health, Money, Note
from tale.skills.weapon_type import WeaponType
from tale.wearable import WearLocation

def load_item(item: dict):
    item_type = item.get('type', 'Item')
        
    if item_type == 'Money':
        new_item = _init_money(item)
    elif item_type == 'Health':
        new_item = _init_health(item)
        new_item.healing_effect=item.get('effect', 10)
    elif item_type == 'Food':
        new_item = _init_food(item)
        new_item.affect_fullness=item.get('effect', 10)
        new_item.poisoned=item.get('poisoned', False)
    elif item_type == 'Weapon':
        new_item = _init_weapon(item)
    elif item_type == 'Drink':
        new_item = _init_drink(item)
        new_item.affect_thirst=item.get('effect', 10)
        new_item.poisoned=item.get('poisoned', False)
    elif item_type == 'Container' or item_type == 'Boxlike':
        new_item = _init_boxlike(item)
    elif item_type == 'Wearable':
        new_item = _init_wearable(item)
    else:
        module = sys.modules['tale.items.basic']
        try:
            clazz = getattr(module, item_type)
        except AttributeError:
            try:
                clazz = getattr(sys.modules['tale.base'], item_type)
            except AttributeError:
                clazz = getattr(sys.modules['tale.base'], 'Item')
        new_item = clazz(name=item['name'], title=item.get('title', item['name']), descr=item.get('descr', ''), short_descr=item.get('short_descr', ''))
        if isinstance(new_item, Note):
            set_note(new_item, item)
    return new_item

def _init_money(item: dict):
    return Money(item['name'], 
                 value=item.get('value', 10), 
                 title=item.get('title', item['name']), 
                 short_descr=item.get('short_descr', ''))

def _init_health(item: dict):
    return Health(name=item['name'], 
                 value=item.get('value', 10), 
                 title=item.get('title', item['name']), 
                 short_descr=item.get('short_descr', ''),
                 descr=item.get('descr', ''),)

def _init_food(item: dict):
    return Food(name=item['name'], 
                 value=item.get('value', 10),
                 title=item.get('title', item['name']), 
                 short_descr=item.get('short_descr', ''),
                 descr=item.get('descr', ''),)

def _init_weapon(item: dict):
    return Weapon(name=item['name'],
                    title=item.get('title', item['name']),
                    short_descr=item.get('short_descr', ''),
                    descr=item.get('descr', ''),
                    wc=item.get('wc', 1),
                    weapon_type=WeaponType[item.get('weapon_type', WeaponType.UNARMED.name)],
                    base_damage=item.get('base_damage', random.randint(1,3)),
                    bonus_damage=item.get('bonus_damage', 0),
                    weight=item.get('weight', 1),
                    value=item.get('value', 1),) 

def _init_drink(item: dict):
    return Drink(name=item['name'], 
                 value=item.get('value', 10),
                 title=item.get('title', item['name']), 
                 short_descr=item.get('short_descr', ''))

def _init_boxlike(item: dict):
    return Boxlike(name=item['name'],
                    title=item.get('title', item['name']),
                    short_descr=item.get('short_descr', ''),
                    descr=item.get('descr', ''),
                    weight=item.get('weight', 1),
                    value=item.get('value', 1))

def _init_wearable(item: dict):
    wear_location = None
    if WearLocation.has_value(item.get('wear_location', '')):
        wear_location = WearLocation[item['wear_location']]
    return Wearable(name=item['name'],
                    title=item.get('title', item['name']),
                    short_descr=item.get('short_descr', ''),
                    descr=item.get('descr', ''),
                    weight=item.get('weight', 1),
                    wear_location=wear_location,
                    value=item.get('value', 1))
    
def set_note(note: Note, item: dict):
    note.text = item.get('text', '')
