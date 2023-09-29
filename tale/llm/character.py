


from json import JSONDecodeError
import json
import random

from tale import _MudContext, parse_utils
from tale.base import Location
from tale.llm.llm_ext import DynamicStory
from tale.load_character import CharacterV2


class Character():

    def __init__(self, pre_prompt: str, 
                 dialogue_prompt: str, 
                 item_prompt: str, 
                 backend: str, 
                 io_util, # Type: IOUtil
                 default_body: dict, 
                 analysis_body: dict,
                 travel_prompt: str,
                 reaction_prompt: str,
                 idle_action_prompt: str,
                 character_prompt: str,
                 json_grammar: dict):
        self.pre_prompt = pre_prompt
        self.dialogue_prompt = dialogue_prompt
        self.character_prompt = character_prompt
        self.item_prompt = item_prompt
        self.backend = backend
        self.io_util = io_util
        self.default_body = default_body
        self.analysis_body = analysis_body
        self.travel_prompt = travel_prompt
        self.reaction_prompt = reaction_prompt
        self.idle_action_prompt = idle_action_prompt
        self.__story = None
        self.json_grammar = json_grammar

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
        
        if self.backend == 'kobold_cpp':
            request_body = self.analysis_body
            request_body['prompt'] = prompt
        elif self.backend == 'openai':
            request_body = self.default_body
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
    
    def generate_character(self, story_context: str = '', keywords: list = [], story_type: str = ''):
        """ Generate a character card based on the current story context"""
        prompt = self.character_prompt.format(story_type=story_type if story_type else _MudContext.config.type,
                                              story_context=story_context, 
                                              keywords=', '.join(keywords))
        request_body = self.default_body
        if self.backend == 'kobold_cpp':
            # do some parameter tweaking for kobold_cpp
            request_body['stop_sequence'] = ['\n\n'] # to avoid text after the character card
            request_body['temperature'] = 0.7
            request_body['top_p'] = 0.92
            request_body['rep_pen'] = 1.0
            request_body['banned_tokens'] = ['```']
            request_body['grammar'] = self.json_grammar
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
    
    def perform_idle_action(self, character_name: str, location: Location, character_card: str = '', sentiments: dict = {}, last_action: str = '') -> list:
        characters = {}
        for living in location.livings:
            if living.name != character_name.lower():
                characters[living.name] = living.short_description
        items=location.items,
        prompt = self.idle_action_prompt.format(
            last_action=last_action if last_action else f"{character_name} arrives in {location.name}",
            location=": ".join([location.title, location.short_description]),
            story_context=self.__story.config.context,
            character_name=character_name,
            character=character_card,
            items=items,
            characters=json.dumps(characters),
            sentiments=json.dumps(sentiments))
        request_body = self.default_body
        if self.backend == 'kobold_cpp':
            request_body['prompt'] = prompt
            request_body['seed'] = random.randint(0, 2147483647)
            request_body['banned_tokens'] = ['You']
        elif self.backend == 'openai':
            request_body['messages'][1]['content'] = prompt

        text = self.io_util.asynchronous_request(request_body)
        return text.split(';')
    
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
        request_body = self.default_body
        if self.backend == 'kobold_cpp':
            request_body['prompt'] = prompt
        elif self.backend == 'openai':
            request_body['messages'][1]['content'] = prompt
        text = self.io_util.asynchronous_request(request_body)
        return text
    
    def perform_reaction(self, action: str, character_name: str, acting_character_name: str, location: Location, character_card: str = '', sentiment: str = ''):
        prompt = self.pre_prompt
        prompt += self.reaction_prompt.format(
            action=action,
            location_name=location.name,
            character_name=character_name,
            character=character_card,
            acting_character_name=acting_character_name,
            sentiment=sentiment)
        request_body = self.default_body
        if self.backend == 'kobold_cpp':
            request_body['prompt'] = prompt
        elif self.backend == 'openai':
            request_body['messages'][1]['content'] = prompt
        text = self.io_util.asynchronous_request(request_body)
        return text
    
    def set_story(self, story: DynamicStory):
        self.__story = story