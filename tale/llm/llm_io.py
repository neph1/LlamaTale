import re
import requests
import time
import aiohttp
import asyncio
import json
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
        else:
            self.headers = {}
        self.stream = backend_config['STREAM']
        if self.stream:
            self.stream_endpoint = backend_config['STREAM_ENDPOINT']
            self.data_endpoint = backend_config['DATA_ENDPOINT']
        self.user_start_prompt = config['USER_START']
        self.user_end_prompt = config['USER_END']

    def synchronous_request(self, request_body: dict, prompt: str) -> str:
        """ Send request to backend and return the result """
        if request_body.get('grammar', None) and 'openai' in self.url:
            # TODO: temp fix for openai
            request_body.pop('grammar')
            request_body['response_format'] = self.openai_json_format
        self._set_prompt(request_body, prompt)
        response = requests.post(self.url + self.endpoint, headers=self.headers, data=json.dumps(request_body))
        if self.backend == 'kobold_cpp':
            parsed_response = self._parse_kobold_result(response.text)
        else:
            parsed_response = self._parse_openai_result(response.text)
        return parsed_response
    
    def asynchronous_request(self, request_body: dict, prompt: str) -> str:
        if self.backend != 'kobold_cpp':
            return self.synchronous_request(request_body, prompt)
        return self.stream_request(request_body, wait=True, prompt=prompt)

    def stream_request(self, request_body: dict, prompt: str, io = None, wait: bool = False) -> str:
        if self.backend != 'kobold_cpp':
            raise NotImplementedError("Currently does not support streaming requests for OpenAI")
        self._set_prompt(request_body, prompt)
        result = asyncio.run(self._do_stream_request(self.url + self.stream_endpoint, request_body))
        if result:
            return self._do_process_result(self.url + self.data_endpoint, io, wait)
        return ''

    async def _do_stream_request(self, url: str, request_body: dict,) -> bool:
        """ Send request to stream endpoint async to not block the main thread"""
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=json.dumps(request_body)) as response:
                if response.status == 200:
                    return True
                else:
                    # Handle errors
                    print("Error occurred:", response.status)

    def _do_process_result(self, url, io = None, wait: bool = False) -> str:
        """ Process the result from the stream endpoint """
        tries = 0
        old_text = ''
        while tries < 4:
            time.sleep(0.5)
            data = requests.post(url)
            text = self._parse_kobold_result(data.text)

            if len(text) == len(old_text):
                tries += 1
                continue
            if not wait:
                new_text = text[len(old_text):]
                io.output_no_newline(new_text, new_paragraph=False)
            old_text = text
        io.output_no_newline("")
        return old_text

    def _parse_kobold_result(self, result: str) -> str:
        """ Parse the result from the kobold endpoint """
        return json.loads(result)['results'][0]['text']
    
    def _parse_openai_result(self, result: str) -> str:
        """ Parse the result from the openai endpoint """
        try:
            return json.loads(result)['choices'][0]['message']['content']
        except:
            print("Error parsing result from OpenAI")
            print(result)

    def _set_prompt(self, request_body: dict, prompt: str) -> dict:
        if self.user_start_prompt:
            prompt = prompt.replace('[USER_START]', self.user_start_prompt)
        if self.user_end_prompt:
            prompt = prompt + self.user_end_prompt
        if self.backend == 'kobold_cpp':
            context = self._extract_context(prompt)
            request_body['memory'] = context
            request_body['prompt'] = prompt
        else :
            request_body['messages'][1]['content'] = prompt
        return request_body
    
    def _extract_context(self, full_string):
        pattern = re.escape('<context>') + "(.*?)" + re.escape('</context>')
        match = re.search(pattern, full_string, re.DOTALL)
        if match:
            return '<context>' + match.group(1) + '</context>'
        else:
            return ''