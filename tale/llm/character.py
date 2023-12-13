

from copy import deepcopy
from json import JSONDecodeError
import json
import random

from tale import _MudContext, parse_utils
from tale.base import Location
from tale.llm import llm_config
from tale.llm.llm_io import IoUtil
from tale.load_character import CharacterV2


class CharacterBuilding():

    def __init__(self, backend: str, io_util: IoUtil, default_body: dict):
        self.pre_prompt = llm_config.params['PRE_PROMPT']
        self.dialogue_prompt = llm_config.params['DIALOGUE_PROMPT']
        self.character_prompt = llm_config.params['CREATE_CHARACTER_PROMPT']
        self.item_prompt = llm_config.params['ITEM_PROMPT']
        self.backend = backend
        self.io_util = io_util
        self.default_body = default_body
        self.analysis_body = json.loads(llm_config.params['ANALYSIS_BODY'])
        self.travel_prompt = llm_config.params['TRAVEL_PROMPT']
        self.reaction_prompt = llm_config.params['REACTION_PROMPT']
        self.idle_action_prompt = llm_config.params['IDLE_ACTION_PROMPT']
        self.json_grammar = llm_config.params['JSON_GRAMMAR']

    def generate_dialogue(self, conversation: str, 
                          character_card: str, 
                          character_name: str, 
                          target: str, 
                          target_description: str='', 
                          sentiment = '', 
                          location_description = '',
                          story_context = '',
                          event_history = '',
                          short_len : bool=False):
        prompt = self.pre_prompt

        #formatted_conversation = llm_config.params['USER_START']
        formatted_conversation = conversation.replace('<break>', '\n')#llm_config.params['USER_END'] + '\n' + llm_config.params['USER_START'])
        prompt += self.dialogue_prompt.format(
                story_context=story_context,
                location=location_description,
                previous_conversation=formatted_conversation, 
                character2_description=character_card,
                character2=character_name,
                character1=target,
                character1_description=target_description,
                history=event_history,
                sentiment=sentiment)
        request_body = deepcopy(self.default_body)
        request_body['grammar'] = self.json_grammar

        #if not self.stream:
        response = self.io_util.synchronous_request(request_body, prompt=prompt)
        try:
            json_result = json.loads(parse_utils.sanitize_json(response))
            text = json_result["response"]
            if isinstance(text, list):
                text = text[0]
            new_sentiment = json_result.get("sentiment", None)
            item = json_result.get("give", None)
            if not isinstance(item, str):
                item = None
        except Exception as exc:
            return None, None, None
        
        return text, item, new_sentiment
    
    def dialogue_analysis(self, text: str, character_card: str, character_name: str, target: str):
        """Parse the response from LLM and determine if there are any items to be handled."""
        card = json.loads(character_card)
        items = card.get('items', [])
        prompt = self.generate_item_prompt(text, items, character_name, target)
        
        request_body = deepcopy(self.default_body)
        request_body['grammar'] = self.json_grammar

        text = self.io_util.synchronous_request(request_body, prompt=prompt)
        try:
            json_result = json.loads(parse_utils.sanitize_json(text))
        except JSONDecodeError as exc:
            print(exc)
            return None, None
        
        valid, item_result = self.validate_item_response(json_result, character_name, target, items)
        
        sentiment = self.validate_sentiment(json_result)

        # summary = json_result.get('summary', '')
        
        return item_result, sentiment
    
    def validate_sentiment(self, json: dict):
        try:
            return json.get('sentiment', '')
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
            return False, ''
        result = json_result['result']
        if 'item' not in result or not result['item']:
            return False, ''
        if not result['from']:
            return False, ''
        if result['item'] in items:
            return True, result
        return False, ''
    
    def generate_character(self, story_context: str = '', keywords: list = [], story_type: str = '') -> CharacterV2:
        """ Generate a character card based on the current story context"""
        prompt = self.character_prompt.format(story_type=story_type if story_type else _MudContext.config.type,
                                              story_context=story_context, 
                                              world_info='',
                                              keywords=', '.join(keywords))
        request_body = deepcopy(self.default_body)
        request_body['grammar'] = self.json_grammar
        result = self.io_util.synchronous_request(request_body, prompt=prompt)
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
    
    def perform_idle_action(self, character_name: str, location: Location, story_context: str, character_card: str = '', sentiments: dict = {}, last_action: str = '', event_history: str = '') -> list:
        characters = {}
        for living in location.livings:
            if living.name != character_name.lower():
                characters[living.name] = living.short_description
        items=location.items,
        prompt = self.idle_action_prompt.format(
            last_action=last_action if last_action else f"{character_name} arrives in {location.name}",
            location=": ".join([location.title, location.short_description]),
            story_context=story_context,
            character_name=character_name,
            character=character_card,
            items=items,
            characters=json.dumps(characters),
            history=event_history,
            sentiments=json.dumps(sentiments))
        request_body = deepcopy(self.default_body)
        if self.backend == 'kobold_cpp':
            request_body['seed'] = random.randint(0, 2147483647)
            request_body['banned_tokens'] = ['You']

        text = self.io_util.synchronous_request(request_body, prompt=prompt)
        return parse_utils.trim_response(text) + "\n"
    
    def perform_travel_action(self, character_name: str, location: Location, locations: list, directions: list, character_card: str = ''):
        if location.name in locations:
            locations.remove(location.name)

        prompt = self.pre_prompt
        prompt += self.travel_prompt.format(
            location_name=location.name,
            locations=locations,
            directions=directions,
            character=character_card,
            character_name=character_name)
        request_body = deepcopy(self.default_body)
        text = self.io_util.synchronous_request(request_body, prompt=prompt)
        return text
    
    def perform_reaction(self, action: str, character_name: str, acting_character_name: str, location: Location, story_context: str, character_card: str = '', sentiment: str = '', event_history: str = ''):
        prompt = self.pre_prompt
        prompt += self.reaction_prompt.format(
            action=action,
            location_name=location.name,
            character_name=character_name,
            character=character_card,
            acting_character_name=acting_character_name,
            story_context=story_context,
            history=event_history,
            sentiment=sentiment)
        request_body = deepcopy(self.default_body)
        text = self.io_util.synchronous_request(request_body, prompt=prompt)
        return parse_utils.trim_response(text) + "\n"
    
    