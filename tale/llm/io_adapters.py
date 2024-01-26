
from abc import ABC, abstractmethod
import asyncio
import json
import time

import aiohttp
import requests

from tale.errors import LlmResponseException
from tale.player import PlayerConnection


class AbstractIoAdapter(ABC):

    def __init__(self, url: str, stream_endpoint: str, user_start_prompt: str, user_end_prompt: str):
        self.url = url
        self.stream_endpoint = stream_endpoint
        self.user_start_prompt = user_start_prompt
        self.user_end_prompt = user_end_prompt

    @abstractmethod
    def stream_request(self, request_body: dict, io = None, wait: bool = False) -> str:
        pass
        
    @abstractmethod
    async def _do_stream_request(self, url: str, request_body: dict,) -> bool:
        pass

    @abstractmethod
    def parse_result(self, result: str) -> str:
        pass
    
    @abstractmethod
    def set_prompt(self, request_body: dict, prompt: str, context: str = '') -> dict:
        pass

class KoboldCppAdapter(AbstractIoAdapter):

    def __init__(self, url: str, stream_endpoint: str, data_endpoint: str, user_start_prompt: str, user_end_prompt: str):
        super().__init__(url, stream_endpoint, user_start_prompt, user_end_prompt)
        self.data_endpoint = data_endpoint

    def stream_request(self, request_body: dict, io: PlayerConnection = None, wait: bool = False) -> str:
        result = asyncio.run(self._do_stream_request(self.url + self.stream_endpoint, request_body))

        try:
            if result:
                return self._do_process_result(self.url + self.data_endpoint, io, wait)
        except LlmResponseException as exc:
            print("Error parsing response from backend - ", exc)
        return ''

    async def _do_stream_request(self, url: str, request_body: dict,) -> bool:
        """ Send request to stream endpoint async to not block the main thread"""
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=json.dumps(request_body)) as response:
                if response.status == 200:
                    return True
                else:
                    print("Error occurred:", response.status)

    def _do_process_result(self, url, io: PlayerConnection, wait: bool = False) -> str:
        """ Process the result from the stream endpoint """
        tries = 0
        old_text = ''
        while tries < 4:
            time.sleep(0.25)
            data = requests.post(url)
            
            text = json.loads(data.text)['results'][0]['text']

            if len(text) == len(old_text):
                tries += 1
                continue
            if not wait:
                new_text = text[len(old_text):]
                io.output_no_newline(new_text, new_paragraph=False)
            old_text = text
        return old_text
    
    def parse_result(self, result: str) -> str:
        """ Parse the result from the stream endpoint """
        return json.loads(result)['results'][0]['text']
    
    def set_prompt(self, request_body: dict, prompt: str, context: str = '') -> dict:
        if self.user_start_prompt:
            prompt = prompt.replace('[USER_START]', self.user_start_prompt)
        if self.user_end_prompt:
            prompt = prompt + self.user_end_prompt
        prompt = prompt.replace('<context>{context}</context>', '')
        request_body['prompt'] = prompt
        request_body['memory'] = f'<context>{context}</context>'
        return request_body
    
class LlamaCppAdapter(AbstractIoAdapter):

    def stream_request(self, request_body: dict, io: PlayerConnection = None, wait: bool = False) -> str:
        return asyncio.run(self._do_stream_request(self.url + self.stream_endpoint, request_body, io = io))

    async def _do_stream_request(self, url: str, request_body: dict, io: PlayerConnection) -> str:
        """ Send request to stream endpoint async to not block the main thread"""
        request_body['stream'] = True
        text = ''
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=json.dumps(request_body)) as response:
                if response.status != 200:
                    print("Error occurred:", response.status)
                    return False
                async for chunk in response.content.iter_any():
                    decoded = chunk.decode('utf-8')
                    lines = decoded.split('\n')
                    for line in lines:
                        # Ignore empty lines
                        if not line.strip():
                            continue
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        if key == 'data':
                            data = json.loads(value)
                            choice = data['choices'][0]['delta']
                            content = choice.get('content', None)
                            
                            if content:
                                io.output_no_newline(content, new_paragraph=False)
                                text += content
                    while len(lines) == 0:
                        await asyncio.sleep(0.15)
        return text
            
    def parse_result(self, result: str) -> str:
        """ Parse the result from the stream endpoint """
        try:
            return json.loads(result)['choices'][0]['message']['content']
        except:
            raise LlmResponseException("Error parsing result from backend")
   
    def set_prompt(self, request_body: dict, prompt: str, context: str = '') -> dict:
        if self.user_start_prompt:
            prompt = prompt.replace('[USER_START]', self.user_start_prompt)
        if self.user_end_prompt:
            prompt = prompt + self.user_end_prompt
        if context:
            prompt = prompt.replace('<context>{context}</context>', f'<context>{context}</context>')
            #request_body['messages'][0]['content'] = f'<context>{context}</context>'
        request_body['messages'][1]['content'] = prompt
        return request_body