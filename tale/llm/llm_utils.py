from copy import deepcopy
import json
import os
import yaml
from tale.base import Location
from tale.llm.character import CharacterBuilding
from tale.llm.llm_ext import DynamicStory
from tale.llm.llm_io import IoUtil
from tale.llm.story_building import StoryBuilding
from tale.llm.world_building import WorldBuilding
from tale.player_utils import TextBuffer
import tale.parse_utils as parse_utils
import tale.llm.llm_cache as llm_cache
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
        self.memory_size = config_file['MEMORY_SIZE']
        self.pre_prompt = config_file['PRE_PROMPT'] # type: str
        self.base_prompt = config_file['BASE_PROMPT'] # type: str
        self.combat_prompt = config_file['COMBAT_PROMPT'] # type: str
        self.word_limit = config_file['WORD_LIMIT']
        self.story_background_prompt = config_file['STORY_BACKGROUND_PROMPT'] # type: str
        self.json_grammar = config_file['JSON_GRAMMAR'] # type: str
        self.__story = None # type: DynamicStory
        self.io_util = io_util or IoUtil(config=config_file)
        self.stream = config_file['STREAM']
        self.connection = None
        #self._look_hashes = dict() # type: dict[int, str] # location hashes for look command. currently never cleared.
        self._world_building = WorldBuilding(default_body=self.default_body,
                                             io_util=self.io_util,
                                             backend=self.backend)
        self._character = CharacterBuilding(backend=self.backend,
                                    io_util=self.io_util,
                                    default_body=self.default_body)
        self._story_building = StoryBuilding(default_body=self.default_body,
                                             io_util=self.io_util,
                                             backend=self.backend)

    def evoke(self, player_io: TextBuffer, message: str, short_len : bool=False, rolling_prompt='', alt_prompt='', skip_history=True):
        """Evoke a response from LLM. Async if stream is True, otherwise synchronous.
        Update the rolling prompt with the latest message.
        Will put generated text in lm_cache.look_hashes, and reuse it if same hash is generated."""
        output_template = 'Original:[<it><rev> {message}</>] <bright><rev>Generated:</>{text}'

        if not message or str(message) == "\n":
            str(message), rolling_prompt

        rolling_prompt = self.update_memory(rolling_prompt, message)

        text_hash_value = llm_cache.generate_hash(message)

        cached_look = llm_cache.get_looks([text_hash_value])
        if cached_look:
            return output_template.format(message=message, text=cached_look), rolling_prompt

        trimmed_message = parse_utils.remove_special_chars(str(message))

        amount = 25
        prompt = self.pre_prompt
        prompt += alt_prompt or (self.base_prompt.format(
            story_context=self.__story.config.context,
            history=rolling_prompt if not skip_history or alt_prompt else '',
            max_words=self.word_limit if not short_len else amount,
            input_text=str(trimmed_message)))
        
        request_body = deepcopy(self.default_body)

        if not self.stream:
            text = self.io_util.synchronous_request(request_body, prompt=prompt)
            llm_cache.cache_look(text, text_hash_value)
            return output_template.format(message=message, text=text), rolling_prompt

        player_io.print(output_template.format(message=message, text=text), end=False, format=True, line_breaks=False)
        text = self.io_util.stream_request(request_body, player_io, self.connection, prompt=prompt)
        llm_cache.cache_look(text, text_hash_value)
        
        return '\n', rolling_prompt
    
    def generate_dialogue(self, conversation: str, 
                          character_card: str, 
                          character_name: str, 
                          target: str, 
                          target_description: str='', 
                          sentiment = '', 
                          location_description = '',
                          event_history='',
                          short_len : bool=False):
        return self._character.generate_dialogue(conversation, 
                                                 character_card=character_card, 
                                                 character_name=character_name, 
                                                 target=target, 
                                                 target_description=target_description, 
                                                 sentiment=sentiment, 
                                                 location_description=location_description, 
                                                 story_context=self.__story.config.context, 
                                                 event_history=event_history,
                                                 short_len=short_len)
    
    def update_memory(self, rolling_prompt: str, response_text: str):
        """ Keeps a history of the last couple of events"""
        rolling_prompt += response_text
        if len(rolling_prompt) > self.memory_size:
            rolling_prompt = rolling_prompt[len(rolling_prompt) - self.memory_size + 1:]
        return rolling_prompt
    
    def generate_character(self, story_context: str = '', keywords: list = [], story_type: str = ''):
        return self._character.generate_character(story_context, keywords, story_type)
    
    def get_neighbor_or_generate_zone(self, current_zone: Zone, current_location: Location, target_location: Location) -> Zone:
        return self._world_building.get_neighbor_or_generate_zone(current_zone, current_location, target_location, self.__story)

    def build_location(self, location: Location, exit_location_name: str, zone_info: dict, world_items: dict = {}, world_creatures: dict = {}, neighbors: dict = {}):
        """ Generate a location based on the current story context"""
        return self._world_building.build_location(location, 
                                                   exit_location_name, 
                                                   zone_info, 
                                                   self.__story.config.type, 
                                                   self.__story.config.context,
                                                   self.__story.config.world_info,
                                                   world_creatures=world_creatures,
                                                   world_items=world_items,
                                                   neighbors=neighbors)
     
    def perform_idle_action(self, character_name: str, location: Location, character_card: str = '', sentiments: dict = {}, last_action: str = '', event_history: str = '') -> list:
        return self._character.perform_idle_action(character_name, location, self.__story.config.context, character_card, sentiments, last_action, event_history=event_history)
    
    def perform_travel_action(self, character_name: str, location: Location, locations: list, directions: list, character_card: str = ''):
        return self._character.perform_travel_action(character_name, location, locations, directions, character_card)
    
    def perform_reaction(self, action: str, character_name: str, acting_character_name: str, location: Location, character_card: str = '', sentiment: str = '', event_history: str = ''):
        return self._character.perform_reaction(action=action, 
                                                character_name=character_name, 
                                                acting_character_name=acting_character_name, 
                                                location=location, character_card=character_card, 
                                                sentiment=sentiment, 
                                                story_context=self.__story.config.context,
                                                event_history=event_history)
    
    def generate_story_background(self, world_mood: int, world_info: str, story_type: str):
        return self._story_building.generate_story_background(world_mood, world_info, story_type)
    
    def generate_start_location(self, location: Location, zone_info: dict, story_type: str, story_context: str, world_info: str):
        return self._world_building.generate_start_location(location, zone_info, story_type, story_context, world_info)
        
    def generate_start_zone(self, location_desc: str, story_type: str, story_context: str, world_info: dict) -> Zone:
        return self._world_building.generate_start_zone(location_desc, story_type, story_context, world_info)
    
    def generate_world_items(self, story_context: str, story_type: str, world_info: str, world_mood: int) -> dict:
        return self._world_building.generate_world_items(story_context, story_type, world_info, world_mood)
    
    def generate_world_creatures(self, story_context: str, story_type: str, world_info: str, world_mood: int) -> dict:
        return self._world_building.generate_world_creatures(story_context, story_type, world_info, world_mood)
        
    def generate_random_spawn(self, location: Location, zone_info: dict):
        return self._world_building.generate_random_spawn(location=location, 
                                                          zone_info=zone_info, 
                                                          story_type=self.__story.config.type, 
                                                          story_context=self.__story.config.context,
                                                          world_info=self.__story.config.world_info,
                                                          world_creatures=self.__story.catalogue._creatures,
                                                          world_items=self.__story.catalogue._items)
    
    def generate_quest(self, base_quest: dict, character_name: str, location: Location, character_card: str, zone_info: dict, event_history: str = ''):
        return self._character.generate_quest(base_quest=base_quest,
                                              character_name=character_name, 
                                              character_card=character_card, 
                                              location=location, 
                                              story_context=self.__story.config.context, 
                                              story_type=self.__story.config.type, 
                                              world_info=self.__story.config.world_info, 
                                              zone_info=zone_info, 
                                              event_history=event_history)
  
    def set_story(self, story: DynamicStory):
        """ Set the story object."""
        self.__story = story

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
    



