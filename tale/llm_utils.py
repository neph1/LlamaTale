import json
import os
import yaml
from json import JSONDecodeError
from tale.llm_io import IoUtil
import tale.parse_utils as parse_utils
from tale.player_utils import TextBuffer

class LlmUtil():
    """ Prepares prompts for various LLM requests"""

    def __init__(self):
        with open(os.path.realpath(os.path.join(os.path.dirname(__file__), "llm_config.yaml")), "r") as stream:
            try:
                config_file = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        self.url = config_file['URL']
        self.endpoint = config_file['ENDPOINT']
        self.stream_endpoint = config_file['STREAM_ENDPOINT']
        self.data_endpoint = config_file['DATA_ENDPOINT']
        self.default_body = json.loads(config_file['DEFAULT_BODY'])
        self.analysis_body = json.loads(config_file['ANALYSIS_BODY'])
        self.memory_size = config_file['MEMORY_SIZE']
        self.pre_prompt = config_file['PRE_PROMPT']
        self.base_prompt = config_file['BASE_PROMPT']
        self.dialogue_prompt = config_file['DIALOGUE_PROMPT']
        self.action_prompt = config_file['ACTION_PROMPT']
        self.combat_prompt = config_file['COMBAT_PROMPT']
        self.item_prompt = config_file['ITEM_PROMPT']
        self.word_limit = config_file['WORD_LIMIT']
        self._story_background = ''
        self.io_util = IoUtil()
        self.stream = config_file['STREAM']
        self.connection = None

    def evoke(self, player_io: TextBuffer, message: str, max_length : bool=False, rolling_prompt='', alt_prompt='', skip_history=True):
        if len(message) > 0 and str(message) != "\n":
            trimmed_message = parse_utils.remove_special_chars(str(message))
            base_prompt = alt_prompt if alt_prompt else self.base_prompt
            amount = 50 #int(len(trimmed_message) / 2)
            prompt = self.pre_prompt
            prompt += base_prompt.format(
                story_context=self._story_background,
                history=rolling_prompt if not skip_history or alt_prompt else '',
                max_words=self.word_limit if not max_length else amount,
                input_text=str(trimmed_message))
            
            rolling_prompt = self.update_memory(rolling_prompt, trimmed_message)
            
            request_body = self.default_body 
            request_body['prompt'] = prompt

            if not self.stream:
                text = self.io_util.synchronous_request(self.url + self.endpoint, request_body)
                rolling_prompt = self.update_memory(rolling_prompt, text)
                return f'Original:[ {message} ]\nGenerated:\n{text}', rolling_prompt
            else:
                player_io.print(f'Original:[ {message} ]\nGenerated:\n', end=False, format=True, line_breaks=False)
                text = self.io_util.stream_request(self.url + self.stream_endpoint, self.url + self.data_endpoint, request_body, player_io, self.connection)
                rolling_prompt = self.update_memory(rolling_prompt, text)
                return '\n', rolling_prompt
        return str(message), rolling_prompt
    
    def generate_dialogue(self, conversation: str, character_card: str, character_name: str, target: str, target_description: str='', sentiment = '', location_description = ''):
        prompt = self.pre_prompt
        prompt += self.dialogue_prompt.format(
                story_context=self._story_background,
                location=location_description,
                previous_conversation=conversation, 
                character2_description=character_card,
                character2=character_name,
                character1=target,
                character1_description=target_description,
                sentiment=sentiment)
        request_body = self.default_body
        request_body['prompt'] = prompt
        text = parse_utils.trim_response(self.io_util.synchronous_request(self.url + self.endpoint, request_body))
        
        item_handling_result, new_sentiment = self.dialogue_analysis(text, character_card, character_name, target)
        
        return f'{text}', item_handling_result, new_sentiment
    
    def dialogue_analysis(self, text: str, character_card: str, character_name: str, target: str):
        items = character_card.split('items:')[1].split(']')[0]
        prompt = self.generate_item_prompt(text, items, character_name, target)
        request_body = self.analysis_body
        request_body['prompt'] = prompt
        text = parse_utils.trim_response(self.io_util.synchronous_request(self.url + self.endpoint, request_body))
        try:
            json_result = json.loads(text.replace('\n', ''))
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
        rolling_prompt += response_text
        if len(rolling_prompt) > self.memory_size:
            rolling_prompt = rolling_prompt[len(rolling_prompt) - self.memory_size + 1:]
        return rolling_prompt
     
    @property
    def story_background(self) -> str:
        return self._story_background

    @story_background.setter
    def story_background(self, value: str) -> None:
        self._story_background = value
