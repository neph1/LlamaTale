import json
import os
import yaml
import random
from json import JSONDecodeError
from tale import math_utils
from tale.base import Location
from tale.llm_ext import DynamicStory
from tale.llm_io import IoUtil
from tale.load_character import CharacterV2
from tale.player_utils import TextBuffer
import tale.parse_utils as parse_utils

class LlmUtil():
    """ Prepares prompts for various LLM requests"""

    def __init__(self):
        with open(os.path.realpath(os.path.join(os.path.dirname(__file__), "../llm_config.yaml")), "r") as stream:
            try:
                config_file = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        self.backend = config_file['BACKEND']
        self.default_body = json.loads(config_file['DEFAULT_BODY']) if self.backend == 'kobold_cpp' else json.loads(config_file['OPENAI_BODY'])
        self.analysis_body = json.loads(config_file['ANALYSIS_BODY'])
        self.memory_size = config_file['MEMORY_SIZE']
        self.pre_prompt = config_file['PRE_PROMPT']
        self.base_prompt = config_file['BASE_PROMPT']
        self.dialogue_prompt = config_file['DIALOGUE_PROMPT']
        self.action_prompt = config_file['ACTION_PROMPT']
        self.combat_prompt = config_file['COMBAT_PROMPT']
        self.character_prompt = config_file['CREATE_CHARACTER_PROMPT']
        self.location_prompt = config_file['CREATE_LOCATION_PROMPT']
        self.item_prompt = config_file['ITEM_PROMPT']
        self.word_limit = config_file['WORD_LIMIT']
        self.spawn_prompt = config_file['SPAWN_PROMPT']
        self.items_prompt = config_file['ITEMS_PROMPT']
        self.__story = None # type: DynamicStory
        self.io_util = IoUtil(config=config_file)
        self.stream = config_file['STREAM']
        self.connection = None
        self._look_hashes = dict() # type: dict[int, str] # location hashes for look command. currently never cleared.

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
            return f'Original:[ {message} ]\nGenerated:\n{text}', rolling_prompt

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
        prompt = self.pre_prompt
        prompt += self.dialogue_prompt.format(
                story_context=self.__story.config.context,
                location=location_description,
                previous_conversation=conversation, 
                character2_description=character_card,
                character2=character_name,
                character1=target,
                character1_description=target_description,
                sentiment=sentiment)
        request_body = self.default_body
        if self.backend == 'kobold_cpp':
            request_body['prompt'] = prompt
        elif self.backend == 'openai':
            request_body['messages'][1]['content'] = prompt
        #if not self.stream:
        text = parse_utils.trim_response(self.io_util.synchronous_request(request_body))
        #else:
        #    player_io = mud_context.pla
        #    text = self.io_util.stream_request(self.url + self.stream_endpoint, self.url + self.data_endpoint, request_body, player_io, self.connection)

        item_handling_result, new_sentiment = self.dialogue_analysis(text, character_card, character_name, target)
        
        return f'{text}', item_handling_result, new_sentiment
    
    def dialogue_analysis(self, text: str, character_card: str, character_name: str, target: str):
        """Parse the response from LLM and determine if there are any items to be handled."""
        items = character_card.split('items:')[1].split(']')[0]
        prompt = self.generate_item_prompt(text, items, character_name, target)
        request_body = self.analysis_body
        if self.backend == 'kobold_cpp':
            request_body['prompt'] = prompt
        elif self.backend == 'openai':
            request_body['messages'][1]['content'] = prompt
        text = parse_utils.trim_response(self.io_util.synchronous_request(request_body))
        try:
            json_result = json.loads(parse_utils.sanitize_json(text))
        except JSONDecodeError as exc:
            print(exc)
            return None, None
        
        valid, item_result = self.validate_item_response(json_result, character_name, target, items)
        
        sentiment = self.validate_sentiment(json_result)
        
        return item_result, sentiment
    
    def validate_sentiment(self, json: dict):
        try:
            return json.get('sentiment')
        except:
            print(f'Exception while parsing sentiment {json}')
            return ''
    
    def generate_item_prompt(self, text: str, items: str, character1: str, character2: str) -> str:
        prompt = self.pre_prompt
        prompt += self.item_prompt.format(
                text=text, 
                items=items,
                character1=character1,
                character2=character2)
        return prompt
     
    def validate_item_response(self, json_result: dict, character1: str, character2: str, items: str) -> bool:
        if 'result' not in json_result or not json_result.get('result'):
            return False, None
        result = json_result['result']
        if 'item' not in result or not result['item']:
            return False, None
        if not result['from']:
            return False, None
        if result['item'] in items:
            return True, result
        return False, None
      
    def update_memory(self, rolling_prompt: str, response_text: str):
        """ Keeps a history of the last couple of events"""
        rolling_prompt += response_text
        if len(rolling_prompt) > self.memory_size:
            rolling_prompt = rolling_prompt[len(rolling_prompt) - self.memory_size + 1:]
        return rolling_prompt
    
    def generate_character(self, story_context: str = '', keywords: list = []):
        """ Generate a character card based on the current story context"""
        prompt = self.character_prompt.format(story_context=story_context, 
                                              keywords=', '.join(keywords))
        request_body = self.default_body
        if self.backend == 'kobold_cpp':
            # do some parameter tweaking for kobold_cpp
            request_body['stop_sequence'] = ['\n\n'] # to avoid text after the character card
            request_body['temperature'] = 0.7
            request_body['top_p'] = 0.92
            request_body['rep_pen'] = 1.0
            request_body['banned_tokens'] = ['```']
            request_body['prompt'] = prompt
        elif self.backend == 'openai':
            request_body['messages'][1]['content'] = prompt
        result = self.io_util.synchronous_request(request_body)
        try:
            json_result = json.loads(parse_utils.sanitize_json(result))
        except JSONDecodeError as exc:
            print(exc)
            return None
        try:
            return CharacterV2().from_json(json_result)
        except:
            print(f'Exception while parsing character {json_result}')
            return None

    def build_location(self, location: Location, exit_location_name: str):
        """ Generate a location based on the current story context"""
        zone_info = self.__story.zone_info(zone_name='', location=exit_location_name)

        # TODO: this is a just a placeholder algo to create some things randomly.
        spawn_prompt = ''
        spawn_chance = 0.25
        spawn = random.random() < spawn_chance
        if spawn:
            mood = zone_info.get('mood', 0) + random.randint(-5, 5)
            level = math_utils.normpdf(mean=zone_info.get('level', 1), sd=3, x=0)
            spawn_prompt = self.spawn_prompt.format(alignment=mood > 0 and 'friendly' or 'hostile', level=level)

        items_prompt = ''
        item_amount = random.randint(0, 3)
        if item_amount > 0:
            items_prompt = self.items_prompt.format(items=item_amount)

        prompt = self.location_prompt.format(
            story_type=self.__story.config.type,
            zone_info=zone_info,
            story_context=self.__story.config.context,
            exit_location=exit_location_name,
            location_name=location.name,
            spawn_prompt=spawn_prompt,
            items_prompt=items_prompt,)
        
        request_body = self.default_body
        if self.backend == 'kobold_cpp':
            # do some parameter tweaking for kobold_cpp
            request_body['stop_sequence'] = ['\n\n']
            request_body['temperature'] = 0.5
            request_body['top_p'] = 0.6
            request_body['top_k'] = 0
            request_body['rep_pen'] = 1.0
            request_body['banned_tokens'] = ['```']
            request_body['prompt'] = prompt
        elif self.backend == 'openai':
            request_body['messages'][1]['content'] = prompt
        result = self.io_util.synchronous_request(request_body)
        try:
            json_result = json.loads(parse_utils.sanitize_json(result))
            return self.validate_location(json_result, location, exit_location_name)
        except JSONDecodeError as exc:
            print(exc)
            return None
        
    def validate_location(self, json_result: dict, location_to_build: Location, exit_location_name: str):
        """Validate the location generated by LLM and update the location object."""
        try:
            description = json_result.get('description', '')
            if not description:
                # this is a hack to get around that it sometimes generate an extra json layer
                json_result = json_result[location_to_build.name]
            location_to_build.description = json_result['description']

            items = parse_utils.load_items(json_result.get("items", []))
            # the loading function works differently and will not insert the items into the location
            # since the item doesn't have the location
            
            for item in items.values():
                location_to_build.insert(item, None)

            npcs = parse_utils.load_npcs(json_result.get("npcs", []))
            for npc in npcs.values():
                location_to_build.insert(npc, None)

            new_locations, exits = parse_utils.parse_generated_exits(json_result, 
                                                                     exit_location_name, 
                                                                     location_to_build)
            location_to_build.built = True
            location_to_build.add_exits(exits)
            return new_locations
        except Exception as exc:
            print(f'Exception while parsing location {json_result} ')
            print(exc)
            return None
        
    def _store_hash(self, text_hash_value: int, text: str):
        if text_hash_value != -1:
            self._look_hashes[text_hash_value] = text

    def set_story(self, story: DynamicStory):
        self.__story = story
