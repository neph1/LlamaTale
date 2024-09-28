from abc import ABC
from enum import IntEnum

class MagicType(IntEnum):
    HEAL = 1
    BOLT = 2
    DRAIN = 3
    REJUVENATE = 4
    HIDE = 5
    REVEAL = 6



class Spell(ABC):
    def __init__(self, name: str, base_cost: int, base_value: int = 1, max_level: int = -1):
        self.name = name
        self.base_value = base_value
        self.base_cost = base_cost
        self.max_level = max_level

    def check_cost(self, magic_points: int, level: int) -> bool:
        return magic_points >= self.base_cost * level

spells = {
    MagicType.HEAL: Spell('heal', base_cost=2, base_value=5),
    MagicType.BOLT: Spell('bolt', base_cost=3, base_value=5),
    MagicType.DRAIN: Spell('drain', base_cost=3, base_value=5),
    MagicType.REJUVENATE: Spell('rejuvenate', base_cost=2, base_value=4),
    MagicType.HIDE: Spell('hide', base_cost=3),
    MagicType.REVEAL: Spell('reveal', base_cost=3)
}

class MagicSkills(dict):

    def get(self, magic_type: MagicType) -> int:
        return super().get(magic_type, None)

    def set(self, magic_type: MagicType, value: int) -> None:
        self[magic_type] = value

    def to_json(self) -> dict:
        return {magic_type: value for magic_type, value in self.items()}

    @classmethod
    def from_json(cls, json_data: dict) -> 'MagicSkills':
        magic_skills = cls()
        for magic_type, value in json_data.items():
            magic_skills[MagicType[magic_type]] = value
        return magic_skills