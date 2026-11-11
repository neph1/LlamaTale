

from enum import  IntEnum


class SkillType(IntEnum):

    HIDE = 1
    SEARCH = 2
    PICK_LOCK = 3
    DODGE = 4        # defense against trap effects
    SET_TRAP = 5     # arming traps
    DISARM_TRAP = 6  # disarming revealed traps

class Skills(dict):

    def __init__(self):
        
        self[SkillType.HIDE] = 0
        self[SkillType.SEARCH] = 0
        self[SkillType.PICK_LOCK] = 0
        self[SkillType.DODGE] = 0
        self[SkillType.SET_TRAP] = 0
        self[SkillType.DISARM_TRAP] = 0

    def get(self, skill: SkillType) -> int:
        return super().get(skill, 0)  # Use the dict's get method
    
    def set(self, skill: SkillType, value: int) -> None:
        self[skill] = value  # Use dict assignment

    def to_json(self) -> dict:
        # Convert the skill names and values to JSON-serializable form
        return {skill: value for skill, value in self.items()}
    
    @classmethod
    def from_json(cls, json_data: dict) -> 'Skills':
        # Convert the JSON data to a Skills object
        skills = cls()
        for skill, value in json_data.items():
            skills[skill] = value
        return skills
