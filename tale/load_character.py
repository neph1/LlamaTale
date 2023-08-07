import tale.parse_utils as parse_utils
from PIL import Image

import base64
import json
import os

class CharacterLoader():
    
    def load_character(self, path: str) -> dict:
        f = os.path.join(os.getcwd(), path)
        if '.json' in path:
            self.loaded_character = self.load_from_json(f)
        elif '.png' in path or '.jpg' in path:
            self.loaded_character = self.load_image(f)
        else:
            print(f'Must end with .json or .png or .jpg')
        return self.loaded_character or None

    def load_image(self, path: str):
        image = Image.open(path)
        encoded_char = image.info.get('chara')

        char_data = base64.b64decode(encoded_char)
        return json.loads(char_data)

    def load_from_json(self, path: str):
        json_char = parse_utils.load_json(path)
        return json_char
    
    
    
class CharacterV2():
    
    def __init__(self, name: str='', 
                 race: str='human', 
                 gender: str='f', 
                 appearance: str = '', 
                 personality: str = '', 
                 description: str = '', 
                 occupation: str = '',
                 age: int=30, 
                 money: int=0) -> None:
        self.name = name
        self.race = race
        self.gender = gender
        
        self.personality = personality
        self.description = description
        self.appearance = appearance or description.split(';')[0]
        self.occupation = occupation
        self.age = age
        self.money = money
        
    def from_json(self, json: dict):
        self.name = json.get('name')
        self.race = json.get('race', 'human')
        self.gender = json.get('gender', 'f')
        description = json.get('description')
        self.description = description
        self.appearance = json.get('appearance', description.split(';')[0])
        self.personality = json.get('personality', '')
        self.occupation = json.get('occupation', '')
        self.age = json.get('age', 30)
        self.money = json.get('money', 0)
        return self
        
