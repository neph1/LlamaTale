from tale.load_character import CharacterLoader, CharacterV2

class TestCharacterLoader():

    character_loader = CharacterLoader()

    # def test_load_image(self):
    #     image = 'tests/files/gandalf.png'

    #     json_data = self.character_loader.load_character(image)

    #     assert(json_data)

    #     character = CharacterV2().from_json(json_data)
    #     assert(json_data.get('name'))
    #     assert(json_data.get('description'))

    def test_load_from_json(self):
        path = 'tests/files/test_character.json'
        char_data = self.character_loader.load_character(path)
        assert(char_data)
        assert(char_data.get('name') == 'test character')
        assert(char_data.get('description'))

    def test_load_missing_file(self):
        path = 'tests/files/missing.json'
        char_data = self.character_loader.load_character(path)
        assert(not char_data)

    def test_CharacterV2(self):
        path = 'tests/files/test_character.json'
        char_data = self.character_loader.load_character(path)
        description = char_data.get('description')
        character = CharacterV2(name = char_data.get('name').lower().split(' ')[0],
            race = char_data.get('race', 'human'),
            gender = char_data.get('gender', 'm'),
            money = char_data.get('money', 0.0),
            appearance = char_data.get('appearance', ''),
            description = description,
            aliases = char_data.get('aliases', []))
        self._verify_character(character)

    def test_CharacterV2_from_json(self):
        path = 'tests/files/test_character.json'
        char_data = self.character_loader.load_character(path)
        character = CharacterV2().from_json(char_data)
        self._verify_character(character)

    def test_CharacterV2_from_json_with_memory(self):
        path = 'tests/files/test_character.json'
        char_data = self.character_loader.load_character(path)
        char_data['memory'] = {
            'known_locations': {'tavern': 'a cozy tavern'},
            'observed_events': ['test met the king'],
            'sentiments': {'king': 'hostile'},
            'action_history': ['test waved'],
            'planned_actions': [],
            'goal': 'befriend the king'}
        char_data['relationships'] = {'queen': 'kind'}
        character = CharacterV2().from_json(char_data)
        self._verify_character(character)
        assert(character.memory['known_locations'] == {'tavern': 'a cozy tavern'})
        assert(character.memory['observed_events'] == ['test met the king'])
        assert(character.memory['sentiments'] == {'king': 'hostile', 'queen': 'kind'})
        assert(character.memory['action_history'] == ['test waved'])
        assert(character.memory['goal'] == 'befriend the king')

    def test_CharacterV2_from_json_v2_data_memory(self):
        char_data = {
            'spec': 'chara_card_v2',
            'data': {
                'name': 'Nested Bot',
                'memory': {'sentiments': {'bob': 'shy'}, 'observed_events': ['bob waved']},
                'relationships': {'alice': 'kind'}}}
        character = CharacterV2().from_json(char_data)
        assert(character.name == 'nested')
        assert(character.memory['sentiments'] == {'bob': 'shy', 'alice': 'kind'})
        assert(character.memory['observed_events'] == ['bob waved'])

    def test_CharacterV2_from_json_top_level_sentiments(self):
        char_data = {
            'name': 'Sent Bot',
            'memory': {'sentiments': {'bob': 'shy'}},
            'sentiments': {'alice': 'kind'}}
        character = CharacterV2().from_json(char_data)
        assert(character.memory['sentiments'] == {'bob': 'shy', 'alice': 'kind'})

    def test_CharacterV2_from_json_relationships_override_memory_sentiments(self):
        char_data = {
            'name': 'Conflict Bot',
            'memory': {'sentiments': {'king': 'hostile', 'queen': 'neutral'}},
            'relationships': {'king': 'friendly'}}
        character = CharacterV2().from_json(char_data)
        # top-level relationships win over memory sentiments on key conflict
        assert(character.memory['sentiments'] == {'king': 'friendly', 'queen': 'neutral'})

    def test_CharacterV2_from_json_without_memory(self):
        char_data = {'name': 'Plain Bot'}
        character = CharacterV2().from_json(char_data)
        assert(character.memory == {})

    def _verify_character(self, character: CharacterV2):
        assert(character.name == 'test')
        assert(character.appearance == 'test appearance')
        assert(character.description == 'test description')
        assert(character.aliases == ['alias1', 'alias2'])
        assert(character.autonomous == False)
        
