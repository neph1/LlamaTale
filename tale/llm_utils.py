import json
import os
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
        self.rolling_prompt = ''
        self.base_prompt = config_file['BASE_PROMPT']

    def evoke(self, message: str, max_length : bool=False):
        if len(message) > 0 and str(message) != "\n":
            amount = len(message) * 2
            print(f'Original:[ {message} ]')
            prompt = self.rolling_prompt
            prompt += self.base_prompt.format(input_text=str(message))
            
            request_body = self.default_body
            request_body['prompt'] = prompt
            if max_length:
                request_body['max_length'] = amount
            response = requests.post(self.url, data=json.dumps(request_body))
            text = self.trim_response(json.loads(response.text)['results'][0]['text'])
            self.update_memory(text)
            return text
        return str(message)

    def update_memory(self, response_text: str):
        self.rolling_prompt += response_text
        if len(self.rolling_prompt) > self.memory_size:
            self.rolling_prompt = self.rolling_prompt[self.memory_size+1:]
        
    
    def trim_response(self, message: str):
        enders = ['.', '!', '?', '`', '*', '"', ')', '}', '`', ']']
        lastChar = 0
        for c in enders:
            last = message.rfind(c)
            if last > lastChar:
                lastChar = last
        return message[:lastChar+1]
