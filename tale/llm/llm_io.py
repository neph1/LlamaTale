import requests
import time
import aiohttp
import asyncio
import json
import tale.parse_utils as parse_utils
from tale.player_utils import TextBuffer

class IoUtil():
    """ Handles connection and data retrieval from backend """

    def __init__(self, config: dict = None):
        if not config:
            # for tests
            return 
        self.backend = config['BACKEND']
        self.url = config['URL']
        self.endpoint = config['ENDPOINT']
        self.stream_endpoint = config['STREAM_ENDPOINT']
        self.data_endpoint = config['DATA_ENDPOINT']
        if self.backend == 'openai':
            headers = json.loads(config['OPENAI_HEADERS'])
            headers['Authorization'] = f"Bearer {config['OPENAI_API_KEY']}"
            self.headers = headers
        else:
            self.headers = {}
        self.stream = config['STREAM']
        self.user_start_prompt = config['USER_START']
        self.user_end_prompt = config['USER_END']

    def synchronous_request(self, request_body: dict, prompt: str) -> str:
        """ Send request to backend and return the result """
        self._set_prompt(request_body, prompt)
        response = requests.post(self.url + self.endpoint, headers=self.headers, data=json.dumps(request_body))
        if self.backend == 'openai':
            parsed_response = self._parse_openai_result(response.text)
        else:
            parsed_response = self._parse_kobold_result(response.text)
        return parse_utils.trim_response(parsed_response)
    
    def asynchronous_request(self, request_body: dict, prompt: str) -> str:
        if self.backend == 'openai':
            return self.synchronous_request(request_body, prompt)
        return self.stream_request(request_body, wait=True, prompt=prompt)

    def stream_request(self, request_body: dict, prompt: str, player_io: TextBuffer = None, io = None, wait: bool = False) -> str:
        if self.backend == 'openai':
            raise NotImplementedError("Currently does not support streaming requests for OpenAI")
        self._set_prompt(request_body, prompt)
        result = asyncio.run(self._do_stream_request(self.url + self.stream_endpoint, request_body))
        if result:
            return self._do_process_result(self.url + self.data_endpoint, player_io, io, wait)
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

    def _do_process_result(self, url, player_io: TextBuffer = None, io = None, wait: bool = False) -> str:
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
                player_io.print(new_text, end=False, format=True, line_breaks=False)
                io.write_output()
            old_text = text

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
            request_body['prompt'] = prompt
        elif self.backend == 'openai':
            request_body['messages'][1]['content'] = prompt
        return request_body