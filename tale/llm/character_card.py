
from tale.quest import Quest


class CharacterCard(dict):
    def __init__(self, *, name: str, gender: str, age: int, occupation: str, personality: str, appearance: str, items: list, race: str, quest: Quest=None, goal: str=None, example_voice: str="", wearing: list=None, wielding: dict=None, roleplay_prompt: str="", roleplay_description: str=""):
        super().__init__()
        self['name'] = name
        self['gender'] = gender
        self['age'] = age
        self['occupation'] = occupation
        self['personality'] = personality
        self['appearance'] = appearance
        self['items'] = items
        self['race'] = race
        self['goal'] = goal
        self['example_voice'] = example_voice
        if quest:
            self['quest'] = quest.__str__()
        else:
            self['quest'] = None
        self['wearing'] = wearing if wearing else []
        self['wielding'] = wielding if wielding else {}
        self['roleplay_prompt'] = roleplay_prompt
        self['roleplay_appearance'] = roleplay_description
