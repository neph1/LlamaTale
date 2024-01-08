import re
import requests
import time
import aiohttp
import asyncio
import json
from tale.errors import LlmResponseException
import tale.parse_utils as parse_utils
from tale.player_utils import TextBuffer

class IoUtil():
    """ Handles connection and data retrieval from backend """

    def __init__(self, config: dict = None, backend_config: dict = None):
        if not config:
            # for tests
            return 
        self.backend = config['BACKEND']
        self.url = backend_config['URL']
        self.endpoint = backend_config['ENDPOINT']
        
        if self.backend != 'kobold_cpp':
            headers = json.loads(backend_config['OPENAI_HEADERS'])
            headers['Authorization'] = f"Bearer {backend_config['OPENAI_API_KEY']}"
            self.openai_json_format = json.loads(backend_config['OPENAI_JSON_FORMAT'])
            self.headers = headers
            self.io_adapter = LlamaCppStreamAdapter(self.url, backend_config['STREAM_ENDPOINT'], config['USER_START'], config['USER_END'])
        else:
            self.io_adapter = KoboldCppStreamAdapter(self.url, backend_config['STREAM_ENDPOINT'], backend_config['DATA_ENDPOINT'], config['USER_START'], config['USER_END'])
            self.headers = {}

        self.stream = backend_config['STREAM']


    def synchronous_request(self, request_body: dict, prompt: str, context: str = '') -> str:
        """ Send request to backend and return the result """
        if request_body.get('grammar', None) and 'openai' in self.url:
            # TODO: temp fix for openai
            request_body.pop('grammar')
            request_body['response_format'] = self.openai_json_format
        request_body = self.io_adapter._set_prompt(request_body, prompt, context)
        print(request_body)
        response = requests.post(self.url + self.endpoint, headers=self.headers, data=json.dumps(request_body))
        try:
            parsed_response = self.io_adapter._parse_result(response.text)
        except LlmResponseException as exc:
            print("Error parsing response from backend - ", exc)
            return ''
        return parsed_response
    
    def asynchronous_request(self, request_body: dict, prompt: str, context: str = '') -> str:
        if self.backend != 'kobold_cpp':
            return self.synchronous_request(request_body, prompt)
        return self.stream_request(request_body, wait=True, prompt=prompt, context=context)

    def stream_request(self, request_body: dict, prompt: str, context: str = '', io = None, wait: bool = False) -> str:
        if self.io_adapter:
            request_body = self.io_adapter._set_prompt(request_body, prompt, context)
            print(request_body)
            return self.io_adapter.stream_request(request_body, io, wait)
        raise NotImplementedError("Currently does not support streaming requests for OpenAI")


class AbstractIoAdapter():

    def __init__(self, url: str, stream_endpoint: str, user_start_prompt: str, user_end_prompt: str):
        self.url = url
        self.stream_endpoint = stream_endpoint
        self.user_start_prompt = user_start_prompt
        self.user_end_prompt = user_end_prompt

    def stream_request(self, request_body: dict, io = None, wait: bool = False) -> str:
        pass
        
    async def _do_stream_request(self, url: str, request_body: dict,) -> bool:
        pass

    def _parse_result(self, result: str) -> str:
        pass

    def _set_prompt(self, request_body: dict, prompt: str, context: str = '') -> dict:
        pass
class KoboldCppStreamAdapter(AbstractIoAdapter):

    def __init__(self, url: str, stream_endpoint: str, data_endpoint: str, user_start_prompt: str, user_end_prompt: str):
        super().__init__(url, stream_endpoint, user_start_prompt, user_end_prompt)
        self.data_endpoint = data_endpoint

    def stream_request(self, request_body: dict, io = None, wait: bool = False) -> str:
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

    def _do_process_result(self, url, io = None, wait: bool = False) -> str:
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
    
    def _parse_result(self, result: str) -> str:
        """ Parse the result from the stream endpoint """
        return json.loads(result)['results'][0]['text']
    
    def _set_prompt(self, request_body: dict, prompt: str, context: str = '') -> dict:
        if self.user_start_prompt:
            prompt = prompt.replace('[USER_START]', self.user_start_prompt)
        if self.user_end_prompt:
            prompt = prompt + self.user_end_prompt
        prompt.replace('<context>{context}</context>', '')
        request_body['prompt'] = prompt
        request_body['memory'] = context
        return request_body
class LlamaCppStreamAdapter(AbstractIoAdapter):

    def stream_request(self, request_body: dict, io = None, wait: bool = False) -> str:
        result = asyncio.run(self._do_stream_request(self.url + self.stream_endpoint, request_body, io = io))

    async def _do_stream_request(self, url: str, request_body: dict, io = None) -> bool:
        """ Send request to stream endpoint async to not block the main thread"""
        request_body['stream'] = True
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
                                await asyncio.sleep(0.05) # delay to not empty the buffer
                    
                return True
            
    def _parse_result(self, result: str) -> str:
        """ Parse the result from the stream endpoint """
        try:
            return json.loads(result)['choices'][0]['message']['content']
        except:
            raise LlmResponseException("Error parsing result from backend")
   
    def _set_prompt(self, request_body: dict, prompt: str, context: str = '') -> dict:
        if self.user_start_prompt:
            prompt = prompt.replace('[USER_START]', self.user_start_prompt)
        if self.user_end_prompt:
            prompt = prompt + self.user_end_prompt
        if context:
            prompt = prompt.format(context=context)
        request_body['messages'][1]['content'] = prompt
        return request_body