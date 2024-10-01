import enum
import random

from tale.races import BodyType

class WearLocation(enum.Enum):
    FULL_BODY = 0 # robes etc, covers TORSO, ARMS, LEGS
    HEAD = 1
    FACE = 2
    NECK = 3
    TORSO = 4
    ARMS = 5
    HANDS = 6
    LEGS = 7
    FEET = 8
    WAIST = 9 # belts etc
    BACK = 10 # backpacks etc
    UNDER_GARMENTS = 11 # underwear etc

    @classmethod
    def has_value(cls, value):
        return value in cls._member_names_
    
dressable_body_types = [BodyType.HUMANOID, BodyType.SEMI_BIPEDAL, BodyType.WINGED_MAN]

def body_parts_for_bodytype(bodytype: BodyType) -> list:
    if bodytype in dressable_body_types:
        return list(WearLocation)[1:-3]
    if bodytype == BodyType.QUADRUPED:
        return [WearLocation.HEAD, WearLocation.LEGS, WearLocation.TORSO, WearLocation.FEET, WearLocation.NECK]
    return None

def random_wearable_for_body_part(bodypart: WearLocation, setting: str = 'fantasy', armor_only = False) -> dict:
    if setting == 'fantasy':
        wearables = wearables_fantasy
    else:
        wearables = wearables_modern
    available_wearables = [key for key, value in wearables.items() if value['location'] == bodypart and (not armor_only or value['ac'] > 0)]
    if not available_wearables:
        return None
    wearable_name = random.choice(available_wearables)
    # TODO: Fix name
    wearable = wearables[wearable_name]
    wearable['name'] = wearable_name
    wearable['short_descr'] = f"A {wearable['name']} in {random.choice(wearable_colors)}"
    return wearable

wearable_colors = ['black', 'green', 'blue', 'red', 'yellow', 'white', 'brown', 'grey', 'purple', 'orange', 'pink', 'cyan', 'magenta']

# Mostly 'copilot' generated wearable types
wearables_fantasy = {
    'robe': {
        'type':  'Wearable',
        'location': WearLocation.FULL_BODY,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'cloak': {
        'type':  'Wearable',
        'location': WearLocation.BACK,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'tunic': {
        'type':  'Wearable',
        'location': WearLocation.TORSO,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'shirt': {
        'type':  'Wearable',
        'location': WearLocation.TORSO,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'pants': {
        'type':  'Wearable',
        'location': WearLocation.LEGS,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'shoes': {
        'type':  'Wearable',
        'location': WearLocation.FEET,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'belt': {
        'type':  'Wearable',
        'location': WearLocation.WAIST,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'hat': {
        'type':  'Wearable',
        'location': WearLocation.HEAD,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'steel_helmet': {
        'type':  'Wearable',
        'location': WearLocation.HEAD,
        'weight': 3,
        'value': 10,
        'ac': 3,
    },
    'mail_coif': {
        'type':  'Wearable',
        'location': WearLocation.HEAD,
        'weight': 3,
        'value': 10,
        'ac': 2,
    },
    'breeches': {
        'type':  'Wearable',
        'location': WearLocation.LEGS,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'chainmail': {
        'type':  'Wearable',
        'location': WearLocation.TORSO,
        'weight': 3,
        'value': 10,
        'ac': 3,
    },
}

# Mostly 'copilot' generated wearable types
wearables_modern = {
    't-shirt': {
        'type':  'Wearable',
        'location': WearLocation.TORSO,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'shirt': {
        'type':  'Wearable',
        'location': WearLocation.TORSO,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'jeans': {
        'type':  'Wearable',
        'location': WearLocation.LEGS,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'sneakers': {
        'type':  'Wearable',
        'location': WearLocation.FEET,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'belt': {
        'type':  'Wearable',
        'location': WearLocation.WAIST,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'dress_shoes': {
        'type':  'Wearable',
        'location': WearLocation.FEET,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'hat': {
        'type':  'Wearable',
        'location': WearLocation.HEAD,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'dress': {
        'type':  'Wearable',
        'location': WearLocation.FULL_BODY,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'suit': {
        'type':  'Wearable',
        'location': WearLocation.FULL_BODY,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'jacket': {
        'type':  'Wearable',
        'location': WearLocation.TORSO,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'coat': {
        'type':  'Wearable',
        'location': WearLocation.TORSO,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'cap': {
        'type':  'Wearable',
        'location': WearLocation.HEAD,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'pants': {
        'type':  'Wearable',
        'location': WearLocation.LEGS,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'shorts': {
        'type':  'Wearable',
        'location': WearLocation.LEGS,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'boxers': {
        'type':  'Wearable',
        'location': WearLocation.UNDER_GARMENTS,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'briefs': {
        'type':  'Wearable',
        'location': WearLocation.UNDER_GARMENTS,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'bra': {
        'type':  'Wearable',
        'location': WearLocation.UNDER_GARMENTS,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'socks': {
        'type':  'Wearable',
        'location': WearLocation.UNDER_GARMENTS,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'panties': {
        'type':  'Wearable',
        'location': WearLocation.UNDER_GARMENTS,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'thong': {
        'type':  'Wearable',
        'location': WearLocation.UNDER_GARMENTS,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'stockings': {
        'type':  'Wearable',
        'location': WearLocation.UNDER_GARMENTS,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'skirt': {
        'type':  'Wearable',
        'location': WearLocation.LEGS,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'dress_shirt': {
        'type':  'Wearable',
        'location': WearLocation.TORSO,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'blouse': {
        'type':  'Wearable',
        'location': WearLocation.TORSO,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'sweater': {
        'type':  'Wearable',
        'location': WearLocation.TORSO,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'coveralls': {
        'type':  'Wearable',
        'location': WearLocation.FULL_BODY,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'top': {
        'type':  'Wearable',
        'location': WearLocation.TORSO,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
}

# Disclaimer: Not to limit the player, but to give the generator some hints
female_clothing_modern = {'dress', 'dress_shirt', 'blouse', 'skirt', 'bra', 'panties', 'thong', 'stockings', 'top'}
male_clothing_modern = {'suit', 'boxers', 'briefs', 'shirt'}
neutral_clothing_modern = {'t-shirt', 'shirt', 'jeans', 'sneakers', 'belt', 'dress_shoes', 'hat', 'coveralls', 'sweater', 'socks', 'coat', 'jacket'}
