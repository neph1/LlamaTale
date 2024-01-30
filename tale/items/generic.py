""" This contains various generic items the LLM can use when it want to add some
    Should be dicts after a refactor...
"""


import json
import os

import yaml
from tale import parse_utils
from tale.base import Item, Weapon
from tale.items.basic import Note
from tale.weapon_type import WeaponType

def load() -> dict:
    items = dict()
    with open(os.path.realpath(os.path.join(os.path.dirname(__file__), "../../generic_items.json")), "r") as file:
        try:
            items = yaml.safe_load(file)
        except yaml.YAMLError as exc:
            print(exc)
        return items

items = load()

generic_weapons = items.get('generic_weapons', [])
fantasy_weapons = items.get('fantasy_weapons', [])
modern_weapons = items.get('modern_weapons', [])
scifi_weapons = items.get('scifi_weapons', [])
fantasy_items = items.get('fantasy_items', [])
modern_items = items.get('modern_items', [])
scifi_items = items.get('scifi_items', [])
generic_various = items.get('generic_various', [])

generic_items = {
    'fantasy': [*generic_weapons, *fantasy_weapons, *fantasy_items, *generic_various],
    'modern': [*generic_weapons, *modern_weapons, *modern_items, *generic_various],
    'postapoc': [*generic_weapons, *modern_weapons, *modern_items, *generic_various],
    'scifi': [*generic_weapons, *scifi_weapons, *scifi_items, *modern_weapons, *modern_items, *generic_various],
    '': [*generic_weapons, *generic_various],
}

