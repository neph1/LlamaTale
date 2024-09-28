

from enum import IntEnum


class WeaponType(IntEnum):

    ONE_HANDED = 1
    TWO_HANDED = 2
    ONE_HANDED_RANGED = 3
    TWO_HANDED_RANGED = 4
    MAGIC = 5
    UNARMED = 6
    THROWING = 7


ranged = [WeaponType.ONE_HANDED_RANGED, WeaponType.TWO_HANDED_RANGED, WeaponType.THROWING]

hand_to_hand = [WeaponType.UNARMED, WeaponType.ONE_HANDED, WeaponType.TWO_HANDED]

class WeaponSkills(dict):

    def __init__(self):
        for weapon in WeaponType:
            self[weapon] = 0

    def set(self, weapon_type: WeaponType, value: int) -> None:
        self[weapon_type] = value

    def get(self, weapon_type: WeaponType) -> int:
        return self[weapon_type]
    
    def to_json(self) -> dict:
        # Convert the skill names and values to JSON-serializable form
        return {skill: value for skill, value in self.items()}
    
    @classmethod
    def from_json(cls, json_data: dict) -> 'WeaponSkills':
        # Convert the JSON data to a Skills object
        skills = cls()
        for skill, value in json_data.items():
            skills[skill] = value
        return skills

    def __str__(self):
        return str({weapon: value for weapon, value in self.items()})

    def __repr__(self):
        return str(self)