""" This contains various generic items the LLM can use when it want to add some
    Should be dicts after a refactor...
"""


import json
import os

def load() -> dict:
    items = dict()
    with open(os.path.realpath(os.path.join(os.path.dirname(__file__), "../../items/generic_items.json")), "r") as file:
        items = json.load(file, strict=False)
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
generic_drinks = items.get('generic_drinks', [])
generic_food = items.get('generic_food', [])

generic_items = {
    'fantasy': [*generic_weapons, *fantasy_weapons, *fantasy_items, *generic_various, *generic_drinks, *generic_food],
    'modern': [*generic_weapons, *modern_weapons, *modern_items, *generic_various, *generic_drinks, *generic_food],
    'postapoc': [*generic_weapons, *modern_weapons, *modern_items, *generic_various, *generic_drinks, *generic_food],
    'scifi': [*generic_weapons, *scifi_weapons, *scifi_items, *modern_weapons, *modern_items, *generic_various, *generic_drinks, *generic_food],
    '': [*generic_weapons, *generic_various, *generic_drinks, *generic_food],
}

