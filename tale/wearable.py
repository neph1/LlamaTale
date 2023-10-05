import enum

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

# Mostly 'copilot' generated wearable types
wearables_fantasy = {
    'robe': {
        'type': WearLocation.FULL_BODY,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'cloak': {
        'type': WearLocation.BACK,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'tunic': {
        'type': WearLocation.TORSO,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'shirt': {
        'type': WearLocation.TORSO,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'pants': {
        'type': WearLocation.LEGS,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'shoes': {
        'type': WearLocation.FEET,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'belt': {
        'type': WearLocation.WAIST,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'hat': {
        'type': WearLocation.HEAD,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'steel_helmet': {
        'type': WearLocation.HEAD,
        'weight': 3,
        'value': 10,
        'ac': 3,
    },
    'mail_coif': {
        'type': WearLocation.HEAD,
        'weight': 3,
        'value': 10,
        'ac': 2,
    },
    'breeches': {
        'type': WearLocation.LEGS,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
}

# Mostly 'copilot' generated wearable types
wearables_modern = {
    't-shirt': {
        'type': WearLocation.TORSO,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'shirt': {
        'type': WearLocation.TORSO,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'jeans': {
        'type': WearLocation.LEGS,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'sneakers': {
        'type': WearLocation.FEET,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'belt': {
        'type': WearLocation.WAIST,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'dress_shoes': {
        'type': WearLocation.FEET,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'hat': {
        'type': WearLocation.HEAD,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'dress': {
        'type': WearLocation.FULL_BODY,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'suit': {
        'type': WearLocation.FULL_BODY,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'jacket': {
        'type': WearLocation.TORSO,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'coat': {
        'type': WearLocation.TORSO,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'cap': {
        'type': WearLocation.HEAD,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'pants': {
        'type': WearLocation.LEGS,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'shorts': {
        'type': WearLocation.LEGS,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'boxers': {
        'type': WearLocation.UNDER_GARMENTS,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'briefs': {
        'type': WearLocation.UNDER_GARMENTS,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'bra': {
        'type': WearLocation.UNDER_GARMENTS,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'socks': {
        'type': WearLocation.UNDER_GARMENTS,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'panties': {
        'type': WearLocation.UNDER_GARMENTS,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'thong': {
        'type': WearLocation.UNDER_GARMENTS,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'stockings': {
        'type': WearLocation.UNDER_GARMENTS,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'skirt': {
        'type': WearLocation.LEGS,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'dress_shirt': {
        'type': WearLocation.TORSO,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'blouse': {
        'type': WearLocation.TORSO,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'sweater': {
        'type': WearLocation.TORSO,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'coveralls': {
        'type': WearLocation.FULL_BODY,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
    'top': {
        'type': WearLocation.TORSO,
        'weight': 1,
        'value': 10,
        'ac': 0,
    },
}

# Disclaimer: Not to limit the player, but to give the generator some hints
female_clothing_modern = {'dress', 'dress_shirt', 'blouse', 'skirt', 'bra', 'panties', 'thong', 'stockings', 'top'}
male_clothing_modern = {'suit', 'boxers', 'briefs', 'shirt'}
neutral_clothing_modern = {'t-shirt', 'shirt', 'jeans', 'sneakers', 'belt', 'dress_shoes', 'hat', 'coveralls', 'sweater', 'socks', 'coat', 'jacket'}
