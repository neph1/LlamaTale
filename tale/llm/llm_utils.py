import json
import os
import yaml
import random
from json import JSONDecodeError
from tale import mud_context, math_utils
from tale import zone
from tale.base import Location
from tale.coord import Coord
from tale.llm.character import Character
from tale.llm.llm_ext import DynamicStory
from tale.llm.llm_io import IoUtil
from tale.llm.world_building import WorldBuilding
from tale.load_character import CharacterV2
from tale.player_utils import TextBuffer
import tale.parse_utils as parse_utils
from tale.zone import Zone

class LlmUtil():
    """ Prepares prompts for various LLM requests"""

    def __init__(self, io_util: IoUtil = None):
        with open(os.path.realpath(os.path.join(os.path.dirname(__file__), "../../llm_config.yaml")), "r") as stream:
            try:
                config_file = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        self.backend = config_file['BACKEND']
        self.default_body = json.loads(config_file['DEFAULT_BODY']) if self.backend == 'kobold_cpp' else json.loads(config_file['OPENAI_BODY'])
        self.analysis_body = json.loads(config_file['ANALYSIS_BODY'])
        self.memory_size = config_file['MEMORY_SIZE']
        self.pre_prompt = config_file['PRE_PROMPT'] # type: str
        self.pre_json_prompt = config_file['PRE_JSON_PROMPT'] # type: str
        self.base_prompt = config_file['BASE_PROMPT'] # type: str
        self.dialogue_prompt = config_file['DIALOGUE_PROMPT'] # type: str
        self.action_prompt = config_file['ACTION_PROMPT'] # type: str
        self.combat_prompt = config_file['COMBAT_PROMPT'] # type: str
        self.character_prompt = config_file['CREATE_CHARACTER_PROMPT'] # type: str
        self.location_prompt = config_file['CREATE_LOCATION_PROMPT'] # type: str
        self.item_prompt = config_file['ITEM_PROMPT'] # type: str
        self.word_limit = config_file['WORD_LIMIT']
        self.spawn_prompt = config_file['SPAWN_PROMPT'] # type: str
        self.items_prompt = config_file['ITEMS_PROMPT'] # type: str
        self.zone_prompt = config_file['CREATE_ZONE_PROMPT'] # type: str
        self.idle_action_prompt = config_file['IDLE_ACTION_PROMPT'] # type: str
        self.travel_prompt = config_file['TRAVEL_PROMPT'] # type: str
        self.reaction_prompt = config_file['REACTION_PROMPT'] # type: str
        self.story_background_prompt = config_file['STORY_BACKGROUND_PROMPT'] # type: str
        self.start_location_prompt = config_file['START_LOCATION_PROMPT'] # type: str
        self.json_grammar = config_file['JSON_GRAMMAR'] # type: str
        self.__story = None # type: DynamicStory
        self.io_util = io_util or IoUtil(config=config_file)
        self.stream = config_file['STREAM']
        self.connection = None
        self._look_hashes = dict() # type: dict[int, str] # location hashes for look command. currently never cleared.
        self._world_building = WorldBuilding(spawn_prompt=self.spawn_prompt,
                                             items_prompt=self.items_prompt,
                                             zone_prompt=self.zone_prompt,
                                             location_prompt=self.location_prompt,
                                             pre_json_prompt=self.pre_json_prompt,
                                             json_grammar=self.json_grammar,
                                             default_body=self.default_body,
                                             io_util=self.io_util,
                                             backend=self.backend,
                                             story_background_prompt=self.story_background_prompt,
                                             start_location_prompt=self.start_location_prompt)
        self._character = Character(pre_prompt=self.pre_prompt,
                                    dialogue_prompt=self.dialogue_prompt,
                                    item_prompt=self.item_prompt,
                                    json_grammar=self.json_grammar,
                                    character_prompt=self.character_prompt,
                                    backend=self.backend,
                                    io_util=self.io_util,
                                    default_body=self.default_body,
                                    analysis_body=self.analysis_body,
                                    travel_prompt=self.travel_prompt,
                                    reaction_prompt=self.reaction_prompt,
                                    idle_action_prompt=self.idle_action_prompt)

    def evoke(self, player_io: TextBuffer, message: str, max_length : bool=False, rolling_prompt='', alt_prompt='', skip_history=True):
        """Evoke a response from LLM. Async if stream is True, otherwise synchronous.
        Update the rolling prompt with the latest message.
        Will put generated text in _look_hashes, and reuse it if same hash is passed in."""

        if not message or str(message) == "\n":
            str(message), rolling_prompt

        rolling_prompt = self.update_memory(rolling_prompt, message)

        text_hash_value = hash(message)
        if text_hash_value in self._look_hashes:
            text = self._look_hashes[text_hash_value]
            
            return f'Original:[ {message} ]\nGenerated:\n{text}', rolling_prompt

        trimmed_message = parse_utils.remove_special_chars(str(message))

        base_prompt = alt_prompt if alt_prompt else self.base_prompt
        amount = 25 #int(len(trimmed_message) / 2)
        prompt = self.pre_prompt
        prompt += base_prompt.format(
            story_context=self.__story.config.context,
            history=rolling_prompt if not skip_history or alt_prompt else '',
            max_words=self.word_limit if not max_length else amount,
            input_text=str(trimmed_message))
        
        request_body = self.default_body
        if self.backend == 'kobold_cpp':
            request_body['prompt'] = prompt
        elif self.backend == 'openai':
            request_body['messages'][1]['content'] = prompt

        if not self.stream:
            text = self.io_util.synchronous_request(request_body)
            self._store_hash(text_hash_value, text)
            return f'Original:[ {message} ]\n\nGenerated:\n{text}', rolling_prompt

        player_io.print(f'Original:[ {message} ]\nGenerated:\n', end=False, format=True, line_breaks=False)
        text = self.io_util.stream_request(request_body, player_io, self.connection)
        self._store_hash(text_hash_value, text)
        
        return '\n', rolling_prompt
    
    def generate_dialogue(self, conversation: str, 
                          character_card: str, 
                          character_name: str, 
                          target: str, 
                          target_description: str='', 
                          sentiment = '', 
                          location_description = '',
                          max_length : bool=False):
        return self._character.generate_dialogue(conversation, character_card, character_name, target, target_description, sentiment, location_description, max_length)
    
    def update_memory(self, rolling_prompt: str, response_text: str):
        """ Keeps a history of the last couple of events"""
        rolling_prompt += response_text
        if len(rolling_prompt) > self.memory_size:
            rolling_prompt = rolling_prompt[len(rolling_prompt) - self.memory_size + 1:]
        return rolling_prompt
    
    def generate_character(self, story_context: str = '', keywords: list = [], story_type: str = ''):
        return self._character.generate_character(story_context, keywords, story_type)
    
    def get_neighbor_or_generate_zone(self, current_zone: Zone, current_location: Location, target_location: Location) -> Zone:
        return self._world_building.get_neighbor_or_generate_zone(current_zone, current_location, target_location)

    def build_location(self, location: Location, exit_location_name: str, zone_info: dict):
        """ Generate a location based on the current story context"""
        return self._world_building.build_location(location, exit_location_name, zone_info)
        
    def generate_zone(self, location_desc: str, exit_location_name: str = '', current_zone_info: dict = {}, direction: str = '') -> dict:
        return self._world_building.generate_zone(location_desc, exit_location_name, current_zone_info, direction)

    def perform_idle_action(self, character_name: str, location: Location, character_card: str = '', sentiments: dict = {}, last_action: str = '') -> list:
        return self._character.perform_idle_action(character_name, location, character_card, sentiments, last_action)
    
    def perform_travel_action(self, character_name: str, location: Location, locations: list, directions: list, character_card: str = ''):
        return self._character.perform_travel_action(character_name, location, locations, directions, character_card)
    
    def perform_reaction(self, action: str, character_name: str, acting_character_name: str, location: Location, character_card: str = '', sentiment: str = ''):
        return self._character.perform_reaction(action, character_name, acting_character_name, location, character_card, sentiment)
    
    def generate_story_background(self, world_mood: int, world_info: str):
        return self._world_building.generate_story_background(world_mood, world_info)
        
    def _store_hash(self, text_hash_value: int, text: str):
        """ Store the generated text in a hash table."""
        if text_hash_value != -1:
            self._look_hashes[text_hash_value] = text

    def set_story(self, story: DynamicStory):
        """ Set the story object."""
        self.__story = story
        self._world_building.set_story(story)
        self._character.set_story(story)

    def _kobold_generation_prompt(self, request_body: dict) -> dict:
        """ changes some parameters for better generation of locations in kobold_cpp"""
        request_body = request_body.copy()
        request_body['stop_sequence'] = ['\n\n']
        request_body['temperature'] = 0.5
        request_body['top_p'] = 0.6
        request_body['top_k'] = 0
        request_body['rep_pen'] = 1.0
        request_body['grammar'] = self.json_grammar
        #request_body['banned_tokens'] = ['```']
        return request_body
    
    def generate_start_location(self, location: Location, zone_info: dict, story_type: str, story_context: str, world_info: str):
        return self._world_building.generate_start_location(location, zone_info, story_type, story_context, world_info)
        
    def generate_start_zone(self, location_desc: str, story_type: str, story_context: str, world_mood: int, world_info: str) -> Zone:
        return self._world_building.generate_start_zone(location_desc, story_type, story_context, world_mood, world_info)
    


