import json
import pytest
import tests.files
from tale.load_character import CharacterLoader, CharacterV2

class TestCharacterLoader():

    character_loader = CharacterLoader()

    def test_load_image(self):
        image = 'tests/files/gandalf.png'

        json_data = self.character_loader.load_character(image)

        assert(json_data)

        character = CharacterV2().from_json(json_data)
        assert(json_data.get('name'))
        assert(json_data.get('description'))

    def test_load_from_json(self):
        path = 'tests/files/riley.json'
        char_data = self.character_loader.load_character(path)
        assert(char_data)
        assert(char_data.get('name'))
        assert(char_data.get('description'))

    def test_CharacterV2(self):
        path = 'tests/files/riley.json'
        char_data = self.character_loader.load_character(path)
        description = char_data.get('description')
        character = CharacterV2(name = char_data.get('name'),
            race = char_data.get('race', 'human'),
            gender = char_data.get('gender', 'm'),
            money = char_data.get('money', 0.0),
            description = description)
        self._verify_character(character)

    def test_CharacterV2_from_json(self):
        path = 'tests/files/riley.json'
        char_data = self.character_loader.load_character(path)
        character = CharacterV2().from_json(char_data)
        self._verify_character(character)

    def _verify_character(self, character: CharacterV2):
        assert(character.name)
        assert(character.appearance)
        assert(character.description)
        
