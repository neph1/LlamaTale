import json
import os
import re
import requests
import yaml

class LlmUtil():
    def __init__(self):
        with open(os.path.realpath(os.path.join(os.path.dirname(__file__), "llm_config.yaml")), "r") as stream:
            try:
                config_file = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        self.url = config_file['URL'] + config_file['ENDPOINT']
        self.default_body = json.loads(config_file['DEFAULT_BODY'])
        self.memory_size = config_file['MEMORY_SIZE']
        self.pre_prompt = config_file['PRE_PROMPT']
        self.base_prompt = config_file['BASE_PROMPT']
        self.dialogue_prompt = config_file['DIALOGUE_PROMPT']

    def evoke(self, message: str, max_length : bool=False, rolling_prompt='', alt_prompt=''):
        if len(message) > 0 and str(message) != "\n":
            trimmed_message = self.remove_special_chars(str(message))
            base_prompt = alt_prompt if alt_prompt else self.base_prompt
            amount = len(trimmed_message) * 2
            prompt = rolling_prompt
            prompt += self.base_prompt.format(input_text=str(trimmed_message))
            
            rolling_prompt = self.update_memory(rolling_prompt, trimmed_message)
            
            request_body = self.default_body
            request_body['prompt'] = prompt
            if max_length:
                request_body['max_length'] = amount
            response = requests.post(self.url, data=json.dumps(request_body))
            text = self.trim_response(json.loads(response.text)['results'][0]['text'])
            
            rolling_prompt = self.update_memory(rolling_prompt, text)
            return f'Original:[ {message} ] Generated:\n{text}', rolling_prompt
        return str(message), rolling_prompt
    
    def generate_dialogue(self, conversation: str, character_card: str, character_name: str, target: str):
        prompt = self.pre_prompt
        prompt += self.dialogue_prompt.format(
                previous_conversation=conversation, 
                character2_description=character_card,
                character2=character_name,
                character1=target)
        
        request_body = self.default_body
        request_body['prompt'] = prompt
        response = requests.post(self.url, data=json.dumps(request_body))
        text = self.trim_response(json.loads(response.text)['results'][0]['text'])
        return f'{text}'

    def update_memory(self, rolling_prompt: str, response_text: str):
        rolling_prompt += response_text
        if len(rolling_prompt) > self.memory_size:
            rolling_prompt = rolling_prompt[len(rolling_prompt) - self.memory_size + 1:]
        return rolling_prompt
        
    def remove_special_chars(self, message: str):
        re.sub('[^A-Za-z0-9 .,_\-\'\"]+', '', message)
        return message
        
    def trim_response(self, message: str):
        enders = ['.', '!', '?', '`', '*', '"', ')', '}', '`', ']']
        lastChar = 0
        for c in enders:
            last = message.rfind(c)
            if last > lastChar:
                lastChar = last
        return message[:lastChar+1]
